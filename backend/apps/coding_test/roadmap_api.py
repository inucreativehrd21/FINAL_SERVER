"""
로드맵, 설문조사, 뱃지, 목표 관련 API
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from .models import (
    UserSurvey, Roadmap, Badge, UserBadge,
    Goal, UserGoal, Problem, Submission
)
from .badge_logic import check_and_award_badges
import json
import random


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_survey(request):
    """설문조사 제출 및 로드맵 생성"""
    user = request.user

    # 설문조사 데이터
    survey_data = {
        'programming_experience': request.data.get('programming_experience'),
        'learning_goals': request.data.get('learning_goals', []),
        'interested_topics': request.data.get('interested_topics', []),
        'preferred_difficulty': request.data.get('preferred_difficulty'),
        'daily_problem_goal': request.data.get('daily_problem_goal', 2)
    }

    # 이미 설문조사가 있으면 업데이트, 없으면 생성
    survey, created = UserSurvey.objects.update_or_create(
        user=user,
        defaults=survey_data
    )

    # 기존 활성화된 로드맵 비활성화
    Roadmap.objects.filter(user=user, is_active=True).update(is_active=False)

    # 로드맵 생성 (자동으로 is_active=True)
    roadmap = generate_roadmap(user, survey)

    # 기본 목표 생성 (기존 목표는 유지)
    create_default_goals(user, survey)

    message = '설문조사가 완료되었고 로드맵이 생성되었습니다.' if created else '설문조사가 업데이트되었고 로드맵이 재생성되었습니다.'

    return Response({
        'success': True,
        'message': message,
        'data': {
            'survey_id': survey.id,
            'roadmap_id': roadmap.id
        }
    })


def generate_roadmap(user, survey):
    """설문조사 기반 로드맵 생성"""
    # 선호 난이도에 따른 레벨 범위 설정
    difficulty_map = {
        'easy': (1, 5),
        'medium': (6, 10),
        'hard': (11, 15)
    }
    min_level, max_level = difficulty_map.get(survey.preferred_difficulty, (1, 5))

    # 관심 분야 태그로 문제 필터링
    interested_tags = survey.interested_topics
    problems = Problem.objects.filter(
        level__gte=min_level,
        level__lte=max_level
    ).order_by('level', 'problem_id')  # 난이도순 정렬

    # 태그가 있으면 필터링
    if interested_tags:
        problems = problems.filter(tags__overlap=interested_tags)

    # 문제 ID 리스트 (최대 50개로 증가)
    problem_ids = list(problems.values_list('problem_id', flat=True)[:50])

    # 문제가 충분하지 않으면 난이도 범위를 확장하여 추가
    if len(problem_ids) < 20:
        # 먼저 같은 태그로 난이도 범위 확장
        if interested_tags:
            extended_problems = Problem.objects.filter(
                tags__overlap=interested_tags
            ).exclude(problem_id__in=problem_ids).order_by('level', 'problem_id')[:30 - len(problem_ids)]
            problem_ids.extend(extended_problems.values_list('problem_id', flat=True))

        # 여전히 부족하면 태그 무시하고 난이도 범위 내에서 추가
        if len(problem_ids) < 20:
            additional_problems = Problem.objects.filter(
                level__gte=min_level,
                level__lte=max_level
            ).exclude(problem_id__in=problem_ids).order_by('level', 'problem_id')[:20 - len(problem_ids)]
            problem_ids.extend(additional_problems.values_list('problem_id', flat=True))

    # 로드맵 생성
    roadmap = Roadmap.objects.create(
        user=user,
        recommended_problems=problem_ids,
        current_step=0
    )

    return roadmap


def create_default_goals(user, survey):
    """기본 목표 생성"""
    # 매일 로그인 목표
    daily_login_goal = Goal.objects.get_or_create(
        goal_type='daily_login',
        defaults={
            'name': '매일 로그인하기',
            'description': '7일 연속으로 로그인하세요',
            'target_value': 7
        }
    )[0]

    UserGoal.objects.get_or_create(
        user=user,
        goal=daily_login_goal
    )

    # 매일 문제 풀기 목표
    daily_problem_goal = Goal.objects.get_or_create(
        goal_type='daily_problem',
        defaults={
            'name': '매일 문제 풀기',
            'description': f'매일 {survey.daily_problem_goal}개씩 문제를 푸세요',
            'target_value': survey.daily_problem_goal
        }
    )[0]

    UserGoal.objects.get_or_create(
        user=user,
        goal=daily_problem_goal
    )

    # 주간 문제 목표
    weekly_goal = Goal.objects.get_or_create(
        goal_type='weekly_problems',
        defaults={
            'name': '주간 10문제 해결',
            'description': '이번 주에 10개의 문제를 해결하세요',
            'target_value': 10
        }
    )[0]

    UserGoal.objects.get_or_create(
        user=user,
        goal=weekly_goal
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_roadmap(request):
    """사용자의 활성화된 로드맵 조회"""
    user = request.user

    # 활성화된 로드맵 확인
    roadmap = Roadmap.objects.filter(user=user, is_active=True).first()
    if not roadmap:
        return Response({
            'success': False,
            'message': '설문조사를 먼저 완료해주세요.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 추천 문제 정보 가져오기
    problems = Problem.objects.filter(
        problem_id__in=roadmap.recommended_problems
    ).values('problem_id', 'title', 'step_title', 'level', 'tags')

    # 순서 유지
    problem_dict = {p['problem_id']: p for p in problems}
    ordered_problems = [
        problem_dict[pid] for pid in roadmap.recommended_problems
        if pid in problem_dict
    ]

    return Response({
        'success': True,
        'data': {
            'roadmap': {
                'id': roadmap.id,
                'current_step': roadmap.current_step,
                'recommended_problems': roadmap.recommended_problems,
                'progress_percentage': roadmap.progress_percentage,
                'created_at': roadmap.created_at,
                'updated_at': roadmap.updated_at,
                'is_active': roadmap.is_active
            },
            'problems': ordered_problems
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_roadmaps(request):
    """사용자의 모든 로드맵 조회"""
    user = request.user

    roadmaps = Roadmap.objects.filter(user=user).order_by('-is_active', '-created_at')

    roadmaps_data = []
    for roadmap in roadmaps:
        # 각 로드맵의 문제 개수 및 진행률 계산
        total_problems = len(roadmap.recommended_problems)
        roadmaps_data.append({
            'id': roadmap.id,
            'current_step': roadmap.current_step,
            'total_problems': total_problems,
            'progress_percentage': roadmap.progress_percentage,
            'is_active': roadmap.is_active,
            'created_at': roadmap.created_at,
            'updated_at': roadmap.updated_at
        })

    return Response({
        'success': True,
        'data': roadmaps_data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_roadmap(request, roadmap_id):
    """로드맵 삭제"""
    user = request.user

    try:
        roadmap = Roadmap.objects.get(id=roadmap_id, user=user)
    except Roadmap.DoesNotExist:
        return Response({
            'success': False,
            'message': '로드맵을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 활성화된 로드맵을 삭제하는 경우
    was_active = roadmap.is_active
    roadmap.delete()

    # 삭제된 로드맵이 활성화 상태였다면, 가장 최근 로드맵을 활성화
    if was_active:
        latest_roadmap = Roadmap.objects.filter(user=user).order_by('-created_at').first()
        if latest_roadmap:
            latest_roadmap.is_active = True
            latest_roadmap.save()

    return Response({
        'success': True,
        'message': '로드맵이 삭제되었습니다.'
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def activate_roadmap(request, roadmap_id):
    """로드맵 활성화 (선택)"""
    user = request.user

    try:
        roadmap = Roadmap.objects.get(id=roadmap_id, user=user)
    except Roadmap.DoesNotExist:
        return Response({
            'success': False,
            'message': '로드맵을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 모든 로드맵 비활성화
    Roadmap.objects.filter(user=user).update(is_active=False)

    # 선택한 로드맵 활성화
    roadmap.is_active = True
    roadmap.save()

    return Response({
        'success': True,
        'message': '로드맵이 활성화되었습니다.',
        'data': {
            'roadmap_id': roadmap.id,
            'is_active': roadmap.is_active
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_badges(request):
    """모든 뱃지 조회"""
    badges = Badge.objects.all().values('id', 'badge_type', 'name', 'description', 'icon')

    return Response({
        'success': True,
        'data': list(badges)
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_badges(request):
    """사용자가 획득한 뱃지 조회 (진행 상황 포함)"""
    from .badge_logic import get_user_badge_progress, BADGE_CONDITIONS

    user = request.user

    # 모든 뱃지 가져오기
    all_badges = Badge.objects.all()

    # 사용자가 획득한 뱃지
    user_badges = UserBadge.objects.filter(user=user).select_related('badge')
    earned_badge_ids = {ub.badge.id: ub.earned_at for ub in user_badges}

    # 진행 상황 계산
    progress = get_user_badge_progress(user)

    badges_data = []
    for badge in all_badges:
        badge_info = {
            'badge_id': badge.id,
            'badge_type': badge.badge_type,
            'name': badge.name,
            'description': badge.description,
            'icon': badge.icon,
            'earned': badge.id in earned_badge_ids,
            'earned_at': earned_badge_ids.get(badge.id),
        }

        # 진행 상황 추가
        if badge.badge_type in progress:
            prog = progress[badge.badge_type]
            badge_info['progress'] = {
                'current': prog['current'],
                'target': prog['target'],
                'percentage': prog['percentage'],
                'condition_description': prog['condition_description'],
                'condition_type': prog['condition_type']
            }
        elif badge.badge_type in BADGE_CONDITIONS:
            # BADGE_CONDITIONS에는 있지만 progress에 없는 경우
            desc, cond_type, target = BADGE_CONDITIONS[badge.badge_type]
            badge_info['progress'] = {
                'current': 0,
                'target': target,
                'percentage': 0,
                'condition_description': desc,
                'condition_type': cond_type
            }
        else:
            # 조건 정의가 없는 뱃지
            badge_info['progress'] = {
                'current': 0,
                'target': 0,
                'percentage': 0,
                'condition_description': badge.condition_description or badge.description,
                'condition_type': badge.condition_type or 'special'
            }

        badges_data.append(badge_info)

    return Response({
        'success': True,
        'data': badges_data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_goals(request):
    """사용자 목표 진행 상황 조회"""
    user = request.user
    user_goals = UserGoal.objects.filter(user=user).select_related('goal')

    goals_data = [
        {
            'id': ug.id,
            'goal_id': ug.goal.id,
            'goal_name': ug.goal.name,
            'goal_description': ug.goal.description,
            'goal_type': ug.goal.goal_type,
            'target_value': ug.goal.target_value,
            'current_value': ug.current_value,
            'is_completed': ug.is_completed,
            'progress_percentage': ug.progress_percentage,
            'started_at': ug.started_at,
            'completed_at': ug.completed_at
        }
        for ug in user_goals
    ]

    return Response({
        'success': True,
        'data': goals_data
    })


# check_and_award_badges는 badge_logic.py에 정의되어 있음 (중복 제거)


def update_user_goals(user):
    """사용자 목표 진행 상황 업데이트"""
    today = timezone.now().date()

    # 매일 문제 풀기 목표 업데이트
    daily_problem_goals = UserGoal.objects.filter(
        user=user,
        goal__goal_type='daily_problem',
        is_completed=False
    )

    for goal in daily_problem_goals:
        # 오늘 해결한 문제 수
        today_submissions = Submission.objects.filter(
            user=user,
            result='success',
            created_at__date=today
        ).values('problem_id').distinct().count()

        goal.current_value = today_submissions
        if goal.current_value >= goal.goal.target_value:
            goal.is_completed = True
            goal.completed_at = timezone.now()
        goal.save()

    # 주간 문제 목표 업데이트
    weekly_goals = UserGoal.objects.filter(
        user=user,
        goal__goal_type='weekly_problems',
        is_completed=False
    )

    for goal in weekly_goals:
        # 이번 주 해결한 문제 수
        week_start = today - timezone.timedelta(days=today.weekday())
        weekly_count = Submission.objects.filter(
            user=user,
            result='success',
            created_at__date__gte=week_start
        ).values('problem_id').distinct().count()

        goal.current_value = weekly_count
        if goal.current_value >= goal.goal.target_value:
            goal.is_completed = True
            goal.completed_at = timezone.now()
        goal.save()
