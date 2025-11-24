"""
배지 획득 로직
사용자의 HintMetrics 데이터를 기반으로 배지 획득 조건 체크
"""
from django.db.models import Avg, Count
from .models import HintMetrics, Badge, UserBadge, Submission


# 뱃지별 조건 정의 (12개 지표 기반으로 업데이트)
# 기존 32개 배지와 매핑
BADGE_CONDITIONS = {
    # 기본 배지 (문제 개수 기준)
    'hello_world': ('첫 코드 제출', 'count', 1),
    'first_problem': ('첫 번째 문제 해결', 'count', 1),
    'problems_10': ('문제 10개 해결', 'count', 10),
    'problems_50': ('문제 50개 해결', 'count', 50),
    'problems_100': ('문제 100개 해결', 'count', 100),

    # 연속 출석/문제 풀기
    'attendance_3days': ('3일 연속 출석', 'streak', 3),
    'problem_streak_7': ('7일 연속 문제 풀기', 'streak', 7),
    'problem_streak_30': ('30일 연속 문제 풀기', 'streak', 30),

    # 문법 오류 기반 (syntax_errors)
    'syntax_perfect': ('문법 오류 평균 0개', 'metric', 'syntax_errors'),
    'syntax_careful': ('문법 오류 평균 1-2개', 'metric', 'syntax_errors'),
    'syntax_racer': ('문법 오류 평균 3-4개', 'metric', 'syntax_errors'),
    'syntax_typo_monster': ('문법 오류 평균 5-6개', 'metric', 'syntax_errors'),
    'korean_grammar': ('문법 오류 평균 7개 이상', 'metric', 'syntax_errors'),

    # 알고리즘 패턴 일치도 기반 (algorithm_pattern_match)
    'skill_genius': ('평균 알고리즘 패턴 일치도 80% 이상', 'metric', 'algorithm_pattern_match'),
    'skill_master': ('평균 알고리즘 패턴 일치도 60-79%', 'metric', 'algorithm_pattern_match'),
    'skill_steady': ('평균 알고리즘 패턴 일치도 40-59%', 'metric', 'algorithm_pattern_match'),
    'skill_newbie': ('힌트를 1번 이상 요청', 'special', 1),

    # 엣지 케이스 처리 기반 (edge_case_handling - LLM)
    'logic_king': ('평균 엣지 케이스 처리 4점 이상', 'metric', 'edge_case_handling'),
    'logic_trial_error': ('평균 엣지 케이스 처리 2.5-4점', 'metric', 'edge_case_handling'),
    'logic_action_first': ('평균 엣지 케이스 처리 2.5점 미만', 'metric', 'edge_case_handling'),

    # 특수 배지
    'no_hint_10': ('10개 문제 힌트 없이 해결', 'special', 10),
    'perfect_coder': ('완벽한 코드 작성자', 'metric', 'combined'),
    'unbreakable': ('한 문제에 5번 이상 힌트 요청', 'special', 5),
    'hint_collector': ('총 30회 이상 힌트 요청', 'special', 30),
    'persistence_king': ('어려운 문제 포기하지 않기', 'special', 1),
    'all_rounder': ('모든 지표 평균 이상', 'metric', 'combined'),

    # 기타 배지
    'streak_7': ('7일 연속 로그인', 'streak', 7),
    'perfect_score': ('모든 테스트 케이스 통과', 'special', 1),
    'all_easy': ('모든 쉬운 문제 해결', 'special', 1),
    'speed_master': ('빠른 문제 해결', 'special', 1),
    'night_owl': ('자정 이후 문제 풀기', 'special', 1),
    'button_mania': ('실행 버튼 50회 이상', 'special', 50),
}


