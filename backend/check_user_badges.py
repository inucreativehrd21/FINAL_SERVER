"""
사용자 뱃지 확인 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.coding_test.models import Badge, UserBadge
from django.contrib.auth import get_user_model

User = get_user_model()

# 모든 사용자 확인
users = User.objects.all()
print(f'총 사용자 수: {users.count()}')

for user in users:
    user_badges = UserBadge.objects.filter(user=user).select_related('badge')
    print(f'\n사용자: {user.username}')
    print(f'  획득한 뱃지: {user_badges.count()}개')

    if user_badges.exists():
        for ub in user_badges:
            print(f'    - {ub.badge.name} ({ub.badge.badge_type})')
            print(f'      획득일: {ub.earned_at}')

# 모든 뱃지 개수 확인
all_badges = Badge.objects.all()
print(f'\n\n총 뱃지 정의: {all_badges.count()}개')
