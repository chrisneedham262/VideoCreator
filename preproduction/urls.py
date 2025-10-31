from django.urls import path
from . import views

urlpatterns = [
    path('toggle-completed/<int:video_id>/', views.toggle_completed, name='toggle_completed'),
]

