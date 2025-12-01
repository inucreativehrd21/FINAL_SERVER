"""
Django REST Framework Serializers for Chatbot App

복사 위치: backend/apps/chatbot/serializers.py
"""

from rest_framework import serializers
from .models import ChatSession, ChatMessage, ChatBookmark


class ChatMessageSerializer(serializers.ModelSerializer):
    """채팅 메시지 시리얼라이저"""

    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'role',
            'content',
            'sources',
            'metadata',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """채팅 세션 시리얼라이저 (메시지 포함)"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'title',
            'messages',
            'message_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        """메시지 개수 반환"""
        return obj.messages.count()


class ChatSessionListSerializer(serializers.ModelSerializer):
    """채팅 세션 목록용 시리얼라이저 (메시지 제외)"""
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = [
            'id',
            'title',
            'message_count',
            'last_message',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        """메시지 개수 반환"""
        return obj.messages.count()

    def get_last_message(self, obj):
        """마지막 메시지 반환"""
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'role': last_msg.role,
                'content': last_msg.content[:100],
                'created_at': last_msg.created_at
            }
        return None


class ChatBookmarkSerializer(serializers.ModelSerializer):
    """북마크 시리얼라이저"""

    class Meta:
        model = ChatBookmark
        fields = [
            'id',
            'content',
            'sources',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
