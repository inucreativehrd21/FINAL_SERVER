"""
코딩 테스트 모델
"""
from django.db import models
from django.conf import settings


class Problem(models.Model):
    """문제 모델"""
    problem_id = models.CharField('문제 ID', max_length=20, unique=True, db_index=True)
    step_title = models.CharField('단계 제목', max_length=200, blank=True)
    title = models.CharField('제목', max_length=200)
    level = models.IntegerField('난이도', choices=[(i, f'레벨 {i}') for i in range(1, 27)])
    tags = models.JSONField('태그', default=list)
    description = models.TextField('문제 설명')
    input_description = models.TextField('입력 설명')
    output_description = models.TextField('출력 설명')
    examples = models.JSONField('예시', default=list)
    url = models.URLField('문제 URL', blank=True)
    solutions = models.JSONField('정답 코드', default=list)
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        db_table = 'problems'
        verbose_name = '문제'
        verbose_name_plural = '문제 목록'
        ordering = ['problem_id']

    def __str__(self):
        return f"[{self.problem_id}] {self.title}"


class Submission(models.Model):
    """제출 기록 모델 (확장: 12개 지표 포함)"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='submissions')
    code = models.TextField('제출 코드')
    result = models.CharField(
        '결과',
        max_length=20,
        choices=[
            ('pending', '대기 중'),
            ('success', '성공'),
            ('fail', '실패'),
            ('error', '에러'),
        ],
        default='pending'
    )
    output = models.TextField('출력', blank=True)
    error_message = models.TextField('에러 메시지', blank=True)
    execution_count = models.IntegerField('실행 횟수', default=1)
    time_spent = models.IntegerField('소요 시간(초)', default=0)
    rating_earned = models.IntegerField('획득 점수', default=0)

    # 테스트 결과
    is_correct = models.BooleanField('정답 여부', default=False)
    passed_tests = models.IntegerField('통과한 테스트 수', default=0)
    total_tests = models.IntegerField('전체 테스트 수', default=0)

    # 정적 지표 (6개)
    syntax_errors = models.IntegerField('문법 오류 개수', default=0)
    test_pass_rate = models.FloatField('테스트 통과율', default=0.0)
    execution_time = models.FloatField('실행 시간(ms)', default=0.0)
    memory_usage = models.FloatField('메모리 사용량(KB)', default=0.0)
    code_quality_score = models.FloatField('코드 품질 점수', default=0.0)
    pep8_violations = models.IntegerField('PEP8 위반 개수', default=0)

    # LLM 지표 (6개, 각 1-5점)
    algorithm_efficiency = models.IntegerField('알고리즘 효율성', default=3)
    code_readability = models.IntegerField('코드 가독성', default=3)
    edge_case_handling = models.IntegerField('엣지 케이스 처리', default=3)
    code_conciseness = models.IntegerField('코드 간결성', default=3)
    test_coverage_estimate = models.IntegerField('테스트 커버리지 추정', default=3)
    security_awareness = models.IntegerField('보안 인식', default=3)

    created_at = models.DateTimeField('제출일', auto_now_add=True)

    class Meta:
        db_table = 'submissions'
        verbose_name = '제출 기록'
        verbose_name_plural = '제출 기록 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({self.result})"


class Bookmark(models.Model):
    """북마크 모델"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='problem_bookmarks')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField('북마크일', auto_now_add=True)

    class Meta:
        db_table = 'problem_bookmarks'
        verbose_name = '문제 북마크'
        verbose_name_plural = '문제 북마크 목록'
        unique_together = ['user', 'problem']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.problem.title}"


