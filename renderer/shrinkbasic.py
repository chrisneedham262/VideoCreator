# renderer/shrink.py
import subprocess
from math import sqrt
from pathlib import Path

# Match your project defaults
W, H, FPS = 1920, 1080, 30
CRF = 18
AUDIO_BR = "192k"
MARGIN = 24  # pixels from the edges

def _run(cmd: str):
    return subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)

def apply_shrink_pip(
    base_path: Path,
    out_path: Path,
    start_sec: float,
    dur_sec: float,
    overlay_path: Path | None = None,
):
    """
    Picture-in-Picture effect:
      - Base video is full frame by default.
      - Between [start_sec, start_sec+dur_sec]:
           * base video also appears as a small PiP (1/12 area) at bottom-left
           * optional overlay (video/image) fills the canvas behind the small PiP
      - Audio always comes from the base video (0:a).

    overlay_path can be a video or an image (images are looped).
    """
    if dur_sec <= 0:
        # nothing to do; just passthrough encode to normalize
        cmd = (
            f'ffmpeg -y -i "{base_path}" '
            f'-vf "scale={W}:{H},fps={FPS},format=yuv420p,setsar=1" '
            f'-c:v libx264 -preset medium -crf {CRF} '
            f'-c:a aac -b:a {AUDIO_BR} -movflags +faststart "{out_path}"'
        )
        _run(cmd)
        return

    # Compute PiP size as 1/12 of the AREA -> linear scale = 1/sqrt(12)
    scale_linear = 1.0 / sqrt(12.0)  # ≈ 0.288675
    pip_w = max(1, int(W * scale_linear))
    pip_h = max(1, int(H * scale_linear))

    # Inputs: 0 = base, 1 = overlay (optional)
    if overlay_path:
        is_img = overlay_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        if is_img:
            inputs = f'-i "{base_path}" -loop 1 -i "{overlay_path}"'
            tail = "-shortest"
        else:
            inputs = f'-i "{base_path}" -i "{overlay_path}"'
            tail = ""
    else:
        inputs = f'-i "{base_path}"'
        tail = ""

    t0 = float(start_sec)
    t1 = float(start_sec + dur_sec)

    # Filtergraph:
    # 1) Prepare base and a split copy (one stays full frame, one will be shrunk)
    # 2) If overlay provided: scale it to full frame and overlay during [t0,t1]
    # 3) Make PiP from the split copy, place bottom-left during [t0,t1]
    #    (x,y) = (MARGIN, H - pip_h - MARGIN)
    chains = []
    chains.append(f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1,split=2[base][src]")

    last = "[base]"
    if overlay_path:
        chains.append(
            f"[1:v]scale={W}:{H},format=yuv420p,setpts=PTS-STARTPTS[ov]"
        )
        chains.append(
            f"{last}[ov]overlay=x=0:y=0:format=auto:"
            f"enable='between(t,{t0:.3f},{t1:.3f})'[bg]"
        )
        last = "[bg]"

    # Build the PiP from [src]
    x = MARGIN
    y = H - pip_h - MARGIN
    chains.append(
        f"[src]scale={pip_w}:{pip_h},format=rgba,setpts=PTS-STARTPTS[pip]"
    )
    chains.append(
        f"{last}[pip]overlay=x={x}:y={y}:format=auto:"
        f"enable='between(t,{t0:.3f},{t1:.3f})'[vout]"
    )

    filter_complex = ";".join(chains)

    cmd = (
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map "[vout]" -map 0:a? '
        f'-c:v libx264 -preset medium -crf {CRF} '
        f'-c:a aac -b:a {AUDIO_BR} -movflags +faststart {tail} "{out_path}"'
    )
    _run(cmd)
