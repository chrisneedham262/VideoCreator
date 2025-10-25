from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.


class PiPClip(models.Model):
    input_data = models.ForeignKey('InputData', related_name='pip_clips', on_delete=models.CASCADE)
    start = models.FloatField()
    duration = models.FloatField()
    overlay = models.FileField(upload_to='uploads/', max_length=500, null=True, blank=True)
    zoom_direction = models.CharField(max_length=10, null=True, blank=True, choices=[
        ('', 'No zoom'),
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right'),
    ])
    zoom_start = models.FloatField(null=True, blank=True)
    zoom_end = models.FloatField(null=True, blank=True)

class BrollClip(models.Model):
    input_data = models.ForeignKey('InputData', related_name='broll_clips', on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/', max_length=500)
    start = models.FloatField()
    duration = models.FloatField()

class InputData(models.Model):
    title = models.CharField(max_length=255)
    main_video = models.FileField(upload_to='uploads/', max_length=500)
    completed_video = models.FileField(upload_to='outputs/', max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.title

# Signal to log when InputData is created
@receiver(post_save, sender=InputData)
def log_input_data_creation(sender, instance, created, **kwargs):
    if created:
        print(f"InputData created: {instance}")

# Signal to log when PiPClip is created
@receiver(post_save, sender=PiPClip)
def log_pip_clip_creation(sender, instance, created, **kwargs):
    if created:
        print(f"PiPClip created: {instance}")

# Signal to log when BrollClip is created
@receiver(post_save, sender=BrollClip)
def log_broll_clip_creation(sender, instance, created, **kwargs):
    if created:
        print(f"BrollClip created: {instance}")