class HintRequest(models.Model):
    """힌트 요청 기록 모델"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='hint_requests')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='hint_requests', null=True, blank=True)
    problem_str_id = models.CharField('문제 ID (문자열)', max_length=50, blank=True)  # LangGraph용
    hint_level = models.CharField(
        '힌트 레벨',
        max_length=20,
        choices=[
            ('small', '소 힌트'),
            ('medium', '중 힌트'),
            ('large', '대 힌트'),
        ],
        blank=True
    )
    hint_type = models.CharField('힌트 타입', max_length=50, blank=True)  # LangGraph 분기 타입
    hint_branch = models.CharField('힌트 분기', max_length=10, blank=True)  # A, B, C, D, E1, E2, F
    user_code = models.TextField('사용자 코드')
    code_hash = models.CharField('코드 해시', max_length=32, blank=True, db_index=True)  # COH 체크용
    hint_response = models.TextField('힌트 응답')
    model_used = models.CharField('사용 모델', max_length=100, blank=True)
    is_langgraph = models.BooleanField('LangGraph 사용 여부', default=False)  # LangGraph vs 기존 API
    coh_depth = models.IntegerField('COH 깊이', default=0)  # COH 상태 저장
    created_at = models.DateTimeField('요청일', auto_now_add=True)

    class Meta:
        db_table = 'hint_requests'
        verbose_name = '힌트 요청'
        verbose_name_plural = '힌트 요청 목록'
        ordering = ['-created_at']

    def __str__(self):
        method = 'LangGraph' if self.is_langgraph else 'API'
        problem_info = self.problem.title if self.problem else self.problem_str_id
        return f"{self.user.username} - {problem_info} ({method})"


class TestCaseProposal(models.Model):
    """테스트 케이스 제안 모델"""
    STATUS_CHOICES = [
        ('pending', '승인 대기'),
        ('approved', '승인됨'),
        ('rejected', '거부됨'),
    ]

    problem_id = models.CharField('문제 ID', max_length=20, db_index=True)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='test_case_proposals',
        verbose_name='제안자'
    )
    input_data = models.TextField('입력 데이터')
    expected_output = models.TextField('예상 출력')
    description = models.TextField('설명', blank=True, help_text='이 테스트 케이스가 필요한 이유')
    status = models.CharField(
        '상태',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_test_cases',
        verbose_name='검토자'
    )
    review_comment = models.TextField('검토 의견', blank=True)
    created_at = models.DateTimeField('제안일', auto_now_add=True)
    reviewed_at = models.DateTimeField('검토일', null=True, blank=True)

    class Meta:
        db_table = 'test_case_proposals'
        verbose_name = '테스트 케이스 제안'
        verbose_name_plural = '테스트 케이스 제안 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.problem_id}] {self.proposed_by.username} - {self.get_status_display()}"


class SolutionProposal(models.Model):
    """솔루션 제안 모델"""
    STATUS_CHOICES = [
        ('pending', '승인 대기'),
        ('approved', '승인됨'),
        ('rejected', '거부됨'),
    ]

    problem_id = models.CharField('문제 ID', max_length=20, db_index=True)
    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='solution_proposals',
        verbose_name='제안자'
    )
    solution_code = models.TextField('솔루션 코드')
    language = models.CharField('프로그래밍 언어', max_length=50, default='python')
    description = models.TextField('설명', blank=True, help_text='이 솔루션에 대한 설명')
    is_reference = models.BooleanField('참조 솔루션 여부', default=True, help_text='JSON에 추가할지 여부')
    status = models.CharField(
        '상태',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_solutions',
        verbose_name='검토자'
    )
    review_comment = models.TextField('검토 의견', blank=True)
    created_at = models.DateTimeField('제안일', auto_now_add=True)
    reviewed_at = models.DateTimeField('검토일', null=True, blank=True)

    class Meta:
        db_table = 'solution_proposals'
        verbose_name = '솔루션 제안'
        verbose_name_plural = '솔루션 제안 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.problem_id}] {self.proposed_by.username} - {self.get_status_display()}"


class ProblemProposal(models.Model):
    """문제 제안 모델"""
    STATUS_CHOICES = [
        ('pending', '승인 대기'),
        ('approved', '승인됨'),
        ('rejected', '거부됨'),
    ]

    problem_id = models.CharField('문제 ID', max_length=20, db_index=True)
    title = models.CharField('문제 제목', max_length=200)
    step_title = models.CharField('단계 제목', max_length=200, blank=True)
    description = models.TextField('문제 설명')
    input_description = models.TextField('입력 설명')
    output_description = models.TextField('출력 설명')
    level = models.IntegerField('난이도', choices=[(i, f'레벨 {i}') for i in range(1, 16)])
    tags = models.JSONField('태그', default=list)
    solution_code = models.TextField('참조 솔루션 코드')
    language = models.CharField('프로그래밍 언어', max_length=50, default='python')
    test_cases = models.JSONField('테스트 케이스', default=list, help_text='입력/출력 테스트 케이스 목록')

    proposed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='problem_proposals',
        verbose_name='제안자'
    )
    status = models.CharField(
        '상태',
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_problems',
        verbose_name='검토자'
    )
    review_comment = models.TextField('검토 의견', blank=True)
    created_at = models.DateTimeField('제안일', auto_now_add=True)
    reviewed_at = models.DateTimeField('검토일', null=True, blank=True)

    class Meta:
        db_table = 'problem_proposals'
        verbose_name = '문제 제안'
        verbose_name_plural = '문제 제안 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.problem_id}] {self.title} - {self.get_status_display()}"


class ProblemSession(models.Model):
    """문제 풀이 세션 추적"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='problem_sessions')
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE, related_name='sessions')

    # 시간 추적
    started_at = models.DateTimeField('시작 시간', auto_now_add=True)
    first_hint_at = models.DateTimeField('첫 힌트 요청 시간', null=True, blank=True)
    first_run_at = models.DateTimeField('첫 실행 시간', null=True, blank=True)
    solved_at = models.DateTimeField('해결 시간', null=True, blank=True)

    # 행동 추적
    hint_count = models.IntegerField('힌트 요청 횟수', default=0)
    run_count = models.IntegerField('실행 횟수', default=0)
    max_code_length = models.IntegerField('최대 코드 길이', default=0)

    # 결과
    is_solved = models.BooleanField('해결 여부', default=False)

    class Meta:
        db_table = 'problem_sessions'
        verbose_name = '문제 풀이 세션'
        verbose_name_plural = '문제 풀이 세션 목록'
        ordering = ['-started_at']
        unique_together = ['user', 'problem']  # 한 사용자가 같은 문제에 대해 하나의 세션만 유지

    def __str__(self):
        return f"{self.user.username} - {self.problem.title}"

    def calculate_difficulty_score(self):
        """이 세션의 난이도 점수 계산 (0~100, 높을수록 어려워함)"""
        score = 0

        # 1. 힌트 요청 시간 (빠를수록 어려워함)
        if self.first_hint_at:
            time_to_hint = (self.first_hint_at - self.started_at).total_seconds()
            if time_to_hint < 60:  # 1분 이내
                score += 30
            elif time_to_hint < 300:  # 5분 이내
                score += 20
            elif time_to_hint < 600:  # 10분 이내
                score += 10

        # 2. 힌트 요청 횟수 (많을수록 어려워함)
        score += min(self.hint_count * 10, 30)

        # 3. 실행 횟수 (많을수록 시행착오가 많음)
        score += min(self.run_count * 3, 20)

        # 4. 코드 길이 (짧을수록 어려워함 - 진전이 없음)
        if self.max_code_length < 50:
            score += 20
        elif self.max_code_length < 100:
            score += 10

        return min(score, 100)


