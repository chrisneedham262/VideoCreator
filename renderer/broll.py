# renderer/broll.py
import subprocess, uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Tuple, Iterable

# ===== Output / encode settings =====
W, H, FPS = 1920, 1080, 30
CRF = 18
AUDIO_BR = "192k"
DEFAULT_FADE_IN = 0.25
DEFAULT_FADE_OUT = 0.25

# ---------- low-level utils ----------
def run(cmd: str):
    return subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)

def probe_duration_seconds(path: Path) -> float:
    """Return media duration in seconds (0 on failure)."""
    cmd = f'ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "{path}"'
    res = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)
    try:
        return max(0.0, float(res.stdout.strip()))
    except Exception:
        return 0.0

@dataclass
class BRollSeg:
    t0: float
    t1: float
    clip_path: Path
    fade_in: float = DEFAULT_FADE_IN
    fade_out: float = DEFAULT_FADE_OUT

# ---------- save inputs ----------
def save_uploaded_file(upload, dest_dir: Path) -> Path:
    """Save a Django InMemoryUploadedFile/TemporaryUploadedFile to disk and return the path."""
    path = dest_dir / f"{uuid.uuid4()}_{upload.name}"
    with open(path, "wb") as f:
        for chunk in upload.chunks():
            f.write(chunk)
    return path

# ---------- schedule -> segments ----------
def build_segments_from_rows(
    files: Iterable, starts: Iterable[str], durs: Iterable[str],
    upload_dir: Path, video_dur: float,
    fade_in: float = DEFAULT_FADE_IN, fade_out: float = DEFAULT_FADE_OUT
) -> Tuple[List[BRollSeg], List[str]]:
    """
    Aligns b-roll rows by index (DOM order), saves files, clamps to video duration,
    returns non-overlapping, sorted segments + human-readable debug lines.
    """
    segs: List[BRollSeg] = []
    debug: List[str] = []

    files = list(files)
    starts = list(starts)
    durs = list(durs)

    for i, br in enumerate(files):
        if not br:
            continue
        try:
            t0 = max(0.0, float(starts[i]))
            dur = max(0.0, float(durs[i]))
        except Exception:
            debug.append(f"Row {i+1}: invalid start/duration → skipped")
            continue
        if dur <= 0:
            debug.append(f"Row {i+1}: duration <= 0 → skipped")
            continue
        t1 = min(video_dur, t0 + dur)
        if t1 <= t0:
            debug.append(f"Row {i+1}: end <= start after clamp → skipped")
            continue

        clip_path = save_uploaded_file(br, upload_dir)
        segs.append(BRollSeg(t0=t0, t1=t1, clip_path=clip_path, fade_in=fade_in, fade_out=fade_out))
        debug.append(f"{t0:.2f}–{t1:.2f} → {clip_path.name}")

    # sort and drop overlaps (keep earliest)
    segs.sort(key=lambda s: s.t0)
    pruned: List[BRollSeg] = []
    for s in segs:
        if not pruned or s.t0 >= pruned[-1].t1:
            pruned.append(s)
        else:
            debug.append(f"Overlap starting at {s.t0:.2f}s → skipped {s.clip_path.name}")
    return pruned, debug

# ---------- ffmpeg filter graph ----------
def build_overlay_graph(base_path: Path, segs: List[BRollSeg]) -> Tuple[str, str, str]:
    """
    Returns (inputs, filter_complex, final_video_label).
    Each B-roll is trimmed to its duration, time-shifted to absolute t0,
    faded in/out, and overlaid ONLY between [t0, t1] (enable=between).
    """
    inputs = [f'-i "{base_path}"']
    chains = [f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[base]"]
    last = "[base]"
    in_idx = 1

    for i, seg in enumerate(segs):
        dur = seg.t1 - seg.t0
        if dur <= 0:
            continue
        inputs.append(f'-i "{seg.clip_path}"')
        chains.append(
            f"[{in_idx}:v]"
            f"scale={W}:{H},fps={FPS},format=rgba,"
            f"trim=0:{dur:.3f},setpts=PTS-STARTPTS,"
            f"setpts=PTS+{seg.t0}/TB,"
            f"fade=t=in:st={seg.t0:.3f}:d={seg.fade_in:.3f}:alpha=1,"
            f"fade=t=out:st={(seg.t1 - seg.fade_out):.3f}:d={seg.fade_out:.3f}:alpha=1"
            f"[b{i}]"
        )
        chains.append(
            f"{last}[b{i}]overlay=x=0:y=0:format=auto:eof_action=pass:"
            f"enable='between(t,{seg.t0:.3f},{seg.t1:.3f})'[v{i}]"
        )
        last = f"[v{i}]"
        in_idx += 1

    return " ".join(inputs), ";".join(chains), last

# ---------- encoders ----------
def encode_with_overlays(base_path: Path, segs: List[BRollSeg], out_path: Path):
    ff_inputs, filter_complex, last_label = build_overlay_graph(base_path, segs)
    cmd = (
        f'ffmpeg -y {ff_inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map "{last_label}" -map 0:a? '
        f'-c:v libx264 -preset medium -crf {CRF} '
        f'-c:a aac -b:a {AUDIO_BR} -movflags +faststart "{out_path}"'
    )
    run(cmd)

def encode_base_only(base_path: Path, out_path: Path):
    cmd = (
        f'ffmpeg -y -i "{base_path}" '
        f'-vf "scale={W}:{H},fps={FPS},format=yuv420p,setsar=1" '
        f'-c:v libx264 -preset medium -crf {CRF} '
        f'-c:a aac -b:a {AUDIO_BR} -movflags +faststart "{out_path}"'
    )
    run(cmd)
