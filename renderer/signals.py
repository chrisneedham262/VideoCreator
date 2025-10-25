from django.dispatch import Signal
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .models import InputData, PiPClip, BrollClip
from django.dispatch import receiver

# Signal to be sent when the render button is clicked
render_clicked = Signal()

@receiver(render_clicked)
def handle_render_clicked(sender, title, main_video, broll_clips, pip_clips, **kwargs):
    # Log the render action - data is already saved in the view
    print(f"Render clicked for: {title}")
    print(f"Main video: {main_video}")
    print(f"B-roll clips: {len(broll_clips)}")
    print(f"PiP clips: {len(pip_clips)}")
    
    # Log PiP clip details including zoom data
    for i, pip_clip in enumerate(pip_clips):
        if len(pip_clip) >= 6:  # New format with zoom data
            start, duration, overlay, zoom_direction, zoom_start, zoom_end = pip_clip
            print(f"  PiP {i+1}: {start}s for {duration}s, zoom: {zoom_direction} ({zoom_start}s-{zoom_end}s)")
        else:  # Old format
            start, duration, overlay = pip_clip
            print(f"  PiP {i+1}: {start}s for {duration}s")
    
    # You can add additional logic here like sending notifications,
    # logging to external services, etc.