class AIModelConfig(models.Model):
    """AI 모델 설정 (싱글톤 패턴)"""
    MODE_CHOICES = [
        ('api', 'API 방식 (Hugging Face)'),
        ('openai', 'OpenAI API'),
        ('local', '로컬 로드 방식'),
        ('runpod', 'Runpod vLLM 방식'),
    ]

    MODEL_CHOICES = [
        # HuggingFace 모델
        ('meta-llama/Llama-3.2-3B-Instruct', 'Llama 3.2 3B Instruct (HuggingFace)'),
        ('Qwen/Qwen2.5-Coder-32B-Instruct', 'Qwen 2.5 Coder 32B (HuggingFace)'),
        ('mistralai/Mistral-7B-Instruct-v0.3', 'Mistral 7B Instruct (HuggingFace)'),
        ('google/gemma-2-9b-it', 'Gemma 2 9B IT (HuggingFace)'),
        ('ModelCloud/Brumby-14B-Base-GPTQMODEL-W4A16-v2', 'Brumby 14B Base (HuggingFace)'),
        # OpenAI 모델
        ('gpt-5.1', 'GPT-5.1 (OpenAI 최신)'),
        ('gpt-4.1', 'GPT-4.1 (OpenAI)'),
        ('o3', 'o3 (OpenAI 추론 특화)'),
        ('gpt-4o', 'GPT-4o (OpenAI)'),
    ]

    HINT_ENGINE_CHOICES = [
        ('api', '기존 API 방식'),
        ('langgraph', 'LangGraph 방식'),
    ]

    mode = models.CharField(
        '모델 사용 방식',
        max_length=20,
        choices=MODE_CHOICES,
        default='api'
    )
    hint_engine = models.CharField(
        '힌트 엔진',
        max_length=20,
        choices=HINT_ENGINE_CHOICES,
        default='api',
        help_text='힌트 생성 방식 선택 (관리자만 변경 가능)'
    )
    api_key = models.CharField(
        'Hugging Face API Key',
        max_length=200,
        blank=True,
        help_text='HuggingFace API 방식 사용 시 필요'
    )
    openai_api_key = models.CharField(
        'OpenAI API Key',
        max_length=200,
        blank=True,
        help_text='OpenAI API 방식 사용 시 필요'
    )
    model_name = models.CharField(
        '모델 이름',
        max_length=200,
        choices=MODEL_CHOICES,
        default='meta-llama/Llama-3.2-3B-Instruct'
    )
    is_model_loaded = models.BooleanField(
        '모델 로드 여부',
        default=False,
        help_text='로컬 모드에서 모델이 메모리에 로드되었는지 여부'
    )

    # Runpod 관련 필드
    runpod_endpoint = models.URLField(
        'Runpod Endpoint URL',
        max_length=500,
        blank=True,
        null=True,
        help_text='Runpod vLLM 서버 엔드포인트 (예: https://abc-8000.proxy.runpod.net)'
    )
    runpod_api_key = models.CharField(
        'Runpod API Key',
        max_length=200,
        blank=True,
        null=True,
        help_text='Runpod API Key (선택사항, vLLM 서버에 인증이 필요한 경우)'
    )

    updated_at = models.DateTimeField('마지막 수정일', auto_now=True)

    class Meta:
        db_table = 'ai_model_config'
        verbose_name = 'AI 모델 설정'
        verbose_name_plural = 'AI 모델 설정'

    def save(self, *args, **kwargs):
        # 싱글톤 패턴: 항상 ID=1인 레코드만 사용
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_config(cls):
        """설정 가져오기 (없으면 기본값으로 생성)"""
        config, created = cls.objects.get_or_create(pk=1)
        return config

    def __str__(self):
        return f"AI 모델 설정 ({self.get_mode_display()})"


