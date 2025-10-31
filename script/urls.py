from django.urls import path
from . import views

app_name = 'script'

urlpatterns = [
    path('', views.prompts_view, name='prompts'),
    path('delete/<int:message_id>/', views.delete_message, name='delete_message'),
]

