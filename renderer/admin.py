from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .models import InputData, PiPClip, BrollClip

class PiPClipInline(admin.TabularInline):
    model = PiPClip
    extra = 1
    fields = ('start', 'duration', 'overlay', 'zoom_direction', 'zoom_start', 'zoom_end', 'edit_link')
    readonly_fields = ('edit_link',)
    
    def edit_link(self, obj):
        if obj.pk:
            # Create a custom URL for editing
            return format_html(
                '<a href="/admin/renderer/pipclip/{}/change/" target="_blank">Edit PiP Clip</a>',
                obj.pk
            )
        return "Save to edit"
    edit_link.short_description = "Edit"

class BrollClipInline(admin.TabularInline):
    model = BrollClip
    extra = 1
    fields = ('file', 'start', 'duration', 'edit_link')
    readonly_fields = ('edit_link',)
    
    def edit_link(self, obj):
        if obj.pk:
            # Create a custom URL for editing
            return format_html(
                '<a href="/admin/renderer/brollclip/{}/change/" target="_blank">Edit Broll Clip</a>',
                obj.pk
            )
        return "Save to edit"
    edit_link.short_description = "Edit"

class InputDataAdmin(admin.ModelAdmin):
    list_display = ('title', 'completed_video', 'created_at')
    inlines = [PiPClipInline, BrollClipInline]
    search_fields = ('title',)
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

# Hidden admin classes for PiPClip and BrollClip
class PiPClipAdmin(admin.ModelAdmin):
    list_display = ('input_data', 'start', 'duration', 'overlay', 'zoom_direction', 'zoom_start', 'zoom_end')
    list_filter = ('input_data', 'zoom_direction')

class BrollClipAdmin(admin.ModelAdmin):
    list_display = ('input_data', 'file', 'start', 'duration')
    list_filter = ('input_data',)

# Register only InputDataAdmin - this will show only InputData in the admin interface
admin.site.register(InputData, InputDataAdmin)

# Register the related models but hide them from the admin index
admin.site.register(PiPClip, PiPClipAdmin)
admin.site.register(BrollClip, BrollClipAdmin)

# Hide PiPClip and BrollClip from the admin index
# This uses Django's built-in mechanism to hide models from the admin index
admin.site._registry[PiPClip].has_module_permission = lambda request: False
admin.site._registry[BrollClip].has_module_permission = lambda request: False