class UserSurvey(models.Model):
    """사용자 설문조사 (로그인 시 1회)"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='survey',
        verbose_name='사용자'
    )

    # 기본 정보
    programming_experience = models.CharField(
        '프로그래밍 경험',
        max_length=20,
        choices=[
            ('beginner', '초급 (0-1년)'),
            ('intermediate', '중급 (1-3년)'),
            ('advanced', '고급 (3년 이상)'),
        ]
    )

    # 학습 목표
    learning_goals = models.JSONField(
        '학습 목표',
        default=list,
        help_text='선택한 학습 목표 리스트 (예: ["알고리즘", "자료구조", "코딩테스트"])'
    )

    # 관심 분야
    interested_topics = models.JSONField(
        '관심 분야',
        default=list,
        help_text='관심 있는 주제 리스트 (예: ["배열", "문자열", "DP"])'
    )

    # 선호 난이도
    preferred_difficulty = models.CharField(
        '선호 난이도',
        max_length=20,
        choices=[
            ('easy', '쉬움 (Level 1-5)'),
            ('medium', '중간 (Level 6-10)'),
            ('hard', '어려움 (Level 11-15)'),
        ]
    )

    # 하루 목표 문제 수
    daily_problem_goal = models.IntegerField(
        '하루 목표 문제 수',
        default=1,
        help_text='하루에 풀고 싶은 문제 개수'
    )

    created_at = models.DateTimeField('제출일', auto_now_add=True)

    class Meta:
        db_table = 'user_surveys'
        verbose_name = '사용자 설문조사'
        verbose_name_plural = '사용자 설문조사 목록'

    def __str__(self):
        return f"{self.user.username}의 설문조사"


class HintMetrics(models.Model):
    """힌트 요청 시 코드 지표 저장 (정적 6개 + LLM 6개)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hint_metrics',
        verbose_name='사용자'
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name='hint_metrics',
        verbose_name='문제'
    )

    # 정적 지표 (6개) - 라이브러리 기반
    syntax_errors = models.IntegerField('문법 오류 개수', default=0)
    test_pass_rate = models.FloatField('테스트 통과율 (%)', default=0, help_text='0-100')
    code_complexity = models.FloatField('코드 복잡도', default=0, help_text='Cyclomatic Complexity')
    code_quality_score = models.FloatField('코드 품질 점수', default=0, help_text='Maintainability Index 0-100')
    algorithm_pattern_match = models.FloatField('알고리즘 패턴 일치도 (%)', default=0, help_text='0-100')
    pep8_violations = models.IntegerField('PEP8 위반 개수', default=0)

    # LLM 지표 (6개) - AI 평가 기반 (1-5점)
    algorithm_efficiency = models.IntegerField('알고리즘 효율성', default=0, help_text='시간/공간 복잡도 1-5')
    code_readability = models.IntegerField('코드 가독성', default=0, help_text='변수명, 주석 1-5')
    design_pattern_fit = models.IntegerField('설계 패턴 적합성', default=0, help_text='알고리즘 패턴 1-5')
    edge_case_handling = models.IntegerField('엣지 케이스 처리', default=0, help_text='경계 조건, 예외 1-5')
    code_conciseness = models.IntegerField('코드 간결성', default=0, help_text='중복 제거, DRY 1-5')
    function_separation = models.IntegerField('함수 분리도', default=0, help_text='모듈화, 단일 책임 1-5')

    # 메타 정보
    hint_count = models.IntegerField('힌트 요청 횟수', default=0)
    hint_config = models.JSONField('힌트 구성', default=dict, help_text='사용자가 선택한 힌트 구성')

    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        db_table = 'hint_metrics'
        verbose_name = '힌트 지표'
        verbose_name_plural = '힌트 지표 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.problem.title} (테스트 통과율: {self.test_pass_rate}%)"


