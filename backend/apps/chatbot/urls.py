"""
Django URL Configuration for Chatbot App

복사 위치: backend/apps/chatbot/urls.py
"""

from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # 채팅
    path('chat/', views.chat, name='chat'),

    # 세션 관리
    path('sessions/', views.get_sessions, name='sessions'),
    path('sessions/<int:session_id>/', views.get_session_history, name='session-history'),
    path('sessions/<int:session_id>/delete/', views.delete_session, name='delete-session'),

    # 북마크
    path('bookmarks/', views.get_bookmarks, name='bookmarks'),
    path('bookmark/', views.create_bookmark, name='create-bookmark'),
    path('bookmark/<int:bookmark_id>/', views.delete_bookmark, name='delete-bookmark'),

    # 개인화 API (신규)
    path('analytics/', views.chatbot_analytics, name='chatbot-analytics'),
    path('history/', views.chatbot_history, name='chatbot-history'),
    path('feedback/', views.chatbot_feedback, name='chatbot-feedback'),
]
