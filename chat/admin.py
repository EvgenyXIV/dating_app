from django.contrib import admin
from .models import ChatRoom, ChatMessage


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ["user1", "user2", "created_at", "is_active"]
    list_filter = ["is_active", "created_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["room", "user", "message", "created_at", "is_read"]
    list_filter = ["is_read", "created_at"]
