# --- captions helpers ---
import subprocess, tempfile
from pathlib import Path

def _run(cmd: str):
    return subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True)

def transcribe_to_srt(media_path: Path, model_size: str = "base") -> Path:
    """
    Create an SRT next to the input using openai-whisper or faster-whisper.
    Returns the SRT path. Raises if both are unavailable.
    """
    # Try faster-whisper (faster on CPU/GPU)
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel(model_size, device="auto")
        segments, info = model.transcribe(str(media_path))
        srt_lines = []
        idx = 1
        def fmt(t):
            h = int(t // 3600); t -= 3600*h
            m = int(t // 60); t -= 60*m
            s = int(t); ms = int(round((t - s)*1000))
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        for seg in segments:
            if seg.start is None or seg.end is None: 
                continue
            text = (seg.text or "").strip()
            srt_lines += [str(idx), f"{fmt(seg.start)} --> {fmt(seg.end)}", text, ""]
            idx += 1
        out_srt = media_path.with_suffix(".auto.srt")
        out_srt.write_text("\n".join(srt_lines), encoding="utf-8")
        return out_srt
    except Exception:
        pass

    # Fallback: openai-whisper
    try:
        import whisper  # type: ignore
        model = whisper.load_model(model_size)
        result = model.transcribe(str(media_path), task="transcribe")
        lines = []
        idx = 1
        def fmt(t):
            h = int(t // 3600); t -= 3600*h
            m = int(t // 60); t -= 60*m
            s = int(t); ms = int(round((t - s)*1000))
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        for seg in result.get("segments", []):
            start = seg.get("start"); end = seg.get("end")
            if start is None or end is None: 
                continue
            text = (seg.get("text") or "").strip()
            lines += [str(idx), f"{fmt(start)} --> {fmt(end)}", text, ""]
            idx += 1
        out_srt = media_path.with_suffix(".auto.srt")
        out_srt.write_text("\n".join(lines), encoding="utf-8")
        return out_srt
    except Exception:
        pass

    raise RuntimeError("No transcription backend found. Install either `pip install faster-whisper` or `pip install openai-whisper`.")

def burn_in_subtitles(input_path: Path, srt_path: Path, out_path: Path, W=1920, H=1080, FPS=30, CRF=18, AUDIO_BR="192k"):
    """
    Burn subtitles onto video (hard subs) using libass renderer.
    Works well for styled subtitles (CapCut-like look can be achieved with ASS).
    """
    # Note: You can force styles via ASS (convert SRT→ASS for richer styling).
    cmd = (
        f'ffmpeg -y -i "{input_path}" -vf '
        f'"scale={W}:{H},fps={FPS},format=yuv420p,setsar=1,subtitles={srt_path.as_posix()}:force_style=\'FontSize=28\'" '
        f'-c:v libx264 -preset medium -crf {CRF} -c:a aac -b:a {AUDIO_BR} -movflags +faststart "{out_path}"'
    )
    _run(cmd)

def mux_soft_subtitles(input_path: Path, srt_path: Path, out_path: Path, CRF=18, AUDIO_BR="192k"):
    """
    Keep captions as a selectable track (not burned in). For MP4: mov_text.
    """
    cmd = (
        f'ffmpeg -y -i "{input_path}" -i "{srt_path}" -c:v libx264 -preset medium -crf {CRF} '
        f'-c:a aac -b:a {AUDIO_BR} -c:s mov_text -map 0:v -map 0:a? -map 1:s:0 '
        f'-movflags +faststart "{out_path}"'
    )
    _run(cmd)