def check_and_award_badges(user):
    """
    사용자의 12개 지표를 분석하여 배지 획득 조건 체크 및 수여

    Args:
        user: Django User 인스턴스

    Returns:
        list: 새로 획득한 배지 목록
    """
    # 평균 지표 계산 (문제별 마지막 지표만 사용)
    metrics_summary = get_user_metrics_summary(user)
    newly_awarded_badges = []

    # 문제 풀이 개수
    solved_count = Submission.objects.filter(user=user, result='success').values('problem').distinct().count()

    # 0. 첫 코드 제출 (hello_world)
    total_submissions = Submission.objects.filter(user=user).count()
    if total_submissions >= 1:
        badge = award_badge_if_not_exists(user, 'hello_world', 'Hello World!', '첫 코드 제출')
        if badge: newly_awarded_badges.append(badge)

    # 1. 기본 배지 (문제 개수)
    if solved_count >= 1:
        badge = award_badge_if_not_exists(user, 'first_problem', '첫 걸음', '첫 번째 문제 해결')
        if badge: newly_awarded_badges.append(badge)

    if solved_count >= 10:
        badge = award_badge_if_not_exists(user, 'problems_10', '열정가', '문제 10개 해결')
        if badge: newly_awarded_badges.append(badge)

    if solved_count >= 50:
        badge = award_badge_if_not_exists(user, 'problems_50', '도전자', '문제 50개 해결')
        if badge: newly_awarded_badges.append(badge)

    if solved_count >= 100:
        badge = award_badge_if_not_exists(user, 'problems_100', '백문불여일견', '문제 100개 해결')
        if badge: newly_awarded_badges.append(badge)

    # 2. 연속 출석/문제 풀기 (간단 구현)
    recent_submissions = Submission.objects.filter(user=user).order_by('-created_at')
    if recent_submissions.exists():
        dates = sorted(set(sub.created_at.date() for sub in recent_submissions), reverse=True)
        max_consecutive = 1
        consecutive_days = 1
        for i in range(1, len(dates)):
            if (dates[i-1] - dates[i]).days == 1:
                consecutive_days += 1
            else:
                max_consecutive = max(max_consecutive, consecutive_days)
                consecutive_days = 1
        max_consecutive = max(max_consecutive, consecutive_days)

        if max_consecutive >= 3:
            badge = award_badge_if_not_exists(user, 'attendance_3days', '3일 출석', '3일 연속 출석')
            if badge: newly_awarded_badges.append(badge)

        if max_consecutive >= 7:
            badge = award_badge_if_not_exists(user, 'problem_streak_7', '일주일 챌린지', '7일 연속 문제 풀기')
            if badge: newly_awarded_badges.append(badge)

        if max_consecutive >= 30:
            badge = award_badge_if_not_exists(user, 'problem_streak_30', '한 달 챌린지', '30일 연속 문제 풀기')
            if badge: newly_awarded_badges.append(badge)

    # 3. 문법 오류 기반 뱃지 (syntax_errors)
    if metrics_summary['avg_syntax_errors'] == 0:
        badge = award_badge_if_not_exists(user, 'syntax_perfect', '문법 나치', '문법 오류 평균 0개')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_syntax_errors'] < 2:
        badge = award_badge_if_not_exists(user, 'syntax_careful', '꼼꼼 감정사', '문법 오류 평균 1-2개')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_syntax_errors'] < 4:
        badge = award_badge_if_not_exists(user, 'syntax_racer', '오타 레이서', '문법 오류 평균 3-4개')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_syntax_errors'] < 6:
        badge = award_badge_if_not_exists(user, 'syntax_typo_monster', '타이핑 괴물', '문법 오류 평균 5-6개')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_syntax_errors'] >= 7:
        badge = award_badge_if_not_exists(user, 'korean_grammar', '유사 한국인', '문법 오류 평균 7개 이상')
        if badge: newly_awarded_badges.append(badge)

    # 4. 알고리즘 패턴 일치도 기반 뱃지 (algorithm_pattern_match)
    if metrics_summary['avg_algorithm_pattern_match'] >= 80:
        badge = award_badge_if_not_exists(user, 'skill_genius', '코딩 천재', '평균 알고리즘 패턴 일치도 80% 이상')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_algorithm_pattern_match'] >= 60:
        badge = award_badge_if_not_exists(user, 'skill_master', '알고리즘 마스터', '평균 알고리즘 패턴 일치도 60-79%')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_algorithm_pattern_match'] >= 40:
        badge = award_badge_if_not_exists(user, 'skill_steady', '꾸준러', '평균 알고리즘 패턴 일치도 40-59%')
        if badge: newly_awarded_badges.append(badge)

    # 5. 엣지 케이스 처리 기반 뱃지 (edge_case_handling - LLM 지표)
    if metrics_summary['avg_edge_case_handling'] >= 4:
        badge = award_badge_if_not_exists(user, 'logic_king', '로직 킹', '평균 엣지 케이스 처리 4점 이상')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_edge_case_handling'] >= 2.5:
        badge = award_badge_if_not_exists(user, 'logic_trial_error', '시행착오의 달인', '평균 엣지 케이스 처리 2.5-4점')
        if badge: newly_awarded_badges.append(badge)
    elif metrics_summary['avg_edge_case_handling'] < 2.5:
        badge = award_badge_if_not_exists(user, 'logic_action_first', '일단 고', '평균 엣지 케이스 처리 2.5점 미만')
        if badge: newly_awarded_badges.append(badge)

    # 6. 완벽한 코더 (test_pass_rate + code_quality_score + algorithm_efficiency)
    if (metrics_summary['avg_test_pass_rate'] == 100 and
        metrics_summary['avg_code_quality_score'] >= 90 and
        metrics_summary['avg_algorithm_efficiency'] >= 4):
        badge = award_badge_if_not_exists(user, 'perfect_coder', '퍼펙트 코더', '완벽한 코드 작성자')
        if badge: newly_awarded_badges.append(badge)

    # 5. 특수 뱃지 (모든 지표 우수)
    all_above_avg = (
        metrics_summary['avg_test_pass_rate'] >= 80 and
        metrics_summary['avg_code_quality_score'] >= 70 and
        metrics_summary['avg_algorithm_efficiency'] >= 3 and
        metrics_summary['avg_code_readability'] >= 3 and
        metrics_summary['avg_edge_case_handling'] >= 3
    )
    if all_above_avg and solved_count >= 10:
        badge = award_badge_if_not_exists(user, 'all_rounder', '만능 개발자', '모든 지표 평균 이상')
        if badge: newly_awarded_badges.append(badge)

    return newly_awarded_badges


