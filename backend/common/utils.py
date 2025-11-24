"""
Common utility functions.
"""
from typing import Dict, Any
from rest_framework.response import Response
from rest_framework import status


def success_response(data: Any = None, message: str = "Success", status_code: int = status.HTTP_200_OK) -> Response:
    """
    성공 응답 포맷 통일
    """
    return Response({
        'success': True,
        'message': message,
        'data': data
    }, status=status_code)


def error_response(message: str, details: Any = None, status_code: int = status.HTTP_400_BAD_REQUEST) -> Response:
    """
    에러 응답 포맷 통일
    """
    return Response({
        'success': False,
        'error': {
            'message': message,
            'details': details
        }
    }, status=status_code)


def calculate_rating_points(level: int, time_spent: int, execution_count: int) -> int:
    """
    문제 난이도와 성능에 따른 레이팅 점수 계산

    Args:
        level: 문제 난이도 (1-5)
        time_spent: 소요 시간 (초)
        execution_count: 실행 횟수

    Returns:
        계산된 레이팅 점수
    """
    # 기본 점수 (난이도별)
    base_points = {
        1: 10,
        2: 20,
        3: 30,
        4: 50,
        5: 100
    }

    points = base_points.get(level, 10)

    # 시간 보너스 (빠를수록 높은 점수)
    if time_spent < 300:  # 5분 이내
        points += 20
    elif time_spent < 600:  # 10분 이내
        points += 10
    elif time_spent < 1200:  # 20분 이내
        points += 5

    # 실행 횟수 패널티 (한 번에 성공할수록 높은 점수)
    if execution_count == 1:
        points += 30
    elif execution_count <= 3:
        points += 15
    elif execution_count <= 5:
        points += 5
    else:
        points -= (execution_count - 5) * 2  # 5회 이상부터는 감점

    return max(points, 1)  # 최소 1점


def determine_user_tendency(submissions: list) -> str:
    """
    사용자의 문제 풀이 성향 분석

    Args:
        submissions: 사용자의 제출 기록 리스트

    Returns:
        'perfectionist' (한번에 정답) 또는 'iterative' (반복 실행)
    """
    if not submissions:
        return 'unknown'

    # 평균 실행 횟수 계산
    avg_execution_count = sum(s.get('execution_count', 0) for s in submissions) / len(submissions)

    # 한 번에 정답을 맞춘 비율
    perfect_rate = sum(1 for s in submissions if s.get('execution_count', 0) == 1) / len(submissions)

    if perfect_rate > 0.5 or avg_execution_count <= 2:
        return 'perfectionist'
    else:
        return 'iterative'