class Badge(models.Model):
    """뱃지 정의 (확장됨)"""
    BADGE_TYPES = [
        # 기존 배지
        ('first_problem', '첫 문제 해결'),
        ('problem_streak_7', '7일 연속 문제 풀이'),
        ('problem_streak_30', '30일 연속 문제 풀이'),
        ('problems_10', '문제 10개 해결'),
        ('problems_50', '문제 50개 해결'),
        ('problems_100', '문제 100개 해결'),
        ('all_easy', '모든 Easy 문제 해결'),
        ('speed_master', '스피드 마스터 (빠른 해결)'),

        # 문법 마스터 시리즈
        ('syntax_typo_monster', '타이핑 괴물'),
        ('syntax_racer', '오타 레이서'),
        ('syntax_careful', '꼼꼼 감정사'),
        ('syntax_perfect', '문법 나치'),

        # 코딩 실력 시리즈
        ('skill_genius', '코딩 천재'),
        ('skill_master', '알고리즘 마스터'),
        ('skill_steady', '꾸준러'),
        ('skill_newbie', '코딩 새싹'),

        # 논리 사고 시리즈
        ('logic_action_first', '일단 고'),
        ('logic_trial_error', '시행착오의 달인'),
        ('logic_king', '로직 킹'),

        # 특수 배지
        ('no_hint_10', '독고다이'),
        ('perfect_coder', '퍼펙트 코더'),
        ('persistence_king', '집념의 화신'),
        ('all_rounder', '만능 엔터테이너'),
        ('attendance_3days', '출석왕'),
        ('hello_world', '헬로 월드'),

        # 유머 배지
        ('korean_grammar', '유사 한국인'),
        ('unbreakable', '불굴의 의지'),
        ('night_owl', '야행성'),
        ('hint_collector', '힌트 수집가'),
        ('button_mania', '버튼 매니아'),
    ]

    CONDITION_TYPES = [
        ('count', '횟수 달성'),
        ('average', '평균 기준'),
        ('streak', '연속 달성'),
        ('first', '최초 달성'),
        ('special', '특수 조건'),
    ]

    badge_type = models.CharField(
        '뱃지 유형',
        max_length=50,
        choices=BADGE_TYPES,
        unique=True
    )
    name = models.CharField('뱃지 이름', max_length=100)
    description = models.TextField('설명')
    icon = models.CharField('아이콘', max_length=10, default='🏆')

    # 획득 조건 관련 필드 추가
    condition_description = models.CharField(
        '획득 조건 설명',
        max_length=200,
        blank=True,
        help_text='사용자에게 표시할 획득 방법 (예: "문제를 10개 풀면 획득")'
    )
    condition_type = models.CharField(
        '조건 유형',
        max_length=20,
        choices=CONDITION_TYPES,
        default='special'
    )
    condition_target = models.IntegerField(
        '목표 값',
        default=0,
        help_text='횟수 조건의 경우 목표 횟수'
    )

    class Meta:
        db_table = 'badges'
        verbose_name = '뱃지'
        verbose_name_plural = '뱃지 목록'

    def __str__(self):
        return self.name