def award_badge_if_not_exists(user, badge_type, name, description):
    """
    배지가 없으면 생성하고 사용자에게 수여

    Args:
        user: Django User
        badge_type: Badge.BADGE_TYPES의 키
        name: 배지 이름
        description: 배지 설명

    Returns:
        Badge 인스턴스 또는 None (이미 획득한 경우)
    """
    # 배지가 DB에 없으면 생성
    badge, created = Badge.objects.get_or_create(
        badge_type=badge_type,
        defaults={
            'name': name,
            'description': description,
            'icon': '🏆'  # 기본 아이콘
        }
    )

    # 사용자가 이미 획득했는지 확인
    user_badge, created = UserBadge.objects.get_or_create(
        user=user,
        badge=badge
    )

    if created:
        print(f'[Badge Awarded] User: {user.username}, Badge: {name}')
        return badge

    return None


def get_user_metrics_summary(user):
    """
    사용자의 평균 지표 요약

    각 문제별로 마지막 힌트 요청 시점의 지표만 사용

    Args:
        user: Django User

    Returns:
        dict: 평균 지표 딕셔너리
    """
    # 각 문제별 마지막 지표만 가져오기
    from django.db.models import Max, Q

    # 문제별 최신 created_at 찾기
    latest_metrics_ids = []
    problems = HintMetrics.objects.filter(user=user).values('problem').distinct()

    for problem_data in problems:
        problem_id = problem_data['problem']
        latest = HintMetrics.objects.filter(
            user=user,
            problem_id=problem_id
        ).order_by('-created_at').first()

        if latest:
            latest_metrics_ids.append(latest.id)

    # 최신 지표들만 필터링
    latest_metrics = HintMetrics.objects.filter(id__in=latest_metrics_ids)

    # 평균 계산 (정적 지표 6개 + LLM 지표 6개)
    aggregates = latest_metrics.aggregate(
        avg_syntax_errors=Avg('syntax_errors'),
        avg_test_pass_rate=Avg('test_pass_rate'),
        avg_code_complexity=Avg('code_complexity'),
        avg_code_quality_score=Avg('code_quality_score'),
        avg_algorithm_pattern_match=Avg('algorithm_pattern_match'),
        avg_pep8_violations=Avg('pep8_violations'),
        # LLM 지표
        avg_algorithm_efficiency=Avg('algorithm_efficiency'),
        avg_code_readability=Avg('code_readability'),
        avg_design_pattern_fit=Avg('design_pattern_fit'),
        avg_edge_case_handling=Avg('edge_case_handling'),
        avg_code_conciseness=Avg('code_conciseness'),
        avg_function_separation=Avg('function_separation')
    )

    return {
        'avg_syntax_errors': aggregates['avg_syntax_errors'] or 0,
        'avg_test_pass_rate': aggregates['avg_test_pass_rate'] or 0,
        'avg_code_complexity': aggregates['avg_code_complexity'] or 0,
        'avg_code_quality_score': aggregates['avg_code_quality_score'] or 0,
        'avg_algorithm_pattern_match': aggregates['avg_algorithm_pattern_match'] or 0,
        'avg_pep8_violations': aggregates['avg_pep8_violations'] or 0,
        'avg_algorithm_efficiency': aggregates['avg_algorithm_efficiency'] or 0,
        'avg_code_readability': aggregates['avg_code_readability'] or 0,
        'avg_design_pattern_fit': aggregates['avg_design_pattern_fit'] or 0,
        'avg_edge_case_handling': aggregates['avg_edge_case_handling'] or 0,
        'avg_code_conciseness': aggregates['avg_code_conciseness'] or 0,
        'avg_function_separation': aggregates['avg_function_separation'] or 0,
        'total_problems': len(latest_metrics_ids)
    }


