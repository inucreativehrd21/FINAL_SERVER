"""
Celery Tasks for Coding Test App

Keep-Alive 핑 등 백그라운드 작업을 정의합니다.

설정:
1. Celery Beat 스케줄 설정 (settings.py 또는 celery.py):
   CELERY_BEAT_SCHEDULE = {
       'runpod-keep-alive': {
           'task': 'apps.coding_test.tasks.keep_runpod_warm',
           'schedule': timedelta(minutes=5),
       },
   }

2. Celery Worker 및 Beat 실행:
   celery -A config worker -l info
   celery -A config beat -l info
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# Celery 가용 여부 확인
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    # Celery 없을 때 더미 데코레이터
    def shared_task(func):
        return func


@shared_task
def keep_runpod_warm():
    """
    Runpod Keep-Alive 핑 태스크

    5분마다 실행되어 Runpod 컨테이너를 warm 상태로 유지합니다.
    Cold Start를 방지하여 사용자 경험을 개선합니다.
    """
    from .hint_proxy import ping_runpod, is_runpod_available

    if not is_runpod_available():
        logger.warning("[KeepAlive] Runpod 설정이 없습니다. 태스크를 건너뜁니다.")
        return {"skipped": True, "reason": "Runpod not configured"}

    try:
        result = ping_runpod()

        if result.get('success'):
            logger.info(f"[KeepAlive] Runpod 핑 성공: {datetime.now()}")
            return {"success": True, "timestamp": str(datetime.now())}
        else:
            logger.warning(f"[KeepAlive] Runpod 핑 실패: {result.get('error')}")
            return {"success": False, "error": result.get('error')}

    except Exception as e:
        logger.error(f"[KeepAlive] 오류: {str(e)}")
        return {"success": False, "error": str(e)}


@shared_task
def cleanup_old_hints(days: int = 30):
    """
    오래된 힌트 기록 정리 태스크

    Args:
        days: 보관 기간 (기본 30일)
    """
    from datetime import timedelta
    from django.utils import timezone
    from .models import HintRequest

    try:
        cutoff_date = timezone.now() - timedelta(days=days)
        deleted_count, _ = HintRequest.objects.filter(
            created_at__lt=cutoff_date
        ).delete()

        logger.info(f"[Cleanup] {deleted_count}개의 오래된 힌트 기록 삭제됨")
        return {"deleted": deleted_count}

    except Exception as e:
        logger.error(f"[Cleanup] 오류: {str(e)}")
        return {"error": str(e)}


# 수동 실행용 함수 (Celery 없이 테스트할 때)
def manual_keep_alive():
    """Celery 없이 수동으로 Keep-Alive 실행"""
    from .hint_proxy import ping_runpod, is_runpod_available

    if not is_runpod_available():
        print("[KeepAlive] Runpod 설정이 없습니다.")
        return

    result = ping_runpod()
    print(f"[KeepAlive] 결과: {result}")
    return result
