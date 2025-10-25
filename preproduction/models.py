from django.db import models

# Create your models here.

class PreProduction(models.Model):
    """
    Model for storing pre-production videos and titles
    that will be used in the video production workflow
    """
    title = models.CharField(max_length=255, help_text="Title for the pre-production video")
    pip_video = models.FileField(
        upload_to='preproduction/', 
        help_text="Pre-production PiP video file"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Date and time when this was created")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last updated")
    
    class Meta:
        ordering = ['-created_at']  # Latest first
        verbose_name = "Pre-Production Video"
        verbose_name_plural = "Pre-Production Videos"
    
    def __str__(self):
        return f"{self.title} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
