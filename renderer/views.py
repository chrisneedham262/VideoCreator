# renderer/views.py
import uuid
from pathlib import Path
from typing import List
from django.conf import settings
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .captions import transcribe_to_srt, burn_in_subtitles
from .shrink import apply_shrink_pip


from .broll import (
    save_uploaded_file, probe_duration_seconds,
    build_segments_from_rows, encode_with_overlays, encode_base_only
)

from .models import InputData, PiPClip, BrollClip
from .signals import render_clicked

# Import PreProduction model
from preproduction.models import PreProduction

@csrf_exempt
def index(request):
    if request.method == "POST":
        # Handle form submission by calling render_video logic
        return render_video(request)
    else:
        # Handle GET request - show the form with preproduction videos
        preproduction_videos = PreProduction.objects.all()  # Already ordered by -created_at
        context = {
            'preproduction_videos': preproduction_videos
        }
        return render(request, "renderer/index.html", context)

def process_main_video(request, updir):
    """Handle main video upload and validation"""
    media = request.FILES.get("media")
    if not media:
        raise ValueError("Upload a main video (with audio).")
    
    base_path = save_uploaded_file(media, updir)
    video_dur = probe_duration_seconds(base_path)
    if video_dur <= 0:
        raise ValueError("Could not detect duration from the uploaded video.")
    
    return base_path, video_dur

def process_broll_clips(request, base_path, video_dur, updir, outdir):
    """Handle B-roll processing"""
    files = request.FILES.getlist("broll_file")
    starts = request.POST.getlist("broll_start")
    durs = request.POST.getlist("broll_dur")
    segs, debug = build_segments_from_rows(files, starts, durs, updir, video_dur)
    
    out_path = outdir / f"{uuid.uuid4()}.mp4"
    if segs:
        encode_with_overlays(base_path, segs, out_path)
        status_msg = "\n".join(debug) if debug else "B-roll applied."
    else:
        encode_base_only(base_path, out_path)
        status_msg = "No B-roll rows. Base-only render."
    
    return out_path, status_msg, segs  # Return segments for DB saving

def process_pip_clips(request, base_path, video_dur, updir, outdir):
    """Handle PiP processing - one PiP effect per overlay"""
    rows = int(request.POST.get("pip_rows") or 0)
    pip_results = []
    status_messages = []
    
    current_base = base_path
    for i in range(rows):
        pip_data = extract_pip_data(request, i, video_dur, updir)
        if pip_data:
            result = apply_single_pip_effect(current_base, pip_data, outdir)
            current_base = result  # Use this result as input for next iteration
            pip_results.append(result)
            status_messages.append(f"+ PiP row {i+1}: {pip_data['start']:.2f}s for {pip_data['duration']:.2f}s")
    
    return pip_results, status_messages

def extract_pip_data(request, row_index, video_dur, updir):
    """Extract PiP data for a single row"""
    enabled = request.POST.get(f"pip_enable_{row_index}") == "on"
    if not enabled:
        return None
    
    try:
        start = float(request.POST.get(f"pip_start_{row_index}") or 0)
        duration = float(request.POST.get(f"pip_dur_{row_index}") or 0)
    except (ValueError, TypeError):
        return None
    
    # Clamp to video duration
    start = max(0.0, min(start, video_dur))
    duration = max(0.0, min(duration, max(0.0, video_dur - start)))
    
    if duration <= 0:
        return None
    
    # Handle overlay file
    overlay_file = request.FILES.get(f"pip_overlay_{row_index}")
    overlay_path = None
    if overlay_file:
        overlay_path = updir / f"{uuid.uuid4()}_{overlay_file.name}"
        with open(overlay_path, "wb") as f:
            for chunk in overlay_file.chunks():
                f.write(chunk)
    
    # Extract zoom direction and timing
    zoom_direction = request.POST.get(f"pip_zoom_direction_{row_index}")
    zoom_start = request.POST.get(f"pip_zoom_start_{row_index}")
    zoom_end = request.POST.get(f"pip_zoom_end_{row_index}")
    
    # Convert zoom times to float if they exist
    zoom_start_float = None
    zoom_end_float = None
    if zoom_start:
        try:
            zoom_start_float = float(zoom_start)
        except (ValueError, TypeError):
            pass
    if zoom_end:
        try:
            zoom_end_float = float(zoom_end)
        except (ValueError, TypeError):
            pass
    
    return {
        'start': start,
        'duration': duration,
        'overlay_path': overlay_path,
        'row_index': row_index,
        'zoom_direction': zoom_direction,
        'zoom_start': zoom_start_float,
        'zoom_end': zoom_end_float
    }

