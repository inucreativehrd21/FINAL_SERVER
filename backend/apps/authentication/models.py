"""
사용자 인증 모델
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
import random
import string


class User(AbstractUser):
    """
    커스텀 사용자 모델
    """
    ROLE_CHOICES = (
        ('user', '일반 사용자'),
        ('admin', '관리자'),
    )

    SKILL_MODE_CHOICES = (
        ('auto', '자동'),
        ('manual', '수동'),
    )

    HINT_LEVEL_CHOICES = (
        (3, '레벨 3 (실력자 - 소크라테스식)'),
        (2, '레벨 2 (보통 - 개념 힌트)'),
        (1, '레벨 1 (기초 - 구체적 힌트)'),
    )

    email = models.EmailField('이메일', unique=True)
    role = models.CharField('역할', max_length=10, choices=ROLE_CHOICES, default='user')
    rating = models.IntegerField('레이팅 점수', default=0)
    tendency = models.CharField(
        '문제 풀이 성향',
        max_length=20,
        choices=(
            ('perfectionist', '완벽주의형'),
            ('iterative', '반복형'),
            ('unknown', '미분류'),
        ),
        default='unknown'
    )

    # 추가 사용자 정보
    name = models.CharField('이름', max_length=50, blank=True)
    nickname = models.CharField('닉네임', max_length=50, blank=True)
    phone_number = models.CharField('전화번호', max_length=20, blank=True)
    birth_date = models.DateField('생년월일', null=True, blank=True)
    gender = models.CharField(
        '성별',
        max_length=10,
        choices=(
            ('male', '남'),
            ('female', '여'),
        ),
        blank=True
    )

    # 실력 지표 관련 필드
    skill_score = models.FloatField(
        '실력 점수',
        default=50.0,
        help_text='0~100 사이의 점수. 높을수록 초보, 낮을수록 실력자'
    )
    skill_mode = models.CharField(
        '실력 지표 모드',
        max_length=10,
        choices=SKILL_MODE_CHOICES,
        default='auto',
        help_text='auto: 문제 풀이 기록으로 자동 갱신, manual: 관리자가 수동 설정'
    )
    hint_level = models.IntegerField(
        '힌트 레벨',
        choices=HINT_LEVEL_CHOICES,
        default=2,
        help_text='1: 구체적 힌트, 2: 개념 힌트, 3: 소크라테스식'
    )

    created_at = models.DateTimeField('가입일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    def is_admin(self):
        """관리자 여부"""
        return self.role == 'admin'

    def update_skill_score(self):
        """문제 풀이 기록을 기반으로 실력 점수 자동 갱신 (auto 모드일 때만)"""
        if self.skill_mode != 'auto':
            return

        # ProblemSession 모델 import (순환 참조 방지)
        from apps.coding_test.models import ProblemSession

        # 최근 10개 세션 가져오기
        recent_sessions = ProblemSession.objects.filter(user=self).order_by('-started_at')[:10]

        if not recent_sessions.exists():
            return

        # 각 세션의 난이도 점수 평균 계산
        total_score = sum(session.calculate_difficulty_score() for session in recent_sessions)
        avg_score = total_score / len(recent_sessions)

        # 실력 점수 업데이트 (0~100, 높을수록 초보)
        self.skill_score = avg_score

        # 힌트 레벨 자동 조정
        if avg_score >= 70:  # 70점 이상: 많이 어려워함 -> 기초
            self.hint_level = 1
        elif avg_score >= 40:  # 40~70점: 보통 -> 보통
            self.hint_level = 2
        else:  # 40점 미만: 잘 풀음 -> 실력자
            self.hint_level = 3

        self.save(update_fields=['skill_score', 'hint_level'])

    def get_hint_level_display_text(self):
        """힌트 레벨 텍스트 반환"""
        level_map = {
            1: '레벨 1 (기초 - 구체적 힌트)',
            2: '레벨 2 (보통 - 개념 힌트)',
            3: '레벨 3 (실력자 - 소크라테스식)'
        }
        return level_map.get(self.hint_level, '레벨 2')


class EmailVerificationCode(models.Model):
    """이메일 인증 코드"""
    email = models.EmailField('이메일')
    code = models.CharField('인증 코드', max_length=6)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    expires_at = models.DateTimeField('만료일')
    is_verified = models.BooleanField('인증 완료 여부', default=False)

    class Meta:
        db_table = 'email_verification_codes'
        verbose_name = '이메일 인증 코드'
        verbose_name_plural = '이메일 인증 코드 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} - {self.code}"

    @staticmethod
    def generate_code():
        """6자리 랜덤 인증 코드 생성"""
        return ''.join(random.choices(string.digits, k=6))

    def is_expired(self):
        """만료 여부 확인"""
        return timezone.now() > self.expires_at

    @classmethod
    def create_verification_code(cls, email):
        """새 인증 코드 생성"""
        code = cls.generate_code()
        expires_at = timezone.now() + timedelta(minutes=10)
        return cls.objects.create(
            email=email,
            code=code,
            expires_at=expires_at
        )
