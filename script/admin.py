from django.contrib import admin
from .models import SystemInstruction, Conversation, Message

admin.site.register(SystemInstruction)
admin.site.register(Conversation)
admin.site.register(Message)
