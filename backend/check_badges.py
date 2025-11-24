"""
뱃지 확인 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.coding_test.models import Badge

badges = Badge.objects.all()
print(f'Total badges in DB: {badges.count()}')
print('\nAll badges:')
for b in badges:
    print(f'  {b.badge_type}: {b.name} - {b.description}')
