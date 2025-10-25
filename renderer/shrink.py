# renderer/shrink.py
import shlex, subprocess
from math import sqrt
from pathlib import Path
from typing import Optional, List
from .overlay import W, H, FPS, DEFAULT_FADE_IN, DEFAULT_FADE_OUT

# Match your project defaults
CRF = 18
AUDIO_BR = "192k"
MARGIN = 24  # pixels from the edges

def _run(cmd: str):
    return subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=True)

def apply_shrink_pip(
    base_path: Path,
    out_path: Path,
    start_sec: float,
    dur_sec: float,
    overlay_path: Path | None = None,
    fade_in: float = DEFAULT_FADE_IN,
    fade_out: float = DEFAULT_FADE_OUT,
    zoom_direction: str | None = None,
    zoom_start: float | None = None,
    zoom_end: float | None = None,
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
    
    # Check for zoom direction and print message (for all PiP rows)
    if zoom_direction:
        print(f"ZOOM DETECTED: {zoom_direction} for PiP overlay")
        if zoom_start is not None and zoom_end is not None:
            print(f"ZOOM TIMING: {zoom_start}s to {zoom_end}s")
    
    if overlay_path:
        # Use the overlay module to process the overlay with zoom effects
        from .overlay import prepare_overlay_chain
        overlay_chains = prepare_overlay_chain(
            input_idx=1,
            t0=t0,
            t1=t1,
            fade_in=fade_in,
            fade_out=fade_out,
        )
        chains.extend(overlay_chains)
        
        # Time-based zoom positioning
        if zoom_direction == "left" and zoom_start is not None and zoom_end is not None:
            print(f"LEFT ZOOM: {zoom_start}s to {zoom_end}s")
            zoom_start_abs = t0 + zoom_start
            zoom_end_abs = t0 + zoom_end
            
            # Use conditional positioning: normal position, then zoom position, then back to normal
            chains.append(
                f"{last}[overlay_1]overlay=x='if(between(t,{zoom_start_abs:.3f},{zoom_end_abs:.3f}),-200,0)':y=0:format=auto:"
                f"enable='between(t,{t0:.3f},{t1:.3f})'[bg]"
            )
        else:
            chains.append(
                f"{last}[overlay_1]overlay=x=0:y=0:format=auto:"
                f"enable='between(t,{t0:.3f},{t1:.3f})'[bg]"
            )
        last = "[bg]"

    # Build the PiP from [src]
    # Don't use setpts=PTS-STARTPTS here as it causes trimming issues
    # The enable='between(t,...)' handles the timing correctly
    x = MARGIN
    y = H - pip_h - MARGIN
    chains.append(
        f"[src]scale={pip_w}:{pip_h},format=rgba,"
        f"fade=t=in:st={t0:.3f}:d=1.0:alpha=1,"  # Fade in over 1 second
        f"fade=t=out:st={(t1 - 1.0):.3f}:d=1.0:alpha=1"  # Fade out over 1 second
        f"[pip]"
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
