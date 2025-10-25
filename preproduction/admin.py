from django.contrib import admin
from .models import PreProduction

# Register your models here.

@admin.register(PreProduction)
class PreProductionAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'updated_at', 'pip_video')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Video Information', {
            'fields': ('title', 'pip_video')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
