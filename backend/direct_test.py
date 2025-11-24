"""
직접 API 뷰 테스트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.coding_test.roadmap_api import get_user_badges
from apps.coding_test.models import Badge, UserBadge
from django.contrib.auth import get_user_model

User = get_user_model()

# 모든 뱃지 확인
print("=== 데이터베이스 뱃지 확인 ===")
badges = Badge.objects.all()
print(f"총 뱃지: {badges.count()}개\n")

# 사용자별 획득 뱃지 확인
users = User.objects.all()
for user in users:
    user_badges = UserBadge.objects.filter(user=user).select_related('badge')
    print(f"\n사용자: {user.username}")
    print(f"획득 뱃지: {user_badges.count()}개")

    if user_badges.exists():
        for ub in user_badges:
            print(f"  - {ub.badge.name} ({ub.badge.badge_type})")

# API 함수 직접 호출 테스트
print("\n\n=== get_user_badges 함수 직접 테스트 ===")
from apps.coding_test.badge_logic import get_user_badge_progress, BADGE_CONDITIONS

admin_user = User.objects.filter(username='admin').first()
if admin_user:
    print(f"\n테스트 대상: {admin_user.username}")

    # 모든 뱃지 가져오기
    all_badges = Badge.objects.all()
    print(f"전체 뱃지: {all_badges.count()}개")

    # 사용자가 획득한 뱃지
    user_badges = UserBadge.objects.filter(user=admin_user).select_related('badge')
    earned_badge_ids = {ub.badge.id: ub.earned_at for ub in user_badges}
    print(f"획득 뱃지 ID: {list(earned_badge_ids.keys())}")

    # 진행 상황 계산
    try:
        progress = get_user_badge_progress(admin_user)
        print(f"진행 상황 계산 완료: {len(progress)}개 뱃지")
    except Exception as e:
        print(f"진행 상황 계산 오류: {e}")
        import traceback
        traceback.print_exc()
        progress = {}

    # 뱃지 데이터 구성
    badges_data = []
    for badge in all_badges:
        badge_info = {
            'badge_id': badge.id,
            'badge_type': badge.badge_type,
            'name': badge.name,
            'description': badge.description,
            'icon': badge.icon,
            'earned': badge.id in earned_badge_ids,
            'earned_at': str(earned_badge_ids.get(badge.id)) if badge.id in earned_badge_ids else None,
        }

        # 진행 상황 추가
        if badge.badge_type in progress:
            prog = progress[badge.badge_type]
            badge_info['progress'] = prog
        elif badge.badge_type in BADGE_CONDITIONS:
            desc, cond_type, target = BADGE_CONDITIONS[badge.badge_type]
            badge_info['progress'] = {
                'current': 0,
                'target': target,
                'percentage': 0,
                'condition_description': desc,
                'condition_type': cond_type
            }

        badges_data.append(badge_info)

    print(f"\n생성된 뱃지 데이터: {len(badges_data)}개")
    print(f"획득한 뱃지: {sum(1 for b in badges_data if b['earned'])}개")

    # 첫 5개 뱃지 샘플 출력
    print("\n첫 5개 뱃지 샘플:")
    for badge in badges_data[:5]:
        print(f"  - {badge['name']} (earned: {badge['earned']})")