class UserBadge(models.Model):
    """사용자가 획득한 뱃지"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='badges',
        verbose_name='사용자'
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='user_badges',
        verbose_name='뱃지'
    )
    earned_at = models.DateTimeField('획득일', auto_now_add=True)

    class Meta:
        db_table = 'user_badges'
        verbose_name = '사용자 뱃지'
        verbose_name_plural = '사용자 뱃지 목록'
        unique_together = ['user', 'badge']
        ordering = ['-earned_at']

    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class Goal(models.Model):
    """목표 정의"""
    GOAL_TYPES = [
        ('daily_login', '매일 로그인'),
        ('daily_problem', '매일 문제 풀기'),
        ('weekly_problems', '주간 문제 목표'),
        ('monthly_problems', '월간 문제 목표'),
    ]

    goal_type = models.CharField(
        '목표 유형',
        max_length=50,
        choices=GOAL_TYPES
    )
    name = models.CharField('목표 이름', max_length=100)
    description = models.TextField('설명')
    target_value = models.IntegerField('목표 값', help_text='예: 7일, 10문제')

    class Meta:
        db_table = 'goals'
        verbose_name = '목표'
        verbose_name_plural = '목표 목록'

    def __str__(self):
        return self.name


class UserGoal(models.Model):
    """사용자의 목표 진행 상황"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='goals',
        verbose_name='사용자'
    )
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name='user_goals',
        verbose_name='목표'
    )
    current_value = models.IntegerField('현재 값', default=0)
    is_completed = models.BooleanField('완료 여부', default=False)
    started_at = models.DateTimeField('시작일', auto_now_add=True)
    completed_at = models.DateTimeField('완료일', null=True, blank=True)

    class Meta:
        db_table = 'user_goals'
        verbose_name = '사용자 목표'
        verbose_name_plural = '사용자 목표 목록'
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.goal.name} ({self.current_value}/{self.goal.target_value})"

    @property
    def progress_percentage(self):
        """진행률 계산"""
        if self.goal.target_value == 0:
            return 0
        return min(100, (self.current_value / self.goal.target_value) * 100)


class ProblemStatus(models.Model):
    """
    사용자별 문제 상태 추적

    분류:
    - solved: 내가 푼 문제 (모든 테스트 통과 + 지표 최적)
    - upgrade: 업그레이드 (정답이지만 지표 개선 가능)
    - upgrading: 업그레이드(푸는 중) (업그레이드 문제를 다시 풀고 있음)
    """
    STATUS_CHOICES = [
        ('solved', '내가 푼 문제'),
        ('upgrade', '업그레이드'),
        ('upgrading', '업그레이드(푸는 중)')
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='problem_statuses'
    )
    problem = models.ForeignKey(
        Problem,
        on_delete=models.CASCADE,
        related_name='user_statuses'
    )
    status = models.CharField('상태', max_length=20, choices=STATUS_CHOICES, default='upgrade')

    # 최고 점수 기록 (종합 점수)
    best_score = models.FloatField('최고 점수', default=0.0)

    # 별점 (0~3개, 코드 효율성 기반)
    # 0: 미해결, 1: 테스트 통과, 2: 품질 70점 이상, 3: 품질 90점 이상 + 효율성 통과
    star_count = models.IntegerField('별점', default=0)

    # 최초 정답 제출 시간
    first_solved_at = models.DateTimeField('최초 정답일', null=True, blank=True)

    # 최근 제출 시간
    last_submitted_at = models.DateTimeField('최근 제출일', auto_now=True)

    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        db_table = 'problem_status'
        verbose_name = '문제 상태'
        verbose_name_plural = '문제 상태 목록'
        unique_together = ['user', 'problem']
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username} - {self.problem.title} ({self.get_status_display()})"


