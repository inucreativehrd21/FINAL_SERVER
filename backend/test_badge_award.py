"""
뱃지 수여 테스트 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.coding_test.badge_logic import check_and_award_badges
from django.contrib.auth import get_user_model

User = get_user_model()

# 첫 번째 사용자로 테스트
user = User.objects.first()
if user:
    print(f'Testing badge award for user: {user.username}')
    newly_awarded = check_and_award_badges(user)

    if newly_awarded:
        print(f'\n{len(newly_awarded)}개의 새 뱃지 획득:')
        for badge in newly_awarded:
            print(f'  - {badge.name} ({badge.badge_type}): {badge.description}')
    else:
        print('\n새로 획득한 뱃지가 없습니다.')

    # 현재 보유 뱃지 확인
    from apps.coding_test.models import UserBadge
    user_badges = UserBadge.objects.filter(user=user).select_related('badge')
    print(f'\n총 보유 뱃지: {user_badges.count()}개')
    for ub in user_badges:
        print(f'  - {ub.badge.name} ({ub.badge.badge_type})')
else:
    print('No users found in database')
