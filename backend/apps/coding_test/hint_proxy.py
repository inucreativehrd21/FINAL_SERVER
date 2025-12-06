"""
Hint Proxy - Runpod 힌트 서비스 호출 프록시

Django에서 Runpod Serverless로 힌트 요청을 전달하고 결과를 받아옵니다.
DB 접근이 필요한 작업(star_count 조회, HintRequest 저장)은 이 모듈에서 처리합니다.

사용법:
    from .hint_proxy import request_hint_via_runpod

    result = await request_hint_via_runpod(
        problem_id='1',
        user_code='print("hello")',
        user=request.user,
        preset='초급',
        custom_components={...}
    )
"""

import os
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from pathlib import Path

from django.conf import settings
from .models import HintRequest, ProblemStatus, Problem

logger = logging.getLogger(__name__)

# Runpod 설정
RUNPOD_ENDPOINT_ID = os.environ.get('RUNPOD_ENDPOINT_ID', '')
RUNPOD_API_KEY = os.environ.get('RUNPOD_API_KEY', '')
RUNPOD_BASE_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"
RUNPOD_HINT_URL = os.environ.get('RUNPOD_HINT_URL', '')

# 문제 데이터 캐시
_problems_cache = None


def _load_problems_data() -> List[Dict]:
    """문제 데이터 로드 (캐싱)"""
    global _problems_cache
    if _problems_cache is not None:
        return _problems_cache

    json_path = Path(__file__).parent / 'data' / 'problems_final_output.json'
    try:
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            _problems_cache = json.load(f)
        return _problems_cache
    except Exception as e:
        logger.error(f"문제 데이터 로드 실패: {e}")
        return []


def _get_problem_data(problem_id: str) -> Dict[str, Any]:
    """문제 ID로 문제 데이터 조회"""
    problems = _load_problems_data()
    for problem in problems:
        if str(problem.get('problem_id')) == str(problem_id):
            return {
                'title': problem.get('title', ''),
                'description': problem.get('description', ''),
                'solutions': problem.get('solutions', [])
            }
    return {'title': '', 'description': '', 'solutions': []}


def _get_star_count(user_id: int, problem_id: str) -> int:
    """사용자의 현재 별점 조회"""
    try:
        status = ProblemStatus.objects.filter(
            user_id=user_id,
            problem__problem_id=problem_id
        ).first()
        return status.star_count if status else 0
    except Exception as e:
        logger.error(f"별점 조회 실패: {e}")
        return 0


def _get_previous_hints(user_id: int, problem_id: str, limit: int = 5) -> List[str]:
    """이전 힌트 조회"""
    try:
        hints = HintRequest.objects.filter(
            user_id=user_id,
            problem_str_id=problem_id  # 모델 필드명에 맞게 수정
        ).order_by('-created_at')[:limit]

        return [h.hint_response for h in hints if h.hint_response]  # 모델 필드명에 맞게 수정
    except Exception as e:
        logger.error(f"이전 힌트 조회 실패: {e}")
        return []


def _call_runpod(payload: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    """Runpod HTTP Flask 서버 호출"""
    if not RUNPOD_HINT_URL:
        raise ValueError("Runpod 설정이 없습니다. RUNPOD_HINT_URL 환경변수를 설정하세요.")

    headers = {
        "Content-Type": "application/json"
    }

    # HTTP Flask 서버 엔드포인트
    url = f"{RUNPOD_HINT_URL}/hint"

    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response.raise_for_status()

        result = response.json()

        # Flask 서버 응답 구조: {"success": bool, "data": {...}, "error": str}
        return result

    except requests.exceptions.Timeout:
        raise Exception("Runpod 요청 시간 초과")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Runpod 요청 실패: {str(e)}")


def _poll_runpod_status(job_id: str, timeout: int = 60) -> Dict[str, Any]:
    """Runpod 작업 상태 폴링"""
    import time

    headers = {
        "Authorization": f"Bearer {RUNPOD_API_KEY}",
        "Content-Type": "application/json"
    }

    url = f"{RUNPOD_BASE_URL}/status/{job_id}"
    start_time = time.time()

    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers, timeout=10)
        result = response.json()

        status = result.get('status')
        if status == 'COMPLETED':
            return result.get('output', {})
        elif status == 'FAILED':
            raise Exception(f"Runpod 실행 실패: {result.get('error', 'Unknown error')}")

        time.sleep(1)  # 1초 대기 후 재시도

    raise Exception("Runpod 폴링 시간 초과")


