"""
Django Admin Configuration for Chatbot App
"""
from django.contrib import admin
from .models import ChatSession, ChatMessage, ChatBookmark


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    """Chat Session Admin"""
    list_display = ['id', 'user', 'title', 'created_at', 'updated_at', 'message_count']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['title', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'

    def message_count(self, obj):
        """Get message count"""
        return obj.messages.count()
    message_count.short_description = 'Message Count'


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    """Chat Message Admin"""
    list_display = ['id', 'session', 'role', 'content_preview', 'created_at', 'has_sources']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'session__title']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        """Content preview"""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'

    def has_sources(self, obj):
        """Check if has sources"""
        return len(obj.sources) > 0
    has_sources.short_description = 'Has Sources'
    has_sources.boolean = True


@admin.register(ChatBookmark)
class ChatBookmarkAdmin(admin.ModelAdmin):
    """Chat Bookmark Admin"""
    list_display = ['id', 'user', 'content_preview', 'created_at', 'has_sources']
    list_filter = ['created_at']
    search_fields = ['content', 'user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'

    def content_preview(self, obj):
        """Content preview"""
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'

    def has_sources(self, obj):
        """Check if has sources"""
        return len(obj.sources) > 0
    has_sources.short_description = 'Has Sources'
    has_sources.boolean = True
