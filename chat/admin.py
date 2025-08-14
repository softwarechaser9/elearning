from django.contrib import admin
from .models import ChatRoom, ChatRoomMembership, ChatMessage, PrivateChat, PrivateMessage


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'created_by', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at', 'course']
    search_fields = ['name', 'description', 'course__title']
    filter_horizontal = ['participants']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatRoomMembership)
class ChatRoomMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'joined_at', 'is_active']
    list_filter = ['is_active', 'joined_at']
    search_fields = ['user__username', 'room__name']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['user', 'room', 'content_preview', 'message_type', 'created_at', 'is_edited']
    list_filter = ['message_type', 'is_edited', 'created_at', 'room']
    search_fields = ['content', 'user__username', 'room__name']
    readonly_fields = ['created_at', 'edited_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(PrivateChat)
class PrivateChatAdmin(admin.ModelAdmin):
    list_display = ['participant1', 'participant2', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['participant1__username', 'participant2__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'chat', 'content_preview', 'message_type', 'created_at', 'is_read']
    list_filter = ['message_type', 'is_read', 'is_edited', 'created_at']
    search_fields = ['content', 'sender__username']
    readonly_fields = ['created_at', 'edited_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'