def apply_single_pip_effect(base_path, pip_data, outdir):
    """Apply a single PiP effect - direct control, no black box"""
    out_path = outdir / f"{uuid.uuid4()}.mp4"
    

    
    # Pass zoom data to apply_shrink_pip for processing
    apply_shrink_pip(
        base_path=base_path,
        out_path=out_path,
        start_sec=pip_data['start'],
        dur_sec=pip_data['duration'],
        overlay_path=pip_data['overlay_path'],
        fade_in=1.0,
        fade_out=1.0,
        zoom_direction=pip_data.get('zoom_direction'),
        zoom_start=pip_data.get('zoom_start'),
        zoom_end=pip_data.get('zoom_end'),
    )
    
    return out_path

@csrf_exempt
def render_video(request):
    ctx = {}

    # tiny helper to append status lines
    def add_status(msg: str):
        ctx["broll_hits"] = (ctx.get("broll_hits") + "\n" if ctx.get("broll_hits") else "") + msg

    try:
        updir = Path(settings.MEDIA_ROOT) / "uploads"
        outdir = Path(settings.MEDIA_ROOT) / "outputs"
        updir.mkdir(parents=True, exist_ok=True)
        outdir.mkdir(parents=True, exist_ok=True)

        # 1. Process main video
        base_path, video_dur = process_main_video(request, updir)
        # Get the media file for database saving
        media = request.FILES.get("media")
        
        # 2. Process B-roll clips
        out_path, broll_status, broll_segs = process_broll_clips(request, base_path, video_dur, updir, outdir)
        add_status(broll_status)
        
        # 3. Process PiP clips (one PiP effect per overlay)
        pip_results, pip_status_messages = process_pip_clips(request, out_path, video_dur, updir, outdir)
        for status_msg in pip_status_messages:
            add_status(status_msg)
        
        # Update out_path to the last PiP result if any were processed
        if pip_results:
            out_path = pip_results[-1]

        # ---- OPTIONAL BURN-IN CAPTIONS ----
        enable_captions = request.POST.get("enable_captions") == "on"
        if enable_captions:
            try:
                # Transcribe from the original base (same audio)
                srt_path = transcribe_to_srt(base_path)

                # Burn captions onto the just-rendered video (out_path) -> final_path
                final_path = outdir / f"{uuid.uuid4()}.mp4"
                burn_in_subtitles(out_path, srt_path, final_path)

                # Serve the captioned file
                out_path = final_path
                add_status("+ Burn-in captions added")
            except Exception as cap_err:
                prev = ctx.get("error") or ""
                msg = f"Captions skipped: {cap_err}"
                ctx["error"] = prev + ("\n" if prev else "") + msg
        else:
            add_status("Captions disabled by user")

        # Done
        ctx["output_url"] = f'{settings.MEDIA_URL}outputs/{out_path.name}'

        title = request.POST.get("title")
        if not title:
            ctx["error"] = "Title is required."
            return render(request, "renderer/index.html", ctx)
        
        # Add title to context for submit button
        ctx["rendered_title"] = title

        # Prepare data for signal
        broll_files = request.FILES.getlist("broll_file")
        broll_starts = request.POST.getlist("broll_start")
        broll_durations = request.POST.getlist("broll_dur")
        pip_rows = int(request.POST.get("pip_rows") or 0)
        
        # Send signal when render button is clicked (before saving data)
        pip_clips_data = []
        for i in range(pip_rows):
            enabled = request.POST.get(f"pip_enable_{i}") == "on"
            if enabled:
                start = float(request.POST.get(f"pip_start_{i}") or 0)
                duration = float(request.POST.get(f"pip_dur_{i}") or 0)
                overlay = request.FILES.get(f"pip_overlay_{i}")
                zoom_direction = request.POST.get(f"pip_zoom_direction_{i}")
                zoom_start = request.POST.get(f"pip_zoom_start_{i}")
                zoom_end = request.POST.get(f"pip_zoom_end_{i}")
                pip_clips_data.append((start, duration, overlay, zoom_direction, zoom_start, zoom_end))
        
        render_clicked.send(
            sender=render_video, 
            title=title, 
            main_video=str(base_path), 
            broll_clips=[(file, start, duration) for file, start, duration in zip(broll_files, broll_starts, broll_durations)], 
            pip_clips=pip_clips_data
        )

        # Save the InputData
        input_data = InputData.objects.create(title=title, main_video=media)

        # Save PiP clips
        for i in range(pip_rows):
            enabled = request.POST.get(f"pip_enable_{i}") == "on"
            if not enabled:
                continue
                
            try:
                start = float(request.POST.get(f"pip_start_{i}") or 0)
                duration = float(request.POST.get(f"pip_dur_{i}") or 0)
            except ValueError:
                continue
                
            if duration <= 0:
                continue
                
            overlay = request.FILES.get(f"pip_overlay_{i}")
            zoom_direction = request.POST.get(f"pip_zoom_direction_{i}")
            zoom_start = request.POST.get(f"pip_zoom_start_{i}")
            zoom_end = request.POST.get(f"pip_zoom_end_{i}")
            
            # Convert zoom times to float if they exist
            zoom_start_float = None
            zoom_end_float = None
            if zoom_start:
                try:
                    zoom_start_float = float(zoom_start)
                except (ValueError, TypeError):
                    pass
            if zoom_end:
                try:
                    zoom_end_float = float(zoom_end)
                except (ValueError, TypeError):
                    pass
            
            PiPClip.objects.create(
                input_data=input_data, 
                start=start, 
                duration=duration, 
                overlay=overlay,
                zoom_direction=zoom_direction,
                zoom_start=zoom_start_float,
                zoom_end=zoom_end_float
            )

        # Save B-roll clips using the saved file paths from segments
        for seg in broll_segs:
            # Get relative path from MEDIA_ROOT for the FileField
            relative_path = seg.clip_path.relative_to(Path(settings.MEDIA_ROOT))
            BrollClip.objects.create(
                input_data=input_data, 
                file=str(relative_path),
                start=seg.t0, 
                duration=(seg.t1 - seg.t0)
            )

        ctx["input_data_id"] = input_data.id

        return render(request, "renderer/index.html", ctx)

    except Exception as e:
        ctx["error"] = str(e)
        return render(request, "renderer/index.html", ctx)

