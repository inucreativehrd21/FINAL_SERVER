"""
Django REST API Views for Chatbot App (개선 버전)

RunPod RAG 시스템과 통합된 챗봇 API - 환경변수 호환성 개선

복사 위치: backend/apps/chatbot/views.py
"""

import os
import logging
import requests

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ChatSession, ChatMessage, ChatBookmark
from .serializers import (
    ChatSessionSerializer,
    ChatSessionListSerializer,
    ChatMessageSerializer,
    ChatBookmarkSerializer
)

logger = logging.getLogger(__name__)

# RunPod RAG 서버 URL (환경변수에서 로드)
# RUNPOD_RAG_URL 또는 RUNPOD_CHATBOT_URL 지원
RUNPOD_RAG_URL = (
    os.environ.get('RUNPOD_RAG_URL') or
    os.environ.get('RUNPOD_CHATBOT_URL', '')
)

if not RUNPOD_RAG_URL:
    logger.warning("⚠️  RUNPOD_RAG_URL or RUNPOD_CHATBOT_URL environment variable not set!")


# === 채팅 API ===

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat(request):
    """
    사용자 질문 → RunPod RAG → DB 저장

    Request Body:
        {
            "message": "질문 내용",
            "session_id": 123  # optional (없으면 새 세션 생성)
        }

    Response:
        {
            "success": true,
            "session_id": 123,
            "message_id": 456,
            "data": {
                "response": "답변 내용",
                "sources": [...]
            }
        }
    """
    message = request.data.get('message')
    session_id = request.data.get('session_id')

    # 입력 검증
    if not message:
        return Response({
            'success': False,
            'error': '메시지가 없습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 1. 채팅 세션 조회 또는 생성
    if session_id:
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            logger.info(f"[Chat] Using existing session: {session.id}")
        except ChatSession.DoesNotExist:
            return Response({
                'success': False,
                'error': '세션을 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)
    else:
        # 새 세션 생성
        session = ChatSession.objects.create(
            user=request.user,
            title=message[:100]  # 첫 질문을 제목으로
        )
        logger.info(f"[Chat] New session created: {session.id}")

    # 2. 사용자 메시지 저장
    user_message = ChatMessage.objects.create(
        session=session,
        role='user',
        content=message
    )
    logger.info(f"[Chat] User message saved: {user_message.id}")

    # 3. 채팅 히스토리 구성 (최근 10개 메시지)
    recent_messages = session.messages.order_by('created_at')[:10]
    chat_history = []
    for msg in recent_messages:
        if msg.id != user_message.id:  # 현재 메시지 제외
            chat_history.append({
                "role": msg.role,
                "content": msg.content
            })

    # 4. RunPod RAG 서버 확인
    if not RUNPOD_RAG_URL:
        return Response({
            'success': False,
            'error': 'RAG 서버가 설정되지 않았습니다. 관리자에게 문의하세요.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 5. RunPod RAG 호출
    payload = {
        'question': message,
        'user_id': str(request.user.id),
        'chat_history': chat_history,
        'session_id': str(session.id)
    }

    try:
        logger.info(f"[Chat] Calling RunPod RAG: {RUNPOD_RAG_URL}")

        response = requests.post(
            f"{RUNPOD_RAG_URL}/api/v1/chat",
            json=payload,
            timeout=90  # LangGraph RAG는 7-10초 소요
        )

        # 응답 처리
        if response.status_code == 200:
            result = response.json()

            if result.get('success'):
                # 6. AI 응답 메시지 저장
                assistant_message = ChatMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=result.get('answer', ''),
                    sources=result.get('sources', []),
                    metadata=result.get('metadata', {})
                )

                logger.info(
                    f"[Chat] Response saved: message_id={assistant_message.id}, "
                    f"sources={len(result.get('sources', []))}, "
                    f"rag_type={result.get('metadata', {}).get('rag_type', 'unknown')}"
                )

                return Response({
                    'success': True,
                    'session_id': session.id,
                    'message_id': assistant_message.id,
                    'data': {
                        'response': result.get('answer'),
                        'sources': result.get('sources', [])
                    }
                })
            else:
                # RAG 서버에서 에러 반환
                error_msg = result.get('error', 'RAG 서버에서 오류가 발생했습니다.')
                logger.error(f"[Chat] RAG server error: {error_msg}")
                return Response({
                    'success': False,
                    'error': error_msg
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # HTTP 상태 코드 에러
            logger.error(f"[Chat] RAG server returned HTTP {response.status_code}")
            return Response({
                'success': False,
                'error': f'RAG 서버 오류 (HTTP {response.status_code})'
            }, status=status.HTTP_502_BAD_GATEWAY)

    except requests.exceptions.Timeout:
        logger.error("[Chat] RAG server timeout (90s)")
        return Response({
            'success': False,
            'error': 'RAG 서버 응답 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.'
        }, status=status.HTTP_504_GATEWAY_TIMEOUT)

    except requests.exceptions.ConnectionError:
        logger.error("[Chat] RAG server connection error")
        return Response({
            'success': False,
            'error': 'RAG 서버에 연결할 수 없습니다. 관리자에게 문의하세요.'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    except Exception as e:
        logger.exception(f"[Chat] Unexpected error: {e}")
        return Response({
            'success': False,
            'error': '서버 오류가 발생했습니다.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# === 세션 관리 API ===

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sessions(request):
    """사용자의 모든 채팅 세션 조회"""
    sessions = ChatSession.objects.filter(user=request.user)
    serializer = ChatSessionListSerializer(sessions, many=True)
    return Response({
        'success': True,
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_history(request, session_id):
    """특정 세션의 채팅 내역 조회"""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        serializer = ChatSessionSerializer(session)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except ChatSession.DoesNotExist:
        return Response({
            'success': False,
            'error': '세션을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    """채팅 세션 삭제"""
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.delete()
        logger.info(f"[Session] Deleted: session_id={session_id}, user={request.user.id}")
        return Response({
            'success': True,
            'message': '세션이 삭제되었습니다.'
        })
    except ChatSession.DoesNotExist:
        return Response({
            'success': False,
            'error': '세션을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)


# === 북마크 API ===

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bookmarks(request):
    """사용자의 모든 북마크 조회"""
    bookmarks = ChatBookmark.objects.filter(user=request.user)
    serializer = ChatBookmarkSerializer(bookmarks, many=True)
    return Response({
        'success': True,
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_bookmark(request):
    """북마크 생성"""
    content = request.data.get('content')
    sources = request.data.get('sources', [])

    if not content:
        return Response({
            'success': False,
            'error': '내용이 없습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    bookmark = ChatBookmark.objects.create(
        user=request.user,
        content=content,
        sources=sources
    )

    logger.info(f"[Bookmark] Created: bookmark_id={bookmark.id}, user={request.user.id}")

    serializer = ChatBookmarkSerializer(bookmark)
    return Response({
        'success': True,
        'data': serializer.data
    }, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_bookmark(request, bookmark_id):
    """북마크 삭제"""
    try:
        bookmark = ChatBookmark.objects.get(id=bookmark_id, user=request.user)
        bookmark.delete()
        logger.info(f"[Bookmark] Deleted: bookmark_id={bookmark_id}, user={request.user.id}")
        return Response({
            'success': True,
            'message': '북마크가 삭제되었습니다.'
        })
    except ChatBookmark.DoesNotExist:
        return Response({
            'success': False,
            'error': '북마크를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
