from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .models import PreProduction

@csrf_exempt
@require_http_methods(["POST"])
def toggle_completed(request, video_id):
    """Toggle the completed status of a PreProduction video"""
    try:
        video = get_object_or_404(PreProduction, id=video_id)
        
        # Parse JSON body
        data = json.loads(request.body)
        completed = data.get('completed', False)
        
        # Update the completed status
        video.completed = completed
        video.save()
        
        return JsonResponse({
            'success': True,
            'completed': video.completed
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
