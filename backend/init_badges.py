"""
뱃지 초기 데이터 생성 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.coding_test.models import Badge

# 뱃지 정의
BADGES = [
    # 문법 마스터 시리즈
    {'badge_type': 'korean_grammar', 'name': '유사 한국인', 'description': '문법 오류 평균 7개 이상', 'icon': '🇰🇷'},
    {'badge_type': 'syntax_typo_monster', 'name': '타이핑 괴물', 'description': '문법 오류 평균 5-6개', 'icon': '⌨️'},
    {'badge_type': 'syntax_racer', 'name': '오타 레이서', 'description': '문법 오류 평균 3-4개', 'icon': '🏎️'},
    {'badge_type': 'syntax_careful', 'name': '꼼꼼 감정사', 'description': '문법 오류 평균 1-2개', 'icon': '🔍'},
    {'badge_type': 'syntax_perfect', 'name': '문법 나치', 'description': '문법 오류 평균 0개', 'icon': '✨'},

    # 코딩 실력 시리즈
    {'badge_type': 'skill_genius', 'name': '코딩 천재', 'description': '평균 알고리즘 패턴 일치도 80% 이상', 'icon': '🧠'},
    {'badge_type': 'skill_master', 'name': '알고리즘 마스터', 'description': '평균 알고리즘 패턴 일치도 60-79%', 'icon': '👨‍💻'},
    {'badge_type': 'skill_steady', 'name': '꾸준러', 'description': '평균 알고리즘 패턴 일치도 40-59%', 'icon': '🏃'},
    {'badge_type': 'skill_newbie', 'name': '코딩 새싹', 'description': '힌트를 1번 이상 요청', 'icon': '🌱'},

    # 논리 사고 시리즈
    {'badge_type': 'logic_king', 'name': '로직 킹', 'description': '평균 엣지 케이스 처리 4점 이상', 'icon': '👑'},
    {'badge_type': 'logic_trial_error', 'name': '시행착오의 달인', 'description': '평균 엣지 케이스 처리 2.5-4점', 'icon': '🔄'},
    {'badge_type': 'logic_action_first', 'name': '일단 고', 'description': '평균 엣지 케이스 처리 2.5점 미만', 'icon': '🏃‍♂️'},

    # 특수 배지
    {'badge_type': 'no_hint_10', 'name': '독고다이', 'description': '10개 문제 힌트 없이 해결', 'icon': '🦸'},
    {'badge_type': 'perfect_coder', 'name': '퍼펙트 코더', 'description': '완벽한 코드 작성자', 'icon': '💯'},
    {'badge_type': 'unbreakable', 'name': '불굴의 의지', 'description': '한 문제에 5번 이상 힌트 요청', 'icon': '💪'},
    {'badge_type': 'hint_collector', 'name': '힌트 수집가', 'description': '총 30회 이상 힌트 요청', 'icon': '🎯'},
    {'badge_type': 'persistence_king', 'name': '끈기왕', 'description': '어려운 문제 포기하지 않기', 'icon': '🔥'},
    {'badge_type': 'all_rounder', 'name': '만능 개발자', 'description': '모든 영역에서 우수', 'icon': '🌟'},

    # 기본 배지
    {'badge_type': 'first_problem', 'name': '첫 걸음', 'description': '첫 번째 문제 해결', 'icon': '👶'},
    {'badge_type': 'problems_10', 'name': '열정가', 'description': '문제 10개 해결', 'icon': '🔟'},
    {'badge_type': 'problems_50', 'name': '도전자', 'description': '문제 50개 해결', 'icon': '🎖️'},
    {'badge_type': 'problems_100', 'name': '백문불여일견', 'description': '문제 100개 해결', 'icon': '💯'},
    {'badge_type': 'problem_streak_7', 'name': '일주일 챌린지', 'description': '7일 연속 문제 풀기', 'icon': '📅'},
    {'badge_type': 'problem_streak_30', 'name': '한 달 챌린지', 'description': '30일 연속 문제 풀기', 'icon': '📆'},
    {'badge_type': 'all_easy', 'name': '쉬운 문제 정복자', 'description': '모든 쉬운 문제 해결', 'icon': '🎓'},
    {'badge_type': 'speed_master', 'name': '스피드 마스터', 'description': '빠른 문제 해결', 'icon': '⚡'},
    {'badge_type': 'hello_world', 'name': 'Hello World!', 'description': '첫 코드 제출', 'icon': '🌍'},
    {'badge_type': 'attendance_3days', 'name': '3일 출석', 'description': '3일 연속 출석', 'icon': '📝'},

    # 유머 배지
    {'badge_type': 'night_owl', 'name': '올빼미', 'description': '자정 이후 문제 풀기', 'icon': '🦉'},
    {'badge_type': 'button_mania', 'name': '버튼광', 'description': '실행 버튼 50회 이상 클릭', 'icon': '🖱️'},
]


def init_badges():
    """모든 뱃지를 DB에 생성"""
    created_count = 0
    updated_count = 0

    for badge_data in BADGES:
        badge, created = Badge.objects.update_or_create(
            badge_type=badge_data['badge_type'],
            defaults={
                'name': badge_data['name'],
                'description': badge_data['description'],
                'icon': badge_data['icon']
            }
        )
        if created:
            created_count += 1
            print(f'[Created] {badge.name} ({badge.badge_type})')
        else:
            updated_count += 1
            print(f'[Updated] {badge.name} ({badge.badge_type})')

    print(f'\n총 {len(BADGES)}개 뱃지 처리 완료')
    print(f'생성: {created_count}개, 업데이트: {updated_count}개')


if __name__ == '__main__':
    init_badges()