@csrf_exempt
def submit_completed_video(request):
    """Handle submission of completed video to InputData"""
    if request.method == "POST":
        title = request.POST.get("title")
        video_url = request.POST.get("video_url")
        
        # Get preproduction videos for the template
        preproduction_videos = PreProduction.objects.all()
        
        if not title or not video_url:
            return render(request, "renderer/index.html", {
                "error": "Missing title or video URL",
                "preproduction_videos": preproduction_videos
            })
        
        # Extract the file path from the URL
        # video_url format: /media/outputs/filename.mp4
        video_path = video_url.replace(settings.MEDIA_URL, '')
        
        try:
            # Find the InputData by title
            input_data = InputData.objects.filter(title=title).order_by('-created_at').first()
            
            if input_data:
                # Update the completed_video field
                input_data.completed_video = video_path
                input_data.save()
                
                # Return success
                return render(request, "renderer/index.html", {
                    "output_url": video_url,
                    "rendered_title": title,
                    "submit_success": True,
                    "broll_hits": f"Completed video saved for: {title}",
                    "preproduction_videos": preproduction_videos
                })
            else:
                return render(request, "renderer/index.html", {
                    "error": f"Could not find InputData with title: {title}",
                    "preproduction_videos": preproduction_videos
                })
        
        except Exception as e:
            return render(request, "renderer/index.html", {
                "error": f"Error saving completed video: {str(e)}",
                "preproduction_videos": preproduction_videos
            })
    
    # If not POST, redirect to index
    from django.shortcuts import redirect
    return redirect('index')
