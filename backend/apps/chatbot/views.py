"""
Django REST API Views for Chatbot App (개선 버전)

RunPod RAG 시스템과 통합된 챗봇 API - 환경변수 호환성 개선

복사 위치: backend/apps/chatbot/views.py
"""

import os
import logging
import requests
from datetime import datetime, timedelta

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Count

from .models import ChatSession, ChatMessage, ChatBookmark
from .serializers import (
    ChatSessionSerializer,
    ChatSessionListSerializer,
    ChatMessageSerializer,
    ChatBookmarkSerializer
)
# Import UserSurvey for personalization
from apps.coding_test.models import UserSurvey

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
        user=request.user,  # 개인화: user 필드 추가
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

    # 4-1. 개인화: UserSurvey에서 사용자 컨텍스트 가져오기
    user_context = {}
    try:
        survey = UserSurvey.objects.filter(user=request.user).first()
        if survey:
            # learning_goals와 interested_topics는 JSONField (list)
            # 문자열로 변환 (쉼표로 구분)
            learning_goals_str = ""
            interested_topics_str = ""

            if survey.learning_goals and isinstance(survey.learning_goals, list):
                learning_goals_str = ", ".join(survey.learning_goals)

            if survey.interested_topics and isinstance(survey.interested_topics, list):
                interested_topics_str = ", ".join(survey.interested_topics)

            user_context = {
                "learning_goals": learning_goals_str,
                "interested_topics": interested_topics_str,
            }
            logger.info(f"[Chat] User context loaded: learning_goals={bool(learning_goals_str)}, interested_topics={bool(interested_topics_str)}")
    except Exception as e:
        logger.warning(f"[Chat] Failed to load user context: {e}")
        # Continue without personalization if UserSurvey fails

    # 5. RunPod RAG 호출 (개인화 파라미터 추가)
    payload = {
        'question': message,
        'user_id': str(request.user.id),
        'user_context': user_context,  # NEW: 개인화 컨텍스트
        'enable_personalization': True,  # NEW: 개인화 활성화
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
                # 6. AI 응답 메시지 저장 (개인화 필드 추가)
                # 카테고리 자동 분류
                question_category = classify_question_category(message)

                # 개인화: related_questions 추출
                related_questions = result.get('related_questions', [])

                # metadata에 related_questions 저장
                metadata = result.get('metadata', {})
                metadata['related_questions'] = related_questions

                assistant_message = ChatMessage.objects.create(
                    session=session,
                    user=request.user,  # 개인화: user 필드 추가
                    role='assistant',
                    content=result.get('answer', ''),
                    sources=result.get('sources', []),
                    metadata=metadata,  # 개인화: related_questions 포함
                    category=question_category  # 개인화: category 자동 분류
                )

                logger.info(
                    f"[Chat] Response saved: message_id={assistant_message.id}, "
                    f"sources={len(result.get('sources', []))}, "
                    f"related_questions={len(related_questions)}, "
                    f"rag_type={result.get('metadata', {}).get('rag_type', 'unknown')}"
                )

                return Response({
                    'success': True,
                    'session_id': session.id,
                    'message_id': assistant_message.id,
                    'data': {
                        'response': result.get('answer'),
                        'sources': result.get('sources', []),
                        'related_questions': related_questions  # 개인화: 관련 질문 반환
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


# ===== 개인화 유틸리티 함수 =====

def classify_question_category(question: str) -> str:
    """
    질문 카테고리 자동 분류 (간단한 키워드 기반)
    
    Args:
        question: 사용자 질문
    
    Returns:
        str: 'git' | 'python' | 'general' | 'unknown'
    """
    question_lower = question.lower()
    
    git_keywords = [
        'git', 'github', 'commit', 'push', 'pull', 'branch',
        'merge', 'rebase', 'clone', 'checkout', 'stash', 'cherry-pick',
        '깃', '커밋', '브랜치', '머지', '리베이스'
    ]
    
    python_keywords = [
        'python', 'pip', 'def', 'class', 'import', 'list', 'dict',
        'pandas', 'numpy', 'django', 'flask', 'lambda', 'decorator',
        '파이썬', '리스트', '딕셔너리', '클래스', '함수'
    ]
    
    # Git 키워드 매칭
    if any(keyword in question_lower for keyword in git_keywords):
        return 'git'
    
    # Python 키워드 매칭
    elif any(keyword in question_lower for keyword in python_keywords):
        return 'python'
    
    # 일반 개발 관련 질문
    elif any(word in question_lower for word in ['code', 'error', 'debug', 'algorithm', '코드', '에러', '알고리즘']):
        return 'general'
    
    else:
        return 'unknown'


# ===== 개인화 통계 API =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatbot_analytics(request):
    """
    개인화 통계 API
    
    Query Params:
        days: 최근 N일 (기본: 30)
    
    Response:
        {
            "has_data": true,
            "peak_time": {...},
            "favorite_category": {...},
            "weekly_stats": {...},
            "category_stats": {...},
            "total_questions": 50,
            "avg_response_time": 3.2
        }
    """
    from django.db.models.functions import ExtractHour, TruncDate
    
    days = int(request.GET.get('days', 30))
    start_date = datetime.now() - timedelta(days=days)
    
    # 사용자의 AI 응답 메시지만 조회
    messages = ChatMessage.objects.filter(
        user=request.user,
        role='assistant',
        created_at__gte=start_date
    )
    
    if not messages.exists():
        return Response({
            'has_data': False,
            'message': '아직 챗봇 사용 기록이 없습니다.'
        })
    
    # 1. 시간대별 사용 빈도
    hour_stats = messages.annotate(
        hour=ExtractHour('created_at')
    ).values('hour').annotate(
        count=Count('id')
    ).order_by('-count')
    
    peak_hour = hour_stats.first() if hour_stats else None
    peak_time_data = None
    if peak_hour:
        hour = peak_hour['hour']
        hour_range = f"{hour:02d}:00-{hour+1:02d}:00"
        
        # 시간대 라벨 결정
        if 6 <= hour < 12:
            label = "오전"
        elif 12 <= hour < 18:
            label = "오후"
        elif 18 <= hour < 22:
            label = "저녁"
        else:
            label = "밤"
        
        peak_time_data = {
            'hour_range': hour_range,
            'label': label,
            'message': f"당신의 주 사용 시간: {label} ({hour_range})",
            'usage_count': peak_hour['count']
        }
    
    # 2. 카테고리별 통계
    category_stats_raw = messages.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    total_messages = messages.count()
    category_stats = {}
    favorite_category = None
    
    for cat in category_stats_raw:
        category_name = cat['category']
        count = cat['count']
        percentage = round((count / total_messages) * 100, 1)
        
        category_stats[category_name] = {
            'count': count,
            'percentage': percentage
        }
        
        if not favorite_category:
            # 가장 많이 사용한 카테고리
            category_display = dict(ChatMessage.CATEGORY_CHOICES).get(category_name, category_name)
            favorite_category = {
                'name': category_display,
                'message': f"가장 많이 질문한 주제: {category_display}"
            }
    
    # 3. 주간 통계
    week_ago = datetime.now() - timedelta(days=7)
    two_weeks_ago = datetime.now() - timedelta(days=14)
    
    this_week_count = messages.filter(created_at__gte=week_ago).count()
    last_week_count = messages.filter(
        created_at__gte=two_weeks_ago,
        created_at__lt=week_ago
    ).count()
    
    growth = 0
    if last_week_count > 0:
        growth = round(((this_week_count - last_week_count) / last_week_count) * 100, 1)
    elif this_week_count > 0:
        growth = 100.0
    
    weekly_stats = {
        'this_week': this_week_count,
        'last_week': last_week_count,
        'growth': growth,
        'message': f"이번 주 {this_week_count}개 질문 (지난주 대비 {'+' if growth >= 0 else ''}{growth}%)"
    }
    
    # 4. 평균 응답 시간 (metadata에서 추출)
    response_times = []
    for msg in messages:
        rt = msg.metadata.get('response_time')
        if rt:
            response_times.append(float(rt))
    
    avg_response_time = round(sum(response_times) / len(response_times), 1) if response_times else 0
    
    return Response({
        'has_data': True,
        'peak_time': peak_time_data,
        'favorite_category': favorite_category,
        'weekly_stats': weekly_stats,
        'category_stats': category_stats,
        'total_questions': total_messages,
        'avg_response_time': avg_response_time
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatbot_history(request):
    """
    채팅 기록 조회
    
    Query Params:
        limit: 최대 개수 (기본: 20)
        offset: 건너뛸 개수 (기본: 0)
        category: 카테고리 필터 (선택)
    
    Response:
        {
            "count": 50,
            "limit": 20,
            "offset": 0,
            "results": [...]
        }
    """
    limit = int(request.GET.get('limit', 20))
    offset = int(request.GET.get('offset', 0))
    category = request.GET.get('category')
    
    # 사용자의 AI 응답만 조회
    queryset = ChatMessage.objects.filter(
        user=request.user,
        role='assistant'
    )
    
    if category:
        queryset = queryset.filter(category=category)
    
    total_count = queryset.count()
    messages = queryset[offset:offset+limit]
    
    results = []
    for msg in messages:
        # 해당 메시지의 세션에서 바로 이전 user 메시지 찾기
        user_msg = ChatMessage.objects.filter(
            session=msg.session,
            role='user',
            created_at__lt=msg.created_at
        ).order_by('-created_at').first()
        
        question = user_msg.content if user_msg else ''
        
        results.append({
            'id': msg.id,
            'question': question,
            'answer': msg.content,
            'category': msg.category,
            'sources': msg.sources,
            'created_at': msg.created_at.isoformat(),
            'is_helpful': msg.is_helpful,
            'feedback_comment': msg.feedback_comment
        })
    
    return Response({
        'count': total_count,
        'limit': limit,
        'offset': offset,
        'results': results
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chatbot_feedback(request):
    """
    피드백 저장
    
    Request Body:
        {
            "message_id": 123,
            "is_helpful": true,
            "feedback_comment": "도움이 되었습니다!"  # 선택
        }
    
    Response:
        {
            "success": true,
            "message": "피드백이 저장되었습니다."
        }
    """
    message_id = request.data.get('message_id')
    is_helpful = request.data.get('is_helpful')
    feedback_comment = request.data.get('feedback_comment', '')
    
    if message_id is None:
        return Response({
            'success': False,
            'error': 'message_id가 필요합니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if is_helpful is None:
        return Response({
            'success': False,
            'error': 'is_helpful이 필요합니다.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        message = ChatMessage.objects.get(id=message_id, user=request.user)
        message.is_helpful = is_helpful
        message.feedback_comment = feedback_comment
        message.save()
        
        logger.info(f"[Feedback] Saved: message_id={message_id}, is_helpful={is_helpful}")
        
        return Response({
            'success': True,
            'message': '피드백이 저장되었습니다.'
        })
    except ChatMessage.DoesNotExist:
        return Response({
            'success': False,
            'error': '메시지를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)