def get_user_badge_progress(user):
    """
    사용자의 각 뱃지별 진행 상황 계산

    Args:
        user: Django User 인스턴스

    Returns:
        dict: 뱃지별 진행 상황 {badge_type: {current, target, percentage}}
    """
    progress = {}

    # 기본 지표 가져오기
    metrics_summary = get_user_metrics_summary(user)
    total_hints = HintMetrics.objects.filter(user=user).count()
    total_problems_with_hints = metrics_summary['total_problems']

    # 성공한 제출 수
    solved_count = Submission.objects.filter(
        user=user,
        result='success'
    ).values('problem').distinct().count()

    # 한 문제에 대한 최대 힌트 요청 수
    max_hints_per_problem = HintMetrics.objects.filter(user=user).values('problem').annotate(
        hint_count=Count('id')
    ).order_by('-hint_count').first()
    max_hints_single = max_hints_per_problem['hint_count'] if max_hints_per_problem else 0

    # 힌트 없이 해결한 문제 수 (submission은 있지만 hint_metrics가 없는 문제)
    # 실제로는 hint_count=0인 문제를 찾아야 함
    problems_without_hints = 0  # TODO: 실제 로직 구현 필요

    # 각 뱃지별 진행 상황 계산
    for badge_type, (desc, cond_type, target_value) in BADGE_CONDITIONS.items():
        current = 0
        target = 1  # 기본값

        # target이 문자열(메트릭 이름)인 경우와 숫자인 경우 구분
        if isinstance(target_value, str):
            # 'metric' 타입의 경우 target은 메트릭 이름
            target = 1
        else:
            # 'count', 'streak', 'special' 타입의 경우 target은 숫자
            target = target_value

        if badge_type in ['problems_10', 'problems_50', 'problems_100', 'first_problem']:
            current = solved_count
        elif badge_type == 'hello_world':
            current = 1 if solved_count > 0 else 0
        elif badge_type == 'hint_collector':
            current = total_hints
            target = target_value
        elif badge_type == 'unbreakable':
            current = max_hints_single
            target = target_value
        elif badge_type == 'no_hint_10':
            current = problems_without_hints
            target = target_value
        elif badge_type == 'perfect_coder':
            # 완벽하게 해결한 문제 수 (12개 지표 기준)
            current = 1 if (
                metrics_summary['avg_test_pass_rate'] == 100 and
                metrics_summary['avg_code_quality_score'] >= 90 and
                metrics_summary['avg_algorithm_efficiency'] >= 4
            ) else 0
            target = 1
        elif badge_type in ['skill_genius', 'skill_master', 'skill_steady']:
            current = int(metrics_summary['avg_algorithm_pattern_match'])
            target = 100
        elif badge_type == 'skill_newbie':
            current = 1 if total_problems_with_hints > 0 else 0
            target = 1
        elif badge_type in ['syntax_perfect', 'syntax_careful', 'syntax_racer', 'syntax_typo_monster', 'korean_grammar']:
            # 문법 오류 기반 - 조건 충족 여부만 표시
            current = 1 if total_problems_with_hints > 0 else 0
            target = 1
        elif badge_type in ['logic_king', 'logic_trial_error', 'logic_action_first']:
            current = 1 if total_problems_with_hints > 0 else 0
            target = 1
        elif badge_type in ['problem_streak_7', 'problem_streak_30', 'attendance_3days']:
            # 연속 일수 계산
            current = 0
            target = target_value
        elif badge_type == 'all_rounder':
            current = 1 if (
                metrics_summary['avg_test_pass_rate'] >= 80 and
                metrics_summary['avg_code_quality_score'] >= 70 and
                metrics_summary['avg_algorithm_efficiency'] >= 3
            ) else 0
            target = 1
        else:
            # 기타 special 타입
            current = 0
            target = target_value if isinstance(target_value, int) else 1

        # 퍼센트 계산 (target이 0이면 100%)
        if target == 0 or target == 1:
            percentage = 100 if current >= target else 0
        else:
            percentage = min(100, int((current / target) * 100))

        progress[badge_type] = {
            'current': current,
            'target': target,
            'percentage': percentage,
            'condition_description': desc,
            'condition_type': cond_type
        }

    return progress