def request_hint_via_runpod(
    problem_id: str,
    user_code: str,
    user,
    preset: str = '초급',
    custom_components: Optional[Dict[str, bool]] = None,
) -> tuple:
    """
    Runpod을 통해 힌트 요청

    Args:
        problem_id: 문제 ID
        user_code: 사용자 코드
        user: Django 사용자 객체
        preset: 프리셋 ('초급', '중급', '고급')
        custom_components: 사용자 정의 구성요소

    Returns:
        tuple: (success, data, error_message, status_code)
    """
    if custom_components is None:
        custom_components = {
            'libraries': True,
            'code_example': True,
            'step_by_step': True,
            'complexity_hint': True,
            'edge_cases': True,
            'improvements': True
        }

    try:
        # 1. DB에서 필요한 정보 조회
        star_count = _get_star_count(user.id, problem_id)
        previous_hints = _get_previous_hints(user.id, problem_id)
        problem_data = _get_problem_data(problem_id)

        if not problem_data.get('title'):
            return (False, None, f"문제 ID {problem_id}를 찾을 수 없습니다.", 404)

        # 1-1. 이전 힌트 기록 조회 (COH용)
        last_hint = HintRequest.objects.filter(
            user_id=user.id,
            problem_str_id=problem_id,
            is_langgraph=True
        ).order_by('-created_at').first()

        last_hint_info = {}
        if last_hint:
            last_hint_info = {
                'code_hash': last_hint.code_hash or '',
                'hint_branch': last_hint.hint_branch or '',
                'coh_depth': last_hint.coh_depth or 0
            }

        # 2. Runpod 요청 페이로드 구성
        payload = {
            "type": "hint",
            "problem_id": problem_id,
            "user_code": user_code,
            "star_count": star_count,
            "preset": preset,
            "custom_components": custom_components,
            "previous_hints": previous_hints,
            "problem_data": problem_data,
            "last_hint_info": last_hint_info
        }

        # 3. Runpod 호출
        logger.info(f"[HintProxy] Runpod 호출 시작: problem_id={problem_id}")
        result = _call_runpod(payload, timeout=90)

        if not result.get('success'):
            error_msg = result.get('error', 'Unknown error')
            logger.error(f"[HintProxy] Runpod 오류: {error_msg}")
            return (False, None, error_msg, 500)

        hint_data = result.get('data', {})

        # 4. HintRequest 저장
        try:
            hint_record = HintRequest.objects.create(
                user=user,
                problem_str_id=problem_id,  # 모델 필드명에 맞게 수정
                user_code=user_code,  # 모델 필드명에 맞게 수정
                hint_response=hint_data.get('hint', ''),  # 모델 필드명에 맞게 수정
                hint_type=hint_data.get('hint_type', ''),
                hint_level=preset,  # 모델 필드명에 맞게 수정
                is_langgraph=True,
                code_hash=hint_data.get('code_hash', ''),
                hint_branch=hint_data.get('hint_branch', ''),
                coh_depth=hint_data.get('coh_depth', 0)
            )
            logger.info(f"[HintProxy] HintRequest 저장 완료: id={hint_record.id}")
        except Exception as e:
            logger.error(f"[HintProxy] HintRequest 저장 실패: {e}")
            # 저장 실패해도 힌트는 반환

        # 5. 결과 반환
        return (True, hint_data, None, 200)

    except Exception as e:
        logger.error(f"[HintProxy] 오류: {str(e)}")
        return (False, None, str(e), 500)


def ping_runpod() -> Dict[str, Any]:
    """
    Runpod Keep-Alive 핑

    Returns:
        응답 딕셔너리
    """
    try:
        result = _call_runpod({"type": "ping"}, timeout=10)
        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def is_runpod_available() -> bool:
    """Runpod 설정이 되어있는지 확인"""
    return bool(RUNPOD_HINT_URL)


# Keep-Alive 스케줄러용 함수
def schedule_keep_alive():
    """
    Keep-Alive 스케줄 설정 (Celery Beat 또는 별도 스케줄러 사용)

    사용 예시 (Celery Beat):
    CELERY_BEAT_SCHEDULE = {
        'runpod-keep-alive': {
            'task': 'apps.coding_test.tasks.keep_runpod_warm',
            'schedule': timedelta(minutes=5),
        },
    }
    """
    pass
