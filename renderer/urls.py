from django.urls import path
from .views import index, explainer_video, render_video

app_name = 'renderer'

urlpatterns = [
    path('', index, name='index'),
    path('explainer/', explainer_video, name='explainer_video'),
    path('render/', render_video, name='render_video'),
]
