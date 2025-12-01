"""
Django Models for Chatbot App

통합 RAG 챗봇 DB 모델
- ChatSession: 채팅 세션 관리
- ChatMessage: 사용자/AI 메시지
- ChatBookmark: 북마크 기능

복사 위치: backend/apps/chatbot/models.py
"""

from django.db import models
from django.conf import settings


class ChatSession(models.Model):
    """채팅 세션"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        verbose_name='사용자'
    )
    title = models.CharField(max_length=255, verbose_name='세션 제목')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일시')

    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['-updated_at']),
            models.Index(fields=['user', '-updated_at']),
        ]
        verbose_name = '채팅 세션'
        verbose_name_plural = '채팅 세션 목록'

    def __str__(self):
        return f"{self.user.username} - {self.title}"


class ChatMessage(models.Model):
    """채팅 메시지"""
    ROLE_CHOICES = (
        ('user', '사용자'),
        ('assistant', 'AI'),
    )

    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='세션'
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        verbose_name='역할'
    )
    content = models.TextField(verbose_name='메시지 내용')
    sources = models.JSONField(
        default=list,
        blank=True,
        verbose_name='참고 문서',
        help_text='RAG에서 검색된 참고 문서 목록'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='메타데이터',
        help_text='RAG 타입, 응답 시간 등 추가 정보'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['role']),
        ]
        verbose_name = '채팅 메시지'
        verbose_name_plural = '채팅 메시지 목록'

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class ChatBookmark(models.Model):
    """채팅 북마크"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_bookmarks',
        verbose_name='사용자'
    )
    message = models.ForeignKey(
        ChatMessage,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='원본 메시지'
    )
    content = models.TextField(verbose_name='북마크 내용')
    sources = models.JSONField(
        default=list,
        blank=True,
        verbose_name='참고 문서'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        db_table = 'chat_bookmarks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
        verbose_name = '채팅 북마크'
        verbose_name_plural = '채팅 북마크 목록'

    def __str__(self):
        return f"{self.user.username} - {self.content[:50]}..."
