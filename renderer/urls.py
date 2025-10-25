from django.urls import path
from .views import index, render_video, submit_completed_video

urlpatterns = [
    path('', index, name='index'),
    path('render/', render_video, name='render_video'),
    path('submit-completed/', submit_completed_video, name='submit_completed_video'),
]
