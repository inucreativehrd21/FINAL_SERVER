"""
관리자 패널 API
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from apps.coding_test.models import Problem

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_current_user(request):
    """현재 로그인한 관리자 정보 조회"""
    user = request.user
    return Response({
        'success': True,
        'data': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_users(request):
    """모든 사용자 목록 조회 (활성 사용자만)"""
    users = User.objects.filter(is_active=True).order_by('-created_at')

    users_data = [
        {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'rating': user.rating,
            'is_active': user.is_active,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'skill_score': user.skill_score,
            'skill_mode': user.skill_mode,
            'hint_level': user.hint_level,
        }
        for user in users
    ]

    return Response({
        'success': True,
        'data': users_data
    })


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_user(request, user_id):
    """사용자 정보 업데이트 (활성/비활성, 관리자 권한)"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': '사용자를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 본인 권한 변경 방지
    if 'is_staff' in request.data and user.id == request.user.id:
        return Response({
            'success': False,
            'message': '자신의 관리자 권한은 변경할 수 없습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # is_active 업데이트
    is_active = request.data.get('is_active')
    if is_active is not None:
        user.is_active = is_active

    # is_staff 업데이트 (관리자 권한)
    is_staff = request.data.get('is_staff')
    if is_staff is not None:
        user.is_staff = is_staff

    user.save()

    return Response({
        'success': True,
        'message': '사용자 정보가 업데이트되었습니다.'
    })


@api_view(['DELETE'])
@permission_classes([IsAdminUser])
def delete_user(request, user_id):
    """사용자 삭제 (소프트 삭제 - 비활성화)"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': '사용자를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 본인은 삭제할 수 없음
    if user.id == request.user.id:
        return Response({
            'success': False,
            'message': '본인은 삭제할 수 없습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 소프트 삭제 (비활성화)
    user.is_active = False
    user.save()

    return Response({
        'success': True,
        'message': '사용자가 삭제되었습니다.'
    })


@api_view(['PATCH'])
@permission_classes([IsAdminUser])
def update_user_skill(request, user_id):
    """사용자 실력 지표 업데이트"""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({
            'success': False,
            'message': '사용자를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    skill_score = request.data.get('skill_score')
    skill_mode = request.data.get('skill_mode')
    hint_level = request.data.get('hint_level')

    if skill_score is not None:
        user.skill_score = float(skill_score)

    if skill_mode is not None:
        if skill_mode not in ['auto', 'manual']:
            return Response({
                'success': False,
                'message': 'skill_mode는 auto 또는 manual이어야 합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        user.skill_mode = skill_mode

    if hint_level is not None:
        hint_level = int(hint_level)
        if hint_level not in [1, 2, 3]:
            return Response({
                'success': False,
                'message': 'hint_level은 1, 2, 3 중 하나여야 합니다.'
            }, status=status.HTTP_400_BAD_REQUEST)
        user.hint_level = hint_level

    user.save(update_fields=['skill_score', 'skill_mode', 'hint_level'])

    return Response({
        'success': True,
        'message': '사용자 실력 지표가 업데이트되었습니다.',
        'data': {
            'id': user.id,
            'username': user.username,
            'skill_score': user.skill_score,
            'skill_mode': user.skill_mode,
            'hint_level': user.hint_level,
        }
    })


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_statistics(request):
    """관리자 패널 통계 조회"""
    import json
    from pathlib import Path

    total_users = User.objects.filter(is_active=True).count()

    # problems_final_output.json 파일에서 문제 수 읽기
    problems_json_path = Path(__file__).parent.parent / 'coding_test' / 'data' / 'problems_final_output.json'
    try:
        with open(problems_json_path, 'r', encoding='utf-8-sig') as f:
            problems_data = json.load(f)
            total_problems = len(problems_data)
    except Exception as e:
        print(f"Error reading problems_final_output.json: {e}")
        total_problems = 0

    return Response({
        'success': True,
        'data': {
            'total_users': total_users,
            'total_problems': total_problems,
        }
    })
