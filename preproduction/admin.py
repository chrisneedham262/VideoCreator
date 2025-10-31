from django.contrib import admin
from .models import PreProduction

# Register your models here.

@admin.register(PreProduction)
class PreProductionAdmin(admin.ModelAdmin):
    list_display = ('title', 'completed', 'created_at', 'updated_at', 'main_video', 'pip_video')
    list_filter = ('completed', 'created_at', 'updated_at')
    search_fields = ('title',)
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('completed',)
    
    fieldsets = (
        ('Video Information', {
            'fields': ('title', 'main_video', 'pip_video', 'completed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
