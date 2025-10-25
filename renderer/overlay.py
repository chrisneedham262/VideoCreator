# renderer/overlay.py
import shlex, subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

# Match project defaults
W, H, FPS = 1920, 1080, 30
CRF = 18
DEFAULT_FADE_IN = 0.25   # fade duration in seconds
DEFAULT_FADE_OUT = 0.25  # fade duration in seconds



def _run(cmd: str):
    return subprocess.run(shlex.split(cmd), capture_output=True, text=True, check=True)

def prepare_overlay_chain(
    input_idx: int,
    t0: float,
    t1: float,
    fade_in: float = DEFAULT_FADE_IN,
    fade_out: float = DEFAULT_FADE_OUT,
) -> List[str]:
    """
    Creates ffmpeg filter chains for overlay processing including:
    - Scaling to full frame
    - Fading in/out
    - Proper timestamp management to prevent trimming
    
    Args:
        input_idx: Input index for ffmpeg (which input file this is)
        t0: Start time in seconds (when to show overlay on timeline)
        t1: End time in seconds
        fade_in: Fade in duration in seconds
        fade_out: Fade out duration in seconds
        
    Returns:
        List of ffmpeg filter chains
    """
    chains = []
    last_label = f"{input_idx}:v"
    
    # Calculate duration for this overlay window
    dur = t1 - t0
    
    # Base scaling and format conversion - scale up by 40% for zoom effect
    expanded_w = int(W * 1.4)  # 40% larger width
    expanded_h = int(H * 1.4)  # 40% larger height
    
    # CRITICAL: Trim overlay from 0 to duration, reset timestamps, then shift to timeline position
    # This ensures the overlay video plays from its beginning, not from timeline position
    # Same logic as broll.py to prevent trimming issues
    chains.append(
        f"[{last_label}]scale={expanded_w}:{expanded_h},format=yuv420p,"
        f"trim=0:{dur:.3f},setpts=PTS-STARTPTS,"
        f"setpts=PTS+{t0}/TB[base_{input_idx}]"
    )
    last_label = f"base_{input_idx}"
    
    # Apply fades
    chains.append(
        f"[{last_label}]fade=t=in:st={t0:.3f}:d={fade_in:.3f}:alpha=1,"
        f"fade=t=out:st={(t1 - fade_out):.3f}:d={fade_out:.3f}:alpha=1"
        f"[overlay_{input_idx}]"
    )
    
    return chains

def apply_overlay_effects(
    base_path: Path,
    overlay_path: Path,
    out_path: Path,
    start_sec: float,
    dur_sec: float,
    fade_in: float = DEFAULT_FADE_IN,
    fade_out: float = DEFAULT_FADE_OUT,
):
    """
    Applies overlay effects to a video including:
    - Overlay positioning
    - Fading in/out
    - Zoom regions
    
    Args:
        base_path: Path to base video
        overlay_path: Path to overlay video/image
        out_path: Path to save output video
        start_sec: When to start overlay
        dur_sec: How long to show overlay
        fade_in: Fade in duration
        fade_out: Fade out duration
        zoom_regions: Optional list of zoom regions to apply
    """
    if dur_sec <= 0:
        # Nothing to do, just copy the base video
        _run(f'ffmpeg -y -i "{base_path}" -c copy "{out_path}"')
        return
        
    t0 = float(start_sec)
    t1 = float(start_sec + dur_sec)
    
    # Prepare filter chains
    chains = []
    
    # Setup base video
    chains.append(f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p,setsar=1[base]")
    
    # Process overlay
    is_image = overlay_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    overlay_chains = prepare_overlay_chain(
        input_idx=1,
        t0=t0,
        t1=t1,
        fade_in=fade_in,
        fade_out=fade_out,
    )
    chains.extend(overlay_chains)
    
    # Composite overlay onto base
    chains.append(
        f"[base][overlay_1]overlay=x=0:y=0:format=auto:"
        f"enable='between(t,{t0:.3f},{t1:.3f})'[v]"
    )
    
    # Build the ffmpeg command
    filter_complex = ";".join(chains)
    
    if is_image:
        inputs = f'-i "{base_path}" -loop 1 -i "{overlay_path}"'
        tail = "-shortest"
    else:
        inputs = f'-i "{base_path}" -i "{overlay_path}"'
        tail = ""
        
    cmd = (
        f'ffmpeg -y {inputs} '
        f'-filter_complex "{filter_complex}" '
        f'-map "[v]" -map 0:a? '
        f'-c:v libx264 -preset medium -crf {CRF} '
        f'-c:a copy {tail} "{out_path}"'
    )
    
    _run(cmd)
