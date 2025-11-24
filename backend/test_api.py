"""
뱃지 API 테스트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.coding_test.roadmap_api import get_user_badges
from django.contrib.auth import get_user_model
from django.test import RequestFactory

User = get_user_model()
user = User.objects.first()

if user:
    # Mock request 객체 생성
    factory = RequestFactory()
    request = factory.get('/coding-test/user-badges/')
    request.user = user

    # API 호출
    response = get_user_badges(request)

    print(f'Response status: {response.status_code}')
    print(f'Response data keys: {response.data.keys()}')
    print(f'Success: {response.data.get("success")}')

    badges = response.data.get('data', [])
    print(f'\n총 뱃지 수: {len(badges)}개')

    # 획득한 뱃지만 출력
    earned_badges = [b for b in badges if b.get('earned')]
    print(f'획득한 뱃지: {len(earned_badges)}개')
    for badge in earned_badges:
        print(f'  - {badge["name"]} ({badge["badge_type"]})')
        if 'earned_at' in badge and badge['earned_at']:
            print(f'    획득일: {badge["earned_at"]}')

    # 진행중인 뱃지 몇 개 출력
    print(f'\n진행중인 뱃지 (샘플 5개):')
    not_earned = [b for b in badges if not b.get('earned')]
    for badge in not_earned[:5]:
        progress = badge.get('progress', {})
        print(f'  - {badge["name"]}: {progress.get("current", 0)}/{progress.get("target", 0)} ({progress.get("percentage", 0)}%)')
else:
    print('No users found')