class HintEvaluation(models.Model):
    """힌트 품질 평가 결과 모델 (Human + LLM-as-Judge)"""
    EVALUATION_TYPE_CHOICES = [
        ('human', '휴먼 평가'),
        ('llm', 'LLM-as-Judge'),
    ]

    # 관계
    hint_request = models.ForeignKey(
        HintRequest,
        on_delete=models.CASCADE,
        related_name='evaluations',
        verbose_name='힌트 요청',
        null=True,
        blank=True
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='hint_evaluations',
        verbose_name='평가자'
    )

    # 평가 유형
    evaluation_type = models.CharField(
        '평가 유형',
        max_length=10,
        choices=EVALUATION_TYPE_CHOICES,
        default='human'
    )

    # 힌트 정보 (직접 저장)
    problem_id = models.CharField('문제 ID', max_length=50)
    problem_title = models.CharField('문제 제목', max_length=200, blank=True)
    user_code = models.TextField('사용자 코드')
    hint_text = models.TextField('힌트 텍스트')
    hint_level = models.CharField('힌트 레벨', max_length=20, blank=True)  # 초급/중급/고급
    hint_purpose = models.CharField('힌트 목적', max_length=20, blank=True)  # completion/optimization/optimal

    # 5개 평가 지표 (1-5점)
    hint_relevance = models.IntegerField('힌트 관련성', default=0, help_text='1-5점')
    educational_value = models.IntegerField('교육적 가치', default=0, help_text='1-5점')
    difficulty_appropriateness = models.IntegerField('난이도 적절성', default=0, help_text='1-5점')
    code_accuracy = models.IntegerField('코드 정확성', default=0, help_text='1-5점')
    completeness = models.IntegerField('완전성', default=0, help_text='1-5점')

    # 평균 점수
    average_score = models.FloatField('평균 점수', default=0.0)

    # 상세 피드백 (JSON)
    feedback = models.JSONField('상세 피드백', default=dict)

    # 종합 의견
    overall_comment = models.TextField('종합 의견', blank=True)

    # 메타 정보
    model_used = models.CharField('사용 모델', max_length=50, blank=True, help_text='LLM 평가 시 사용된 모델')
    created_at = models.DateTimeField('평가일', auto_now_add=True)

    class Meta:
        db_table = 'hint_evaluations'
        verbose_name = '힌트 평가'
        verbose_name_plural = '힌트 평가 목록'
        ordering = ['-created_at']

    def __str__(self):
        eval_type = '휴먼' if self.evaluation_type == 'human' else 'LLM'
        return f"[{eval_type}] {self.problem_id} - 평균 {self.average_score:.1f}점"

    def save(self, *args, **kwargs):
        # 평균 점수 자동 계산
        scores = [
            self.hint_relevance,
            self.educational_value,
            self.difficulty_appropriateness,
            self.code_accuracy,
            self.completeness
        ]
        valid_scores = [s for s in scores if s > 0]
        if valid_scores:
            self.average_score = sum(valid_scores) / len(valid_scores)
        super().save(*args, **kwargs)


class Roadmap(models.Model):
    """사용자 맞춤 로드맵"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='roadmaps',
        verbose_name='사용자'
    )
    recommended_problems = models.JSONField(
        '추천 문제 목록',
        default=list,
        help_text='설문조사 기반으로 생성된 문제 ID 리스트'
    )
    current_step = models.IntegerField('현재 단계', default=0)
    is_active = models.BooleanField('활성화 상태', default=True, help_text='현재 선택된 로드맵 여부')
    created_at = models.DateTimeField('생성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        db_table = 'roadmaps'
        verbose_name = '로드맵'
        verbose_name_plural = '로드맵 목록'
        ordering = ['-is_active', '-created_at']

    def __str__(self):
        active_status = " (활성)" if self.is_active else ""
        return f"{self.user.username}의 로드맵{active_status} - {self.created_at.strftime('%Y-%m-%d')}"

    @property
    def progress_percentage(self):
        """로드맵 진행률 계산"""
        if not self.recommended_problems:
            return 0
        return min(100, (self.current_step / len(self.recommended_problems)) * 100)
