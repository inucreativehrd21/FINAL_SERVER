"""
LangGraph 기반 힌트 시스템

기존 API 방식(hint_api.py)과 병행하여 사용 가능한 LangGraph 기반 힌트 제공 시스템.
그래프 기반으로 힌트 생성 워크플로우를 정의하고 실행합니다.

실행 모드:
- Local 모드: Django 서버 내에서 직접 LangGraph 실행
- Runpod 모드: Runpod Serverless로 힌트 생성 위임 (무거운 LLM 연산 분리)

사용법:
- 기존 방식: POST /coding-test/hints/ (hint_api.request_hint)
- LangGraph 방식: POST /coding-test/hints/langgraph/ (langgraph_hint.request_hint_langgraph)
- 모드 전환: 환경변수 HINT_EXECUTION_MODE='runpod' 또는 'local' (기본: local)

분기 로직 (A~F):
- A: 문법 오류 있음 → 문법 수정 힌트
- B: completion + 테스트 미통과 → 완성 힌트
- C: completion + 테스트 통과 → 축하 + 다음 별 안내
- D: optimization + 테스트 미통과 → 효율적 완성 힌트
- E1: optimization + 다음 별 달성 → 축하 메시지
- E2: optimization + 다음 별 미달성 → 칭찬 + 개선 위치 명시
- F: optimal (별 3개) → 다른 풀이 제안
"""

from typing import TypedDict, List, Dict, Any, Optional
import json
import requests
import os
from pathlib import Path

# LangGraph imports
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None

# OpenAI 신버전 API
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = None

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings

from .models import HintRequest, Problem, AIModelConfig, HintMetrics, ProblemStatus
from .code_analyzer import analyze_code


# ==================== State 정의 ====================

class HintState(TypedDict):
    """LangGraph 힌트 시스템의 상태"""
    # 입력
    problem_id: str
    problem_title: str
    problem_description: str
    user_code: str
    previous_hints: List[str]
    preset: str  # '초급', '중급', '고급', None
    custom_components: Dict[str, bool]  # 6개 구성요소 선택
    user_id: int

    # solution_code 관련
    solutions: List[Dict[str, Any]]  # 문제의 모든 솔루션 목록
    matched_solution: Dict[str, Any]  # 사용자 코드와 가장 유사한 솔루션
    solution_similarity: float  # 유사도 점수 (0-1)

    # 분석 결과 - 정적 메트릭 (6개)
    static_metrics: Dict[str, Any]
    # - syntax_errors: 문법 오류 수
    # - test_pass_rate: 테스트 통과율 (%)
    # - execution_time: 실행 시간 (ms)
    # - memory_usage: 메모리 사용량 (KB)
    # - code_quality_score: 품질 점수 (0-100)
    # - pep8_violations: PEP8 위반 수

    # 분석 결과 - LLM 메트릭 (6개, 각 1-5점)
    llm_metrics: Dict[str, int]
    # - algorithm_efficiency: 알고리즘 효율성
    # - code_readability: 코드 가독성
    # - edge_case_handling: 엣지 케이스 처리
    # - code_conciseness: 코드 간결성
    # - test_coverage_estimate: 테스트 커버리지 추정
    # - security_awareness: 보안 인식

    # 별점 관련
    current_star_count: int  # 현재 별점 (0-3)
    hint_purpose: str  # 'completion', 'optimization', 'optimal'

    # 분기 결정
    hint_branch: str  # 'A', 'B', 'C', 'D', 'E1', 'E2', 'F'
    purpose_context: str  # LLM에게 전달할 컨텍스트
    weak_metrics: List[Dict[str, Any]]  # 약점 지표

    # COH (Chain of Hint) 관련
    coh_depth: int  # 현재 COH 깊이 (0 = 기본, 1+ = COH 적용)
    coh_max_depth: int  # 프리셋별 최대 COH 깊이
    hint_level: int  # 최종 힌트 레벨 (1-9, 1=가장 상세)
    filtered_components: Dict[str, bool]  # COH 레벨로 필터링된 구성요소
    blocked_components: List[str]  # 차단된 구성요소 목록
    coh_status: Dict[str, Any]  # COH 상태 정보 (프론트엔드 전달용)
    is_syntax_error: bool  # 문법 오류 플래그 (분기 A)

    # 힌트 생성
    llm_prompt: str
    hint_content: Dict[str, Any]  # JSON 형태 힌트 응답
    final_hint: str
    hint_type: str

    # 에러
    error: Optional[str]


# ==================== 노드 함수들 ====================

def input_node(state: HintState) -> HintState:
    """입력 검증 및 문제 정보 로드 노드 (solutions 포함)"""
    json_path = Path(__file__).parent / 'data' / 'problems_final_output.json'

    try:
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            problems = json.load(f)

        problem = next((p for p in problems if p['problem_id'] == str(state['problem_id'])), None)

        if problem:
            state['problem_title'] = problem.get('title', '')
            state['problem_description'] = problem.get('description', '')
            # solutions 로드 (solution_code 기반 힌트용)
            state['solutions'] = problem.get('solutions', [])
        else:
            state['error'] = f"문제 ID {state['problem_id']}를 찾을 수 없습니다."
            state['solutions'] = []
    except Exception as e:
        state['error'] = f"문제 로드 실패: {str(e)}"
        state['solutions'] = []

    return state


def purpose_node(state: HintState) -> HintState:
    """별점 조회 및 힌트 목적 결정 노드"""
    if state.get('error'):
        return state

    # DB에서 현재 별점 조회
    try:
        problem_status = ProblemStatus.objects.filter(
            problem__problem_id=state['problem_id'],
            user_id=state.get('user_id')
        ).first()

        if problem_status:
            state['current_star_count'] = problem_status.star_count or 0
        else:
            state['current_star_count'] = 0
    except:
        state['current_star_count'] = 0

    # 힌트 목적 결정
    current_star = state['current_star_count']
    if current_star == 0:
        state['hint_purpose'] = 'completion'
    elif current_star < 3:
        state['hint_purpose'] = 'optimization'
    else:
        state['hint_purpose'] = 'optimal'

    return state


def static_analysis_node(state: HintState) -> HintState:
    """정적 분석 노드 (6개 메트릭)"""
    if state.get('error'):
        return state

    try:
        analysis_result = analyze_code(
            state['user_code'],
            state['problem_id'],
            state.get('previous_hints', [])
        )

        static_metrics = analysis_result.get('static_metrics', {})
        state['static_metrics'] = {
            'syntax_errors': static_metrics.get('syntax_errors', 0),
            'test_pass_rate': static_metrics.get('test_pass_rate', 0),
            'execution_time': static_metrics.get('execution_time', 0),
            'memory_usage': static_metrics.get('memory_usage', 0),
            'code_quality_score': static_metrics.get('code_quality_score', 0),
            'pep8_violations': static_metrics.get('pep8_violations', 0),
            'cyclomatic_complexity': static_metrics.get('cyclomatic_complexity', 0),
        }

    except Exception as e:
        state['error'] = f"정적 분석 실패: {str(e)}"
        state['static_metrics'] = {}

    return state


def llm_eval_node(state: HintState) -> HintState:
    """LLM 메트릭 평가 노드 (6개 메트릭, GPT-4.1 호출)"""
    if state.get('error'):
        return state

    try:
        ai_config = AIModelConfig.get_config()

        # OpenAI API만 지원
        if ai_config.mode != 'openai' or not ai_config.openai_api_key:
            # LLM 평가 생략, 기본값 사용
            state['llm_metrics'] = {
                'algorithm_efficiency': 3,
                'code_readability': 3,
                'edge_case_handling': 3,
                'code_conciseness': 3,
                'test_coverage_estimate': 3,
                'security_awareness': 3,
            }
            return state

        client = OpenAI(api_key=ai_config.openai_api_key)
        model_name = ai_config.model_name or 'gpt-5.1'

        eval_prompt = f"""당신은 코드 평가 전문가입니다. 아래 코드를 평가하고 JSON으로 응답하세요.

[문제]
{state['problem_title']}
{state['problem_description'][:300]}...

[학생 코드]
```python
{state['user_code'][:1000]}
```

각 항목을 1-5점으로 평가하세요 (1=매우 나쁨, 5=매우 좋음):
1. algorithm_efficiency: 알고리즘 효율성 (시간/공간 복잡도)
2. code_readability: 코드 가독성 (변수명, 구조)
3. edge_case_handling: 엣지 케이스 처리
4. code_conciseness: 코드 간결성
5. test_coverage_estimate: 테스트 커버리지 추정
6. security_awareness: 보안 인식 (입력 검증 등)

JSON 형식으로만 응답:
{{"algorithm_efficiency": N, "code_readability": N, "edge_case_handling": N, "code_conciseness": N, "test_coverage_estimate": N, "security_awareness": N}}"""

        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.1,
            max_tokens=200
        )

        response_text = response.choices[0].message.content.strip()

        # JSON 파싱
        try:
            # JSON 블록 추출
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0]
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0]

            llm_metrics = json.loads(response_text)
            state['llm_metrics'] = llm_metrics
        except:
            # 파싱 실패 시 기본값
            state['llm_metrics'] = {
                'algorithm_efficiency': 3,
                'code_readability': 3,
                'edge_case_handling': 3,
                'code_conciseness': 3,
                'test_coverage_estimate': 3,
                'security_awareness': 3,
            }

    except Exception as e:
        # LLM 호출 실패 시 기본값
        state['llm_metrics'] = {
            'algorithm_efficiency': 3,
            'code_readability': 3,
            'edge_case_handling': 3,
            'code_conciseness': 3,
            'test_coverage_estimate': 3,
            'security_awareness': 3,
        }

    return state


def branch_decision_node(state: HintState) -> HintState:
    """분기 결정 노드 (A~F)"""
    if state.get('error'):
        return state

    static_metrics = state.get('static_metrics', {})
    hint_purpose = state.get('hint_purpose', 'completion')
    current_star = state.get('current_star_count', 0)
    user_code = state.get('user_code', '').strip()

    syntax_errors = static_metrics.get('syntax_errors', 0)
    test_pass_rate = static_metrics.get('test_pass_rate', 0)
    code_quality = static_metrics.get('code_quality_score', 0)

    # 분기 결정 로직
    # 분기 A: 코드 없음 또는 문법 오류
    if not user_code or syntax_errors > 0:
        state['hint_branch'] = 'A'
        if not user_code:
            state['purpose_context'] = """
[힌트 목적: 코드 작성 시작] (분기 A)

⚠️ 아직 코드가 작성되지 않았습니다.
먼저 코드를 작성해주세요.

힌트 제공 시:
1. 문제의 입력/출력 형식을 설명하세요
2. 기본적인 코드 구조를 안내하세요
3. 시작점을 제시하세요
"""
        else:
            state['purpose_context'] = f"""
[힌트 목적: 문법 오류 수정] (분기 A)

⚠️ 코드에 문법 오류가 {syntax_errors}개 있습니다.
문법 오류를 먼저 수정해야 합니다.

힌트 제공 시:
1. 오류가 있는 줄 번호를 명시하세요
2. 오류 원인을 설명하세요
3. 수정 방법을 제시하세요
"""
    elif hint_purpose == 'completion':
        if test_pass_rate >= 100:
            # 분기 C: completion + 테스트 통과
            state['hint_branch'] = 'C'
            state['purpose_context'] = f"""
[축하! 테스트 통과!] (분기 C)

🌟 테스트를 처음 통과했습니다!
현재 코드 품질: {code_quality}/100점

다음 목표: 별 2개 (품질 70점 이상)
더 나은 코드를 위한 개선점을 제안해주세요.
"""
        else:
            # 분기 B: completion + 테스트 미통과
            state['hint_branch'] = 'B'
            state['purpose_context'] = f"""
[힌트 목적: 코드 완성] (분기 B)

테스트 통과율: {test_pass_rate}%
아직 테스트를 통과하지 못했습니다.

힌트 제공 시:
1. 입력 처리 방법
2. 적절한 자료구조
3. 핵심 로직의 방향
을 안내해주세요.
"""
    elif hint_purpose == 'optimization':
        if test_pass_rate < 100:
            # 분기 D: optimization + 테스트 미통과
            state['hint_branch'] = 'D'
            state['purpose_context'] = f"""
[힌트 목적: 효율적 완성] (분기 D)

현재 별점: {current_star}개
테스트 통과율: {test_pass_rate}% (아직 미통과)

이전에 통과했지만 코드를 수정하면서 테스트를 통과하지 못하게 되었습니다.
효율성을 고려하면서도 먼저 테스트를 통과하도록 도와주세요.
"""
        else:
            # 테스트 통과한 상태에서 최적화
            # 다음 별 달성 여부 확인
            if current_star == 1 and code_quality >= 70:
                new_star = 2
            elif current_star == 2 and code_quality >= 90:
                new_star = 3
            else:
                new_star = current_star

            if new_star > current_star:
                # 분기 E1: 다음 별 달성
                state['hint_branch'] = 'E1'
                state['purpose_context'] = f"""
[축하! 별 획득!] (분기 E1)

🌟 별 {new_star}개를 획득했습니다!
현재 코드 품질: {code_quality}/100점

{'최고 등급 달성! 다른 풀이 방법도 시도해보세요.' if new_star >= 3 else f'다음 목표: 별 {new_star + 1}개 (품질 90점 필요)'}
"""
            else:
                # 분기 E2: 다음 별 미달성 → 약점 개선
                state['hint_branch'] = 'E2'

                # 약점 분석
                weak_metrics = _identify_weak_metrics(state)
                state['weak_metrics'] = weak_metrics

                if weak_metrics:
                    weak_desc = "\n".join([f"- {w['description']}" for w in weak_metrics])
                    state['purpose_context'] = f"""
[힌트 목적: 코드 품질 개선] (분기 E2)

✅ 좋은 소식: 코드가 정상적으로 동작합니다! 테스트를 모두 통과했습니다.
현재 별점: {current_star}개 ⭐

🎯 다음 별({current_star + 1}개)을 획득하려면 아래 부분을 개선해야 합니다:
{weak_desc}

📍 힌트 제공 시 반드시 포함할 내용:
1. "코드가 정상 동작한다"는 칭찬을 먼저 해주세요
2. 개선이 필요한 **구체적인 코드 위치**(몇 번째 줄, 어떤 함수/변수)를 명시하세요
3. 왜 그 부분이 문제인지 설명하세요
4. 어떻게 수정하면 되는지 구체적인 방법을 제시하세요

다음 별 조건:
- 별 2개: 코드 품질 70점 이상 (현재: {code_quality}점)
- 별 3개: 코드 품질 90점 이상
"""
                else:
                    state['purpose_context'] = f"""
[힌트 목적: 코드 품질 개선] (분기 E2)

✅ 훌륭합니다! 코드가 정상적으로 동작하고, 품질도 우수합니다!
현재 별점: {current_star}개 ⭐

코드가 이미 좋은 상태이지만, 더 나은 코드를 위한 추가 개선점을 찾아보세요.
힌트 제공 시 "코드가 잘 작성되었다"는 점을 먼저 인정해주세요.
"""

    elif hint_purpose == 'optimal':
        # 분기 F: 이미 최적 (별 3개)
        state['hint_branch'] = 'F'
        state['purpose_context'] = f"""
[최고 등급 달성!] (분기 F)

🌟🌟🌟 별 3개 (최적)를 이미 달성했습니다!
현재 코드 품질: {code_quality}/100점

이 문제에 대해 다른 알고리즘이나 자료구조를 사용한 풀이 방법을 제안해주세요.
예: 다른 시간복잡도의 해법, 다른 접근 방식 등
"""
    else:
        state['hint_branch'] = 'B'
        state['purpose_context'] = "[힌트 목적: 일반 도움]"

    return state


# ==================== COH (Chain of Hint) 노드 함수들 ====================

# COH 상수 정의
COH_MAX_DEPTH = {
    '초급': 3,  # 초급 COH3 → 초급 COH2 → 초급 COH1 → 초급
    '중급': 2,  # 중급 COH2 → 중급 COH1 → 중급
    '고급': 1,  # 고급 COH1 → 고급
}

COH_BASE_LEVEL = {
    '초급': 4,  # 기본 레벨 4
    '중급': 7,  # 기본 레벨 7
    '고급': 9,  # 기본 레벨 9
}

# 레벨별 허용 구성요소
# 레벨 1-4 (초급): 모든 6개 구성요소 허용
# 레벨 5-7 (중급): libraries + complexity_hint, edge_cases, improvements
# 레벨 8-9 (고급): complexity_hint, edge_cases, improvements만
ALWAYS_ALLOWED_COMPONENTS = ['complexity_hint', 'edge_cases', 'improvements']
LEVEL_COMPONENTS = {
    1: ['libraries', 'code_example', 'step_by_step', 'complexity_hint', 'edge_cases', 'improvements'],
    2: ['libraries', 'code_example', 'step_by_step', 'complexity_hint', 'edge_cases', 'improvements'],
    3: ['libraries', 'code_example', 'step_by_step', 'complexity_hint', 'edge_cases', 'improvements'],
    4: ['libraries', 'code_example', 'step_by_step', 'complexity_hint', 'edge_cases', 'improvements'],
    5: ['libraries', 'complexity_hint', 'edge_cases', 'improvements'],
    6: ['libraries', 'complexity_hint', 'edge_cases', 'improvements'],
    7: ['libraries', 'complexity_hint', 'edge_cases', 'improvements'],
    8: ['complexity_hint', 'edge_cases', 'improvements'],
    9: ['complexity_hint', 'edge_cases', 'improvements'],
}

import hashlib
import difflib

def _compute_code_similarity(user_code: str, solution_code: str) -> float:
    """
    사용자 코드와 솔루션 코드의 유사도 계산 (0-1)

    구조적 유사도를 측정하여 사용자의 접근 방식과 가장 비슷한 솔루션을 찾습니다.
    """
    # 코드 정규화 (공백, 주석 제거)
    def normalize(code: str) -> List[str]:
        lines = []
        for line in code.strip().split('\n'):
            # 주석 제거
            if '#' in line:
                line = line[:line.index('#')]
            # 공백 정규화
            line = ' '.join(line.split())
            if line:
                lines.append(line.lower())
        return lines

    user_lines = normalize(user_code)
    solution_lines = normalize(solution_code)

    if not user_lines or not solution_lines:
        return 0.0

    # SequenceMatcher로 유사도 계산
    matcher = difflib.SequenceMatcher(None, user_lines, solution_lines)
    return matcher.ratio()


def _extract_code_patterns(code: str) -> set:
    """
    코드에서 주요 패턴 추출 (input 방식, 자료구조, 알고리즘 등)
    """
    patterns = set()
    code_lower = code.lower()

    # 입력 패턴
    if 'map(int' in code_lower:
        patterns.add('map_int_input')
    if 'input().split()' in code_lower:
        patterns.add('split_input')
    if 'sys.stdin' in code_lower:
        patterns.add('sys_stdin')

    # 자료구조
    if 'dict(' in code_lower or '{}' in code:
        patterns.add('dict')
    if 'set(' in code_lower:
        patterns.add('set')
    if 'deque' in code_lower:
        patterns.add('deque')
    if 'heapq' in code_lower or 'heap' in code_lower:
        patterns.add('heap')

    # 알고리즘 패턴
    if 'def ' in code_lower:
        patterns.add('function_defined')
    if 'for ' in code_lower:
        patterns.add('for_loop')
    if 'while ' in code_lower:
        patterns.add('while_loop')
    if 'recursive' in code_lower or ('def ' in code_lower and code_lower.count('def ') < code_lower.count('return')):
        patterns.add('recursion')
    if 'sorted(' in code_lower or '.sort(' in code_lower:
        patterns.add('sorting')
    if 'bisect' in code_lower:
        patterns.add('binary_search')

    return patterns


def _find_most_similar_solution(user_code: str, solutions: List[Dict[str, Any]]) -> tuple:
    """
    사용자 코드와 가장 유사한 솔루션을 찾습니다.

    Returns:
        tuple: (matched_solution, similarity_score)
    """
    if not solutions:
        return None, 0.0

    best_solution = None
    best_score = 0.0

    user_patterns = _extract_code_patterns(user_code)

    for solution in solutions:
        solution_code = solution.get('solution_code', '')
        if not solution_code:
            continue

        # 1. 코드 유사도 (60% 가중치)
        code_similarity = _compute_code_similarity(user_code, solution_code)

        # 2. 패턴 유사도 (40% 가중치)
        solution_patterns = _extract_code_patterns(solution_code)
        if user_patterns or solution_patterns:
            pattern_overlap = len(user_patterns & solution_patterns)
            pattern_total = len(user_patterns | solution_patterns)
            pattern_similarity = pattern_overlap / pattern_total if pattern_total > 0 else 0
        else:
            pattern_similarity = 0

        # 최종 점수
        total_score = (code_similarity * 0.6) + (pattern_similarity * 0.4)

        if total_score > best_score:
            best_score = total_score
            best_solution = solution

    return best_solution, best_score


def solution_match_node(state: HintState) -> HintState:
    """
    사용자 코드와 가장 유사한 솔루션을 매칭하는 노드

    이 노드는 사용자의 접근 방식을 존중하여,
    가장 비슷한 솔루션을 기반으로 "다음 단계"를 안내합니다.
    """
    if state.get('error'):
        return state

    user_code = state.get('user_code', '').strip()
    solutions = state.get('solutions', [])

    if not user_code:
        # 코드가 없으면 매칭 스킵
        state['matched_solution'] = None
        state['solution_similarity'] = 0.0
        return state

    if not solutions:
        # 솔루션이 없으면 매칭 불가
        state['matched_solution'] = None
        state['solution_similarity'] = 0.0
        return state

    # 가장 유사한 솔루션 찾기
    matched, similarity = _find_most_similar_solution(user_code, solutions)

    state['matched_solution'] = matched
    state['solution_similarity'] = similarity

    return state


def _compute_code_hash(code: str) -> str:
    """코드의 정규화된 해시 계산 (공백/주석 제거 후)"""
    # 공백 정규화
    lines = code.strip().split('\n')
    normalized_lines = []
    for line in lines:
        # 주석 제거
        if '#' in line:
            line = line[:line.index('#')]
        # 공백 정규화
        line = ' '.join(line.split())
        if line:
            normalized_lines.append(line)
    normalized_code = '\n'.join(normalized_lines)
    return hashlib.md5(normalized_code.encode()).hexdigest()


def coh_check_node(state: HintState) -> HintState:
    """
    COH 체크 노드: 이전 힌트 기록을 확인하여 COH 깊이 계산

    플로우차트 기반 COH 결정 로직:
    0. 분기 A(문법 오류)? → COH 증가 안 함, is_syntax_error=True
    1. 같은 분기? → 아니오 → COH 초기화 (depth=0)
    2. 문제 해결? → 예 → COH 초기화 (depth=0)
    3. 코드 변경? → 예 → COH 유지 (이전 depth)
    4. 코드 동일 → COH 증가 (depth+1, 최대값 제한)
    """
    if state.get('error'):
        return state

    preset = state.get('preset', '중급')
    hint_branch = state.get('hint_branch', '')
    user_id = state.get('user_id')
    problem_id = state.get('problem_id')
    current_code = state.get('code', '')

    # 현재 코드의 해시 계산
    current_code_hash = _compute_code_hash(current_code)
    state['code_hash'] = current_code_hash

    # 프리셋별 최대 COH 깊이
    max_depth = COH_MAX_DEPTH.get(preset, 2)
    state['coh_max_depth'] = max_depth

    # 분기 A(문법 오류)는 COH 증가 안 함 - 단순 문법 실수는 COH 소모하지 않음
    if hint_branch == 'A':
        state['coh_depth'] = 0
        state['coh_decision'] = 'skip_syntax_error'
        state['is_syntax_error'] = True  # 문법 오류 플래그
        return state

    state['is_syntax_error'] = False

    try:
        # 최근 힌트 기록 조회 (같은 문제, 같은 사용자, LangGraph 방식)
        last_hint = HintRequest.objects.filter(
            user_id=user_id,
            problem_str_id=problem_id,
            is_langgraph=True
        ).order_by('-created_at').first()

        if not last_hint:
            # 이전 힌트 없음 → COH 초기화
            state['coh_depth'] = 0
            state['coh_decision'] = 'init_no_history'
            return state

        # 이전 힌트의 분기 확인
        prev_branch = last_hint.hint_branch or ''
        prev_code_hash = last_hint.code_hash or ''
        prev_coh_depth = last_hint.coh_depth or 0

        # 1. 같은 분기인지 확인
        if prev_branch != hint_branch:
            # 분기 변경 → COH 초기화
            state['coh_depth'] = 0
            state['coh_decision'] = 'init_branch_changed'
            return state

        # 2. 문제 해결 분기인지 확인 (C: first_complete, E1: star_achieved)
        solved_branches = ['C', 'E1']
        if prev_branch in solved_branches:
            # 해결 분기에서 같은 분기로 다시 요청 → COH 초기화
            state['coh_depth'] = 0
            state['coh_decision'] = 'init_problem_solved'
            return state

        # 3. 코드 변경 확인
        if prev_code_hash and prev_code_hash != current_code_hash:
            # 코드 변경됨 → COH 유지 (이전 깊이 그대로)
            state['coh_depth'] = min(prev_coh_depth, max_depth)
            state['coh_decision'] = 'keep_code_changed'
            return state

        # 4. 코드 동일 → COH 증가
        new_depth = min(prev_coh_depth + 1, max_depth)
        state['coh_depth'] = new_depth
        state['coh_decision'] = 'increase_same_code'

    except Exception as e:
        # 오류 시 기본값
        state['coh_depth'] = 0
        state['coh_decision'] = f'error: {str(e)}'

    return state


def coh_level_node(state: HintState) -> HintState:
    """
    COH 레벨 계산 노드: 프리셋과 COH 깊이로 최종 힌트 레벨 계산

    레벨 계산 공식:
    hint_level = base_level - min(coh_depth, max_depth)

    레벨 의미:
    - 레벨 1 (초급 COH3): 거의 정답 수준의 상세 힌트
    - 레벨 4 (초급 기본): 직접적이지만 정답은 아닌 힌트
    - 레벨 7 (중급 기본): 개념적 힌트
    - 레벨 9 (고급 기본): 소크라테스식 질문
    """
    if state.get('error'):
        return state

    preset = state.get('preset', '중급')
    coh_depth = state.get('coh_depth', 0)

    base_level = COH_BASE_LEVEL.get(preset, 7)
    hint_level = base_level - coh_depth

    # 레벨 범위 제한 (1-9)
    hint_level = max(1, min(9, hint_level))
    state['hint_level'] = hint_level

    return state


def component_filter_node(state: HintState) -> HintState:
    """
    구성요소 필터링 노드: 힌트 레벨에 따라 허용되는 구성요소 필터링

    필터링 규칙:
    - 분기 A(문법 오류): 모든 구성요소 비활성화 (summary만 출력)
    - 레벨 1-4: 모든 구성요소 허용
    - 레벨 5-6: libraries + always_allowed
    - 레벨 7-9: always_allowed만 (complexity_hint, edge_cases, improvements)
    """
    if state.get('error'):
        return state

    hint_level = state.get('hint_level', 7)
    custom_components = state.get('custom_components', {})
    is_syntax_error = state.get('is_syntax_error', False)

    # 분기 A(문법 오류)일 때는 구성요소 선택 무시 - summary만 출력
    if is_syntax_error:
        state['filtered_components'] = {}  # 모든 구성요소 비활성화
        state['blocked_components'] = list(custom_components.keys())  # 모두 blocked로 표시

        # COH 상태 정보 (문법 오류용)
        preset = state.get('preset', '중급')
        state['coh_status'] = {
            'preset': preset,
            'coh_depth': 0,
            'max_depth': COH_MAX_DEPTH.get(preset, 2),
            'hint_level': hint_level,
            'level_name': f"{preset} (문법 오류)",
            'allowed_components': [],
            'blocked_components': list(custom_components.keys()),
            'can_get_more_detailed': False,
            'next_level_hint': "문법 오류를 수정한 후 다시 힌트를 요청하세요.",
            'is_syntax_error': True
        }
        return state

    # 해당 레벨에서 허용되는 구성요소
    allowed_components = LEVEL_COMPONENTS.get(hint_level, ALWAYS_ALLOWED_COMPONENTS)

    # 사용자가 선택한 구성요소 중 허용되는 것만 필터링
    filtered_components = {}
    blocked_components = []

    for comp, selected in custom_components.items():
        if selected:
            if comp in allowed_components:
                filtered_components[comp] = True
            else:
                blocked_components.append(comp)
                filtered_components[comp] = False
        else:
            filtered_components[comp] = False

    state['filtered_components'] = filtered_components
    state['blocked_components'] = blocked_components

    # COH 상태 정보 구성 (프론트엔드 전달용)
    preset = state.get('preset', '중급')
    coh_depth = state.get('coh_depth', 0)
    max_depth = state.get('coh_max_depth', COH_MAX_DEPTH.get(preset, 2))

    # 레벨 이름 생성
    if coh_depth == 0:
        level_name = f"{preset} 기본"
    else:
        level_name = f"{preset} COH{coh_depth}"

    state['coh_status'] = {
        'preset': preset,
        'coh_depth': coh_depth,
        'max_depth': max_depth,
        'hint_level': hint_level,
        'level_name': level_name,
        'allowed_components': allowed_components,
        'blocked_components': blocked_components,
        'can_get_more_detailed': coh_depth < max_depth,
        'next_level_hint': f"같은 유형의 힌트를 {max_depth - coh_depth}번 더 요청하면 더 상세한 힌트를 받을 수 있습니다." if coh_depth < max_depth else "이미 가장 상세한 힌트 레벨입니다."
    }

    return state


def _identify_weak_metrics(state: HintState) -> List[Dict[str, Any]]:
    """약점 지표 식별"""
    weak_metrics = []
    static_metrics = state.get('static_metrics', {})
    llm_metrics = state.get('llm_metrics', {})

    # 정적 메트릭 기준
    if static_metrics.get('cyclomatic_complexity', 0) > 10:
        weak_metrics.append({
            'metric': 'cyclomatic_complexity',
            'value': static_metrics['cyclomatic_complexity'],
            'description': '순환 복잡도가 높습니다. 함수를 분리하세요.'
        })

    if static_metrics.get('pep8_violations', 0) > 5:
        weak_metrics.append({
            'metric': 'pep8_violations',
            'value': static_metrics['pep8_violations'],
            'description': 'PEP8 위반이 많습니다. 코드 스타일을 정리하세요.'
        })

    if static_metrics.get('code_quality_score', 100) < 70:
        weak_metrics.append({
            'metric': 'code_quality_score',
            'value': static_metrics['code_quality_score'],
            'description': '코드 품질 점수가 낮습니다.'
        })

    # LLM 메트릭 기준 (3점 미만은 약점)
    llm_metric_names = {
        'algorithm_efficiency': '알고리즘 효율성이 낮습니다.',
        'code_readability': '코드 가독성이 낮습니다.',
        'edge_case_handling': '엣지 케이스 처리가 부족합니다.',
        'code_conciseness': '코드가 불필요하게 복잡합니다.',
        'test_coverage_estimate': '테스트 커버리지가 부족해 보입니다.',
        'security_awareness': '입력 검증이 부족합니다.',
    }

    for metric, description in llm_metric_names.items():
        if llm_metrics.get(metric, 3) < 3:
            weak_metrics.append({
                'metric': metric,
                'value': llm_metrics[metric],
                'description': description
            })

    return weak_metrics


def _get_preset_rules(preset: str, hint_level: int = 7) -> str:
    """
    레벨별 힌트 작성 규칙 반환

    hint_level 1-4: 초급 (구체적)
    hint_level 5-7: 중급 (방향 제시)
    hint_level 8-9: 고급 (질문 유도)
    """

    # 레벨별 세부 규칙
    level_rules = {
        1: """
[레벨 1 - 거의 정답]
★ 절대 규칙 ★
- 전체 정답 코드를 제공해야 합니다
- 모든 줄에 주석을 달아야 합니다
- 빈칸 없이 완성된 코드를 제공하세요

★ 필수 출력 ★
- summary: 수정/다음단계 요약
- code_example: 완성된 정답 코드 (주석 포함)
- step_by_step: 모든 단계 상세 설명""",

        2: """
[레벨 2 - 매우 상세]
★ 절대 규칙 ★
- 90% 완성된 코드를 제공합니다
- 핵심 부분 1-2군데만 빈칸(___)으로 남깁니다
- 빈칸 옆에 강한 힌트 주석을 답니다

★ 필수 출력 ★
- summary: 현재 상태 + 해결 방향
- code_example: 빈칸 1-2개가 있는 거의 완성된 코드
- step_by_step: 단계별 설명 (코드 포함)""",

        3: """
[레벨 3 - 상세]
★ 절대 규칙 ★
- 핵심 코드 3-5줄만 제공합니다
- 전체 코드는 제공하지 않습니다
- 수정/추가 주석을 반드시 포함합니다

★ 필수 출력 ★
- summary: "Logic N 완료, 다음은 Logic N+1"
- code_example: 핵심 부분 3-5줄 코드
- step_by_step: 구체적 단계 설명""",

        4: """
[레벨 4 - 직접적]
★ 절대 규칙 ★
- 코드 구조(함수명, 변수명, 반복문)만 제공합니다
- 핵심 로직은 "# TODO: ..." 로 표시합니다
- 정답의 약 50% 정도만 코드로 제공합니다

★ 필수 출력 ★
- summary: 현재 상태 + 다음 작업
- code_example: 구조 + TODO 주석 코드
- step_by_step: 단계별 방향 설명""",

        5: """
[레벨 5 - 개념+상세]
★ 절대 규칙 ★
- 실제 Python 코드를 제공하지 않습니다!!!
- 의사코드(pseudocode)로만 설명합니다
- 알고리즘/자료구조 이름을 명시합니다

★ 필수 출력 ★
- summary: 알고리즘/접근법 설명
- step_by_step: 의사코드 형태 설명
- complexity_hint: 목표 복잡도
- code_example: 제공하지 않음!!!""",

        6: """
[레벨 6 - 개념적]
★ 절대 규칙 ★
- 코드를 절대 제공하지 않습니다!!!
- 알고리즘/자료구조 이름만 언급합니다
- 구현 방법은 설명하지 않습니다

★ 필수 출력 ★
- summary: 핵심 개념 1-2문장
- step_by_step: 개념 수준 단계 (코드 없이)
- code_example: 제공하지 않음!!!""",

        7: """
[레벨 7 - 추상적]
★ 절대 규칙 ★
- 코드를 절대 제공하지 않습니다!!!
- 알고리즘/자료구조 이름도 언급하지 않습니다
- "~를 고려해보세요" 형태로 방향만 제시합니다

★ 필수 출력 ★
- summary: 방향 제시 1-2문장
- step_by_step: 추상적 단계 (개념 이름 없이)
- code_example: 제공하지 않음!!!""",

        8: """
[레벨 8 - 방향 제시]
★ 절대 규칙 ★
- 코드를 절대 제공하지 않습니다!!!
- 키워드 1-2개만 제시합니다
- 적용 방법은 설명하지 않습니다
- 학생이 검색해서 스스로 학습하도록 유도합니다

★ 필수 출력 ★
- summary: 키워드 1-2개 + 짧은 방향
- step_by_step: 제공하지 않음
- code_example: 제공하지 않음!!!""",

        9: """
[레벨 9 - 소크라테스식]
★ 절대 규칙 ★
- 코드를 절대 제공하지 않습니다!!!
- 알고리즘 이름을 절대 언급하지 않습니다!!!
- 오직 질문만 제시합니다
- 질문은 1-2개로 제한합니다
- 답변, 설명, 힌트를 주지 않습니다

★ 필수 출력 ★
- summary: 유도 질문 1-2개만 (답변 없이!!!)
- step_by_step: 제공하지 않음
- code_example: 제공하지 않음!!!"""
    }

    return level_rules.get(hint_level, level_rules[7])


def _build_json_schema(custom_components: Dict[str, bool], preset: str, hint_level: int = 7) -> str:
    """
    선택된 구성요소에 따라 JSON 응답 스키마를 생성합니다.
    LLM이 어떤 필드를 출력해야 하는지 명확하게 지정합니다.
    """
    # 레벨에 따라 summary 설명 변경
    if hint_level == 8:
        summary_schema = '"summary": "완전한 문장 (예: 이 문제는 ~하는 방식을 고려해볼 수 있습니다.)"'
    elif hint_level == 9:
        summary_schema = '"summary": "완전한 질문 문장 (예: ~은 어떻게 처리하면 좋을까요?)"'
    else:
        summary_schema = '"summary": "힌트 요약 (필수)"'

    schema_parts = [summary_schema]

    component_schemas = {
        'libraries': '"libraries": ["라이브러리1", "라이브러리2"]',
        'code_example': '"code_example": "코드 예시 (문자열, 줄바꿈은 \\\\n)"',
        'step_by_step': '"step_by_step": ["1단계: ...", "2단계: ..."]',
        'complexity_hint': '"complexity_hint": "시간/공간 복잡도 힌트"',
        'edge_cases': '"edge_cases": ["엣지케이스1", "엣지케이스2"]',
        'improvements': '"improvements": ["개선사항1", "개선사항2"]'
    }

    for comp, selected in custom_components.items():
        if selected and comp in component_schemas:
            schema_parts.append(component_schemas[comp])

    schema = ",\n    ".join(schema_parts)

    return f"""[필수 JSON 응답 형식]
반드시 아래 형식으로 응답하세요. 선택된 모든 필드를 포함해야 합니다:
```json
{{
    {schema}
}}
```"""


# ==================== LLM 자기검증 함수 ====================

def _verify_hint(
    hint_content: Dict[str, Any],
    hint_level: int,
    filtered_components: Dict[str, bool],
    preset: str,
    ai_config: Any = None
) -> Dict[str, Any]:
    """
    LLM 기반 힌트 자기검증

    생성된 힌트가 레벨별 규칙을 준수하는지 검증합니다.

    Args:
        hint_content: 생성된 힌트 내용
        hint_level: 힌트 레벨 (1-9)
        filtered_components: 필터링된 구성요소
        preset: 프리셋 ('초급', '중급', '고급')
        ai_config: AIModelConfig 객체 (로컬 환경용)

    Returns:
        {
            "is_valid": bool,
            "feedback": str,
            "issues": List[str]
        }
    """
    # ai_config가 없으면 가져오기
    if ai_config is None:
        ai_config = AIModelConfig.get_config()

    if ai_config.mode != 'openai' or not ai_config.openai_api_key:
        # API 없으면 검증 스킵
        return {"is_valid": True, "feedback": "", "issues": []}

    if not OPENAI_AVAILABLE:
        return {"is_valid": True, "feedback": "", "issues": []}

    # 레벨별 검증 기준
    level_criteria = {
        1: "전체 정답 코드가 주석과 함께 제공되어야 합니다. 빈칸 없이 완성된 코드여야 합니다.",
        2: "90% 완성된 코드에 1-2개의 빈칸(___)이 있어야 합니다. 빈칸 옆에 힌트 주석이 있어야 합니다.",
        3: "핵심 코드 3-5줄만 제공되어야 합니다. 전체 코드는 제공되면 안 됩니다.",
        4: "코드 구조와 TODO 주석만 제공되어야 합니다. 정답의 약 50%만 코드로 제공되어야 합니다.",
        5: "실제 Python 코드가 있으면 안 됩니다. 의사코드로만 설명해야 합니다. 알고리즘/자료구조 이름은 명시해야 합니다.",
        6: "코드가 있으면 안 됩니다. 알고리즘/자료구조 이름만 언급해야 합니다. 구현 방법은 설명하면 안 됩니다.",
        7: "코드가 있으면 안 됩니다. 알고리즘/자료구조 이름도 언급하면 안 됩니다. 방향만 제시해야 합니다.",
        8: "코드가 있으면 안 됩니다. summary는 반드시 완전한 문장이어야 합니다. '키워드, 키워드' 형태의 쉼표로 구분된 단어 나열은 절대 금지입니다.",
        9: "코드가 있으면 안 됩니다. summary는 반드시 질문 형태의 완전한 문장이어야 합니다. 키워드 나열 금지, 오직 유도 질문만 있어야 합니다."
    }

    criterion = level_criteria.get(hint_level, level_criteria[7])
    hint_json = json.dumps(hint_content, ensure_ascii=False, indent=2)

    verify_prompt = f"""당신은 코딩 힌트 품질 검증 전문가입니다.

[검증 대상 힌트]
```json
{hint_json}
```

[힌트 레벨]: {hint_level}/9 ({preset})

[레벨 {hint_level} 검증 기준]
{criterion}

[검증 규칙]
{_get_preset_rules(preset, hint_level)}

위 힌트가 레벨 {hint_level}의 규칙을 준수하는지 검증하세요.

JSON으로 응답하세요:
{{
    "is_valid": true/false,
    "issues": ["문제점1", "문제점2", ...],
    "feedback": "수정 지침 (is_valid가 false일 때만)"
}}

검증 시 확인사항:
1. code_example이 레벨 규칙에 맞는 상세도인가?
2. step_by_step이 너무 구체적이거나 추상적이지 않은가?
3. main_hint가 레벨에 맞는 형식인가?
4. 레벨 5-9에서 실제 Python 코드가 포함되어 있지 않은가?"""

    try:
        client = OpenAI(api_key=ai_config.openai_api_key)
        model_name = ai_config.model_name or 'gpt-5.1'

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "당신은 힌트 품질 검증 전문가입니다. JSON 형식으로만 응답하세요."},
                {"role": "user", "content": verify_prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()

        # JSON 추출
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0]
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0]

        result = json.loads(response_text)
        return {
            "is_valid": result.get("is_valid", True),
            "feedback": result.get("feedback", ""),
            "issues": result.get("issues", [])
        }

    except Exception as e:
        # 검증 실패 시 통과 처리 (힌트 생성 자체는 유지)
        return {"is_valid": True, "feedback": "", "issues": []}


def build_prompt_node(state: HintState) -> HintState:
    """
    프롬프트 구성 노드 (9단계 COH 레벨 반영)

    레벨별 힌트 스타일 (모든 레벨에서 "다음 단계 코드만" 제공):
    - 레벨 1 (초급 COH3): 거의 정답 - 다음 단계 3-5줄 + 주석
    - 레벨 2 (초급 COH2): 매우 상세 - 다음 단계 3-5줄 + 빈칸 1개
    - 레벨 3 (초급 COH1): 상세 - 다음 단계 2-3줄
    - 레벨 4 (초급 기본): 직접적 - 코드 구조 + TODO
    - 레벨 5 (중급 COH2): 개념+상세 - 의사코드
    - 레벨 6 (중급 COH1): 개념적 - 알고리즘명만
    - 레벨 7 (중급 기본): 추상적 - 방향만
    - 레벨 8 (고급 COH1): 방향 제시 - 문장으로
    - 레벨 9 (고급 기본): 소크라테스식 - 질문만
    """
    if state.get('error'):
        return state

    preset = state.get('preset', '중급')
    custom_components = state.get('filtered_components', state.get('custom_components', {}))
    purpose_context = state.get('purpose_context', '')
    previous_hints = state.get('previous_hints', [])
    hint_level = state.get('hint_level', 7)
    coh_depth = state.get('coh_depth', 0)

    # 매칭된 솔루션 정보
    matched_solution = state.get('matched_solution')
    solution_similarity = state.get('solution_similarity', 0)
    solution_code = matched_solution.get('solution_code', '') if matched_solution else ''

    # ==================== 9단계 레벨별 프롬프트 ====================

    # 문법 오류 여부 확인
    is_syntax_error = state.get('is_syntax_error', False)
    syntax_errors = state.get('static_metrics', {}).get('syntax_errors', 0)

    level_instructions = {
        1: f"""
[레벨 1/9 - 거의 정답 (초급 COH3)]

★ "다음 단계"의 정의 (최우선 규칙) ★
반드시 "오직 한 가지 작업만" 안내하세요!

1. solution_code와 user_code를 비교하세요
2. user_code에서 이미 구현된 부분을 파악하세요
3. solution_code에서 user_code 바로 다음에 오는 "한 가지 작업"만 찾으세요
4. 그 "한 가지 작업"에 해당하는 코드만 제공하세요

예를 들어 solution_code가:
  1. 입력 받기
  2. 보드 저장하기
  3. 패턴 비교하기
  4. 결과 출력하기
이고, user_code가 "1. 입력 받기"까지 완료했다면:
→ "2. 보드 저장하기"에 해당하는 코드만 제공 (3, 4번은 제공하지 않음!)

⛔ 잘못된 예 (두 가지 이상 언급 - 절대 금지!):
- "정수로 변환하고, 보드를 저장해야 합니다" ← 금지!
- "입력을 받고 리스트에 저장하세요" ← 금지!
- "N을 읽고, 보드 데이터를 만들어야 합니다" ← 금지!

✅ 올바른 예 (오직 한 가지만 언급):
- "정수로 변환하면 됩니다"
- "보드를 저장하면 됩니다"
- "N을 읽으면 됩니다"

★ 출력 형식 ★
- summary: "현재 [완료된 부분]. 다음으로 [오직 한 가지 작업만]을 하면 됩니다."
- code_example: 그 한 가지 작업에 해당하는 코드 (주석 포함)
- step_by_step: 이 코드가 무엇을 하는지 설명

예시 (좋은 예):
```python
# 다음 단계: 체스판 데이터를 저장
board = []
for _ in range(N):
    board.append(input())
```
""",

        2: f"""
[레벨 2/9 - 매우 상세 (초급 COH2)]

★ "다음 단계"의 정의 (최우선 규칙) ★
반드시 "오직 한 가지 작업만" 안내하세요!

1. solution_code와 user_code를 비교하세요
2. user_code에서 이미 구현된 부분을 파악하세요
3. solution_code에서 user_code 바로 다음에 오는 "한 가지 작업"만 찾으세요
4. 그 "한 가지 작업"의 코드에서 핵심 1군데를 빈칸(___)으로 만드세요

⛔ 잘못된 예 (두 가지 이상 언급 - 절대 금지!):
- "정수로 변환하고, 보드를 저장해야 합니다" ← 금지!
- "입력을 받고 리스트에 저장하세요" ← 금지!

✅ 올바른 예 (오직 한 가지만 언급):
- "정수로 변환해야 합니다. 빈칸을 채워보세요."
- "보드를 저장해야 합니다. 빈칸을 채워보세요."

★ 출력 형식 ★
- summary: "현재 [상태]. [오직 한 가지 작업만]이 필요합니다. 빈칸을 채워보세요."
- code_example: 빈칸 1개가 있는 다음 단계 코드
- step_by_step: 각 줄 설명

예시 (좋은 예):
```python
# 다음 단계: 체스판 데이터를 저장
board = []
for _ in range(___):  # 힌트: 몇 줄?
    board.append(input())
```
""",

        3: f"""
[레벨 3/9 - 상세 (초급 COH1)]

★ "다음 단계"의 정의 (최우선 규칙) ★
반드시 "오직 한 가지 작업만" 안내하세요!

1. user_code 다음에 해야 할 "한 가지 작업"을 파악
2. 그 작업의 핵심 코드 2-3줄만 제공

⛔ 잘못된 예 (두 가지 이상 언급 - 절대 금지!):
- "입력을 정수로 바꾸고, 리스트에 저장하세요" ← 금지!

✅ 올바른 예 (오직 한 가지만 언급):
- "입력을 정수로 바꾸면 됩니다"
- "리스트에 저장하면 됩니다"

★ 출력 형식 ★
- summary: "[완료된 부분]은 잘 되었습니다. 이제 [오직 한 가지 작업만]을 해보세요."
- code_example: 핵심 코드 2-3줄만
- step_by_step: 작업 방향

예시: `board = [input() for _ in range(N)]`
""",

        4: f"""
[레벨 4/9 - 직접적 (초급 기본)]

★ "다음 단계"의 정의 (최우선 규칙) ★
반드시 "오직 한 가지 작업만" 안내하세요!

1. user_code 다음에 해야 할 "한 가지 작업"을 파악
2. 그 작업의 구조만 제시 (TODO로 표시)

⛔ 잘못된 예 (두 가지 이상 언급 - 절대 금지!):
- "크기를 입력받고, 보드 데이터를 저장하세요" ← 금지!

✅ 올바른 예 (오직 한 가지만 언급):
- "크기를 입력받으세요"
- "보드 데이터를 저장하세요"

★ 출력 형식 ★
- summary: 현재 상태 + 다음에 해야 할 오직 한 가지 작업만
- code_example: 구조 + TODO
- step_by_step: 구현 방향

예시:
```python
board = []
# TODO: N번 반복하며 각 줄을 입력받아 board에 추가
```
""",

        5: f"""
[레벨 5/9 - 개념+상세 (중급 COH2)]

★ 분석 (순서대로 확인) ★
1. user_code에 문법 오류가 있는가? (syntax_errors: {syntax_errors}개)
   → 문법 오류 있으면: "N번 줄에서 문법을 확인해보세요. [구체적 힌트]" 형태
2. solution_code와 비교하여 로직 오류가 있는가?
   → 로직 오류 있으면: 의사코드로 올바른 흐름 설명
3. 둘 다 정상이면 → 다음 단계 의사코드 제공

★ 힌트 작성 규칙 ★
- 의사코드(pseudocode)로 알고리즘 흐름을 설명하세요
- 실제 Python 코드는 제공하지 마세요
- 알고리즘 이름, 자료구조 이름을 명시하세요
- 문법 오류 시: "출력 함수의 철자를 확인해보세요" 형태로 유도

★ 출력 형식 ★
- summary: 사용할 알고리즘/접근법 설명 (문장 형태)
- step_by_step: 의사코드 형태의 단계 설명
- code_example: 제공하지 않음
""",

        6: f"""
[레벨 6/9 - 개념적 (중급 COH1)]

★ 분석 (순서대로 확인) ★
1. user_code에 문법 오류가 있는가? (syntax_errors: {syntax_errors}개)
   → 문법 오류 있으면: "코드에서 함수/변수명을 다시 확인해보세요" 형태
2. user_code의 접근법이 올바른지 확인
   → 방향이 틀리면: 올바른 개념 제시
3. 방향이 맞으면 → 다음 단계 개념 제시

★ 힌트 작성 규칙 ★
- 알고리즘/자료구조 이름만 언급하세요
- 구체적인 구현 방법은 설명하지 마세요
- 문법 오류 시: 코드 제공 없이 확인할 부분만 문장으로 안내

★ 출력 형식 ★
- summary: 핵심 개념 1-2문장 (완전한 문장으로)
- step_by_step: 개념 수준의 단계
- code_example: 제공하지 않음
""",

        7: f"""
[레벨 7/9 - 추상적 (중급 기본)]

★ 분석 (순서대로 확인) ★
1. user_code에 문법 오류가 있는가? (syntax_errors: {syntax_errors}개)
   → 문법 오류 있으면: "코드의 기본 구조를 다시 확인해보세요" 형태
2. user_code의 방향이 맞는지만 확인
   → 방향이 틀리면: 올바른 방향 제시 (추상적으로)
3. 방향이 맞으면 → 다음 고려사항 제시

★ 힌트 작성 규칙 ★
- 구체적인 알고리즘/자료구조 이름을 언급하지 마세요
- "~를 고려해보세요", "~에 집중해보세요" 형태의 완전한 문장
- 문법 오류 시: 추상적으로 확인 방향만 제시

★ 출력 형식 ★
- summary: 방향 제시 1-2문장 (완전한 문장으로)
- step_by_step: 추상적 단계
- code_example: 제공하지 않음
""",

        8: f"""
[레벨 8/9 - 방향 제시 (고급 COH1)]

⛔⛔⛔ 최우선 금지 규칙 ⛔⛔⛔
summary에 쉼표(,)로 구분된 키워드/명사 나열 절대 금지!
작성 후 반드시 확인: summary에 "A, B"나 "A, B, C" 패턴이 있으면 다시 작성하세요!

⛔ 금지 패턴 (이렇게 쓰면 안 됨):
- "순환 이동, 곱의 합" ← 금지!
- "부분 보드, 패턴 비교" ← 금지!
- "브루트포스, 완전탐색" ← 금지!
- "DFS, BFS" ← 금지!
- 어떤 형태든 "명사, 명사" 패턴 금지!

★ summary 작성 규칙 ★
반드시 주어+서술어가 있는 완전한 문장으로 작성:
- "이 문제는 ~하는 방식을 고려해볼 수 있습니다."
- "~하는 방법을 생각해보세요."
- "~에 집중해보시면 좋겠습니다."

✅ 올바른 예:
- "이 문제는 배열의 요소를 한 칸씩 이동시키면서 각 위치에서의 값을 계산하는 방식을 고려해볼 수 있습니다."
- "원본과 목표를 비교하여 다른 부분을 찾는 방법을 생각해보세요."
- "모든 가능한 위치를 순회하며 조건을 확인하는 접근법이 있습니다."

★ 출력 형식 ★
- summary: 완전한 문장 1-2개 (쉼표로 키워드 나열 금지!)
- complexity_hint, edge_cases, improvements: 사용자가 선택한 경우에만 질문 형태로 제공
""",

        9: f"""
[레벨 9/9 - 소크라테스식 (고급 기본)]

★ summary 작성 규칙 (최우선) ★
summary는 반드시 아래 형식의 완전한 질문 문장으로 작성하세요:
- "~은(는) 어떻게 처리하면 좋을까요?"
- "~을(를) 고려해보셨나요?"
- "현재 코드에서 ~하는 부분은 어디인가요?"

예시:
- "현재 코드에서 반복적으로 수행해야 하는 작업은 무엇일까요?"
- "입력을 어떤 형태로 저장하면 좋을지 생각해보셨나요?"
- "두 패턴이 같은지 어떻게 확인할 수 있을까요?"

★ 출력 형식 ★
- summary: 위 형식의 완전한 질문 문장 1-2개
- complexity_hint, edge_cases, improvements: 사용자가 선택한 경우에만 질문 형태로 제공
"""
    }

    # 레벨에 해당하는 지시문 선택
    level_instruction = level_instructions.get(hint_level, level_instructions[7])

    # 선택된 구성요소 - 레벨에 따라 summary 설명 변경
    if hint_level == 8:
        components_instruction = """
[응답에 포함할 항목]
- summary: 완전한 문장으로 방향 제시 (예: "이 문제는 ~하는 방식을 고려해볼 수 있습니다.")
(사용자가 선택한 경우 아래 항목도 포함)
"""
    elif hint_level == 9:
        components_instruction = """
[응답에 포함할 항목]
- summary: 완전한 질문 문장 (예: "~은 어떻게 처리하면 좋을까요?")
(사용자가 선택한 경우 아래 항목도 포함)
"""
    else:
        components_instruction = """
[응답에 포함할 항목]
- summary: 힌트 요약 (필수, 위 레벨에 맞게)
"""

    # 프리셋별 구성요소 설명 (본분은 유지, 상세도만 다름)
    # 초급: 구체적 (코드, 줄 번호 등 직접 제시)
    # 중급: 방향 제시 (무엇을 해야 하는지만)
    # 고급: 질문으로 유도 (스스로 찾도록)

    if preset == '초급':
        component_descriptions = {
            'libraries': '- libraries: 사용하면 좋은 라이브러리 목록과 각 라이브러리의 용도 설명 (리스트)',
            'code_example': '- code_example: **학생의 현재 코드를 기반으로** 수정/보완한 코드 예시 (문자열, 5-10줄). 학생 코드의 구조와 변수명을 유지하고, 수정된 부분에 "# 수정: ..." 주석을 달아주세요. 학생 코드와 무관한 새로운 코드를 작성하지 마세요.',
            'step_by_step': '- step_by_step: **학생의 현재 코드에서 부족한 부분**을 기반으로 한 단계별 해결 방법 (리스트). 예: "1단계: 1번 줄의 `m, n = input().split()`을 `m, n = map(int, input().split())`로 수정하세요" 처럼 구체적인 코드까지 포함하세요.',
            'complexity_hint': '- complexity_hint: 시간/공간 복잡도와 그 이유를 구체적으로 설명',
            'edge_cases': '- edge_cases: **학생의 현재 코드에서 처리되지 않은** 엣지 케이스 목록. 예: "입력이 0일 때 1번 줄에서 에러 발생" 처럼 학생 코드의 어느 부분이 어떤 입력에서 실패하는지 구체적으로 안내하세요.',
            'improvements': '- improvements: **학생의 현재 코드에서 개선할 수 있는 부분** (리스트). 예: "3번 줄의 for문을 리스트 컴프리헨션으로 변경" 처럼 줄 번호와 수정 방법을 구체적으로 언급하세요.',
        }
    elif preset == '중급':
        component_descriptions = {
            'libraries': '- libraries: 사용하면 좋은 라이브러리 목록 (리스트, 용도는 생략)',
            'code_example': '- code_example: 사용 불가 (중급에서는 코드 예시 제공 안 함)',  # 실제로는 차단됨
            'step_by_step': '- step_by_step: **학생의 현재 코드에서 부족한 부분**을 기반으로 한 단계별 해결 방법 (리스트). 예: "1단계: 입력값을 정수로 변환하세요", "2단계: 2차원 리스트로 보드를 저장하세요" 처럼 무엇을 해야 하는지 방향만 제시하고 코드는 주지 마세요.',
            'complexity_hint': '- complexity_hint: 목표 시간/공간 복잡도만 언급 (이유는 생략)',
            'edge_cases': '- edge_cases: **학생의 현재 코드에서 처리되지 않은** 엣지 케이스 목록. 예: "빈 입력 처리", "음수 입력" 처럼 어떤 케이스를 고려해야 하는지만 안내하세요.',
            'improvements': '- improvements: **학생의 현재 코드에서 개선할 수 있는 부분** (리스트). 예: "입력 처리 부분 개선 필요", "반복문 효율성 확인" 처럼 영역만 언급하고 구체적인 수정 방법은 생략하세요.',
        }
    else:  # 고급
        component_descriptions = {
            'libraries': '- libraries: 사용 불가 (고급에서는 라이브러리 힌트 제공 안 함)',  # 실제로는 차단됨
            'code_example': '- code_example: 사용 불가 (고급에서는 코드 예시 제공 안 함)',  # 실제로는 차단됨
            'step_by_step': '- step_by_step: 사용 불가 (고급에서는 단계별 방법 제공 안 함)',  # 실제로는 차단됨
            'complexity_hint': '- complexity_hint: "효율성을 생각해보세요" 형태로 질문으로 유도',
            'edge_cases': '- edge_cases: **학생의 현재 코드를 기반으로** 질문 형태로 안내. 예: "모든 입력 범위를 고려했나요?", "예외 상황은 없을까요?" 처럼 스스로 생각하도록 유도하세요.',
            'improvements': '- improvements: **학생의 현재 코드를 기반으로** 질문 형태로 안내. 예: "더 간결하게 작성할 수 있을까요?", "이 부분이 최선일까요?" 처럼 스스로 개선점을 찾도록 유도하세요.',
        }

    for comp, desc in component_descriptions.items():
        if custom_components.get(comp, False):
            components_instruction += f"\n{desc}"

    # 이전 힌트 컨텍스트
    previous_context = ""
    if previous_hints and isinstance(previous_hints, list) and len(previous_hints) > 0:
        # previous_hints가 문자열 리스트인지, 딕셔너리 리스트인지 확인
        hints_text = []
        for i, h in enumerate(previous_hints[-3:]):
            if isinstance(h, str):
                hint_text = h[:100]
            elif isinstance(h, dict):
                # 딕셔너리인 경우 hint_text 또는 hint 키 사용
                hint_text = str(h.get('hint_text', h.get('hint', str(h))))[:100]
            else:
                hint_text = str(h)[:100]
            hints_text.append(f'{i+1}. {hint_text}...')

        previous_context = f"""
[이전에 제공한 힌트들]
{chr(10).join(hints_text)}

위 힌트들과 중복되지 않는 새로운 관점의 힌트를 제공해주세요.
"""

    # 매칭된 솔루션 정보 구성
    matched_solution = state.get('matched_solution')
    solution_similarity = state.get('solution_similarity', 0)

    solution_context = ""
    if matched_solution and solution_similarity > 0.1:
        solution_code = matched_solution.get('solution_code', '')
        solution_approach = matched_solution.get('approach', '')
        solution_description = matched_solution.get('description', '')

        solution_context = f"""
[참고 솔루션 - 학생의 접근 방식과 가장 유사한 정답 코드]
유사도: {solution_similarity:.0%}
{f'접근 방식: {solution_approach}' if solution_approach else ''}
{f'설명: {solution_description}' if solution_description else ''}
```python
{solution_code[:1500]}
```

⚠️ 중요: 위 솔루션은 학생의 접근 방식과 가장 비슷한 정답입니다.
- 학생의 현재 코드가 "틀렸다"고 하지 마세요
- 학생의 코드에서 "다음 단계로 무엇을 해야 하는지" 안내하세요
- 학생의 코드 구조와 변수명을 존중하면서 힌트를 제공하세요
- code_example은 반드시 위 솔루션을 참고하여 학생 코드 스타일로 작성하세요
"""
    else:
        solution_context = """
[참고 솔루션: 매칭된 솔루션이 없습니다]
학생의 코드를 기반으로 일반적인 힌트를 제공하세요.
"""

    # 초급 레벨(1-4)에서 전체 코드 금지 강화
    code_limit_warning = ""
    if hint_level <= 4:
        code_limit_warning = """
⛔⛔⛔ 최우선 규칙 - 코드 길이 제한 ⛔⛔⛔
- code_example 필드에 10줄 이상의 코드를 절대 작성하지 마세요!
- "전체 코드", "완성 코드", "정답 코드"라는 표현을 사용하지 마세요!
- 오직 "다음 단계"에 해당하는 3-5줄만 제공하세요!
- 이 규칙을 어기면 응답이 거부됩니다!
"""

    prompt = f"""당신은 코딩 테스트 힌트를 제공하는 AI 튜터입니다.
{code_limit_warning}
{purpose_context}

{level_instruction}

[문제 정보]
제목: {state['problem_title']}
설명: {state['problem_description'][:500]}...

[학생의 현재 코드]
```python
{state['user_code'][:1500]}
```
{solution_context}

[코드 분석 결과]
- 테스트 통과율: {state['static_metrics'].get('test_pass_rate', 0)}%
- 코드 품질: {state['static_metrics'].get('code_quality_score', 0)}/100
- 순환 복잡도: {state['static_metrics'].get('cyclomatic_complexity', 0)}
- PEP8 위반: {state['static_metrics'].get('pep8_violations', 0)}개

[LLM 평가 결과]
- 알고리즘 효율성: {state['llm_metrics'].get('algorithm_efficiency', 3)}/5
- 코드 가독성: {state['llm_metrics'].get('code_readability', 3)}/5
- 엣지 케이스 처리: {state['llm_metrics'].get('edge_case_handling', 3)}/5
{previous_context}

{components_instruction}

[중요 규칙]
1. 학생의 현재 코드를 "틀렸다"고 하지 마세요. 대신 "다음 단계"를 안내하세요
2. 학생이 스스로 해결할 수 있도록 방향을 제시하세요
3. 한국어로 친절하게 답변하세요
4. JSON 형식으로 응답하세요
5. **code_example과 힌트는 반드시 참고 솔루션을 기반으로, 학생 코드 스타일을 유지하며 작성하세요**
6. 학생의 접근 방식을 존중하고, 그 방식으로 문제를 풀 수 있도록 안내하세요
{_get_preset_rules(preset, hint_level)}

[중요: code_example은 리스트가 아닌 단일 문자열로 작성하세요. 줄바꿈은 \\n으로 표현합니다.]

{_build_json_schema(custom_components, preset, hint_level)}"""

    state['llm_prompt'] = prompt
    return state


def generate_hint_node(state: HintState) -> HintState:
    """
    힌트 생성 노드 (GPT-4.1 호출) + LLM 자기검증

    자기검증 루프:
    1. 힌트 생성
    2. _verify_hint로 검증
    3. 부적합 시 피드백 반영하여 재생성 (최대 2회)
    """
    if state.get('error'):
        return state

    try:
        ai_config = AIModelConfig.get_config()

        if ai_config.mode != 'openai' or not ai_config.openai_api_key:
            state['error'] = 'OpenAI API 키가 설정되지 않았습니다.'
            return state

        client = OpenAI(api_key=ai_config.openai_api_key)
        model_name = ai_config.model_name or 'gpt-5.1'

        # 검증 관련 상태 초기화
        hint_level = state.get('hint_level', 7)
        preset = state.get('preset', '중급')
        filtered_components = state.get('filtered_components', {})

        # 자기검증은 레벨 5 이상에서만 수행 (초급은 스킵 - 시간 절약)
        # 초급(레벨 1-4)은 코드 예시를 포함하므로 생성 시간이 이미 길고,
        # 레벨 위반 가능성도 낮음
        should_verify = hint_level >= 5
        max_retries = 2 if should_verify else 0
        verification_feedback = None
        final_hint_content = None

        for attempt in range(max_retries + 1):
            # 프롬프트 구성 (재시도 시 피드백 반영)
            current_prompt = state['llm_prompt']
            if verification_feedback:
                current_prompt += f"""

[⚠️ 이전 힌트 검증 실패 - 수정 필요]
{verification_feedback}

위 피드백을 반영하여 레벨 {hint_level} 규칙에 맞게 힌트를 다시 작성하세요."""

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "당신은 코딩 교육 전문가입니다. JSON 형식으로만 응답하세요."},
                    {"role": "user", "content": current_prompt}
                ],
                temperature=0.1,
                max_tokens=1500  # 초급은 코드 포함으로 더 긴 응답 필요
            )

            response_text = response.choices[0].message.content.strip()

            # JSON 파싱
            try:
                if '```json' in response_text:
                    response_text = response_text.split('```json')[1].split('```')[0]
                elif '```' in response_text:
                    response_text = response_text.split('```')[1].split('```')[0]

                hint_content = json.loads(response_text)
            except:
                hint_content = {'summary': response_text}

            # 자기검증 수행 (레벨 5 이상만)
            if not should_verify:
                # 초급: 검증 스킵
                final_hint_content = hint_content
                final_hint_content['_verification'] = {
                    'passed': True,
                    'attempts': 1,
                    'skipped': True,
                    'reason': '초급 레벨은 자기검증 스킵'
                }
                break

            verification = _verify_hint(
                hint_content,
                hint_level,
                filtered_components,
                preset,
                ai_config
            )

            if verification["is_valid"]:
                # 검증 통과
                final_hint_content = hint_content
                final_hint_content['_verification'] = {
                    'passed': True,
                    'attempts': attempt + 1
                }
                break
            else:
                # 검증 실패 - 피드백 저장 후 재시도
                verification_feedback = verification["feedback"]
                if verification["issues"]:
                    verification_feedback += "\n문제점:\n- " + "\n- ".join(verification["issues"])

                # 마지막 시도였다면 그대로 사용
                if attempt == max_retries:
                    final_hint_content = hint_content
                    final_hint_content['_verification'] = {
                        'passed': False,
                        'attempts': attempt + 1,
                        'issues': verification["issues"]
                    }

        state['hint_content'] = final_hint_content

    except Exception as e:
        state['error'] = f"힌트 생성 실패: {str(e)}"

    return state


def format_hint_node(state: HintState) -> HintState:
    """
    최종 힌트 포맷팅 노드

    사용자가 선택한 구성요소는 삭제하지 않음
    COH 레벨에 따라 상세도만 조절 (프롬프트에서 처리)
    프리셋별 구성요소 제한은 프론트엔드에서 처리
    """
    if state.get('error'):
        state['final_hint'] = f"힌트 생성 중 오류가 발생했습니다: {state['error']}"
        state['hint_type'] = 'error'
        return state

    hint_content = state.get('hint_content', {})
    hint_level = state.get('hint_level', 7)

    # 사용자가 선택한 구성요소는 삭제하지 않음
    # COH 레벨에 따라 상세도만 조절됨 (프롬프트에서 처리)

    branch = state.get('hint_branch', '')

    # 분기에 따른 힌트 타입 결정
    hint_type_map = {
        'A': 'syntax_fix',
        'B': 'completion',
        'C': 'first_complete',
        'D': 'efficient_completion',
        'E1': 'star_achieved',
        'E2': 'quality_improvement',
        'F': 'alternative_solution'
    }

    state['hint_type'] = hint_type_map.get(branch, 'general')

    # 최종 힌트 포맷팅
    final_hint = hint_content.get('summary', '')

    # libraries 처리 (문자열 리스트 또는 딕셔너리 리스트 대응)
    if hint_content.get('libraries'):
        libs = hint_content['libraries']
        if isinstance(libs, list) and len(libs) > 0:
            if isinstance(libs[0], dict):
                # 딕셔너리 리스트인 경우: name 또는 library 키에서 추출
                lib_names = [lib.get('name') or lib.get('library') or str(lib) for lib in libs]
            else:
                # 문자열 리스트인 경우
                lib_names = [str(lib) for lib in libs]
            final_hint += f"\n\n📚 추천 라이브러리: {', '.join(lib_names)}"

    # step_by_step 처리 (문자열 리스트 또는 딕셔너리 리스트 대응)
    if hint_content.get('step_by_step'):
        steps = hint_content['step_by_step']
        if isinstance(steps, list) and len(steps) > 0:
            if isinstance(steps[0], dict):
                step_texts = [step.get('step') or step.get('description') or str(step) for step in steps]
            else:
                step_texts = [str(step) for step in steps]
            final_hint += "\n\n📝 단계별 접근:\n" + "\n".join(step_texts)

    if hint_content.get('complexity_hint'):
        final_hint += f"\n\n⏱️ 복잡도 힌트: {hint_content['complexity_hint']}"

    # edge_cases 처리 (문자열 리스트 또는 딕셔너리 리스트 대응)
    if hint_content.get('edge_cases'):
        cases = hint_content['edge_cases']
        if isinstance(cases, list) and len(cases) > 0:
            if isinstance(cases[0], dict):
                case_texts = [case.get('case') or case.get('description') or str(case) for case in cases]
            else:
                case_texts = [str(case) for case in cases]
            final_hint += "\n\n⚠️ 엣지 케이스:\n- " + "\n- ".join(case_texts)

    # improvements 처리 (문자열 리스트 또는 딕셔너리 리스트 대응)
    if hint_content.get('improvements'):
        imps = hint_content['improvements']
        if isinstance(imps, list) and len(imps) > 0:
            if isinstance(imps[0], dict):
                imp_texts = [imp.get('improvement') or imp.get('description') or str(imp) for imp in imps]
            else:
                imp_texts = [str(imp) for imp in imps]
            final_hint += "\n\n💡 개선 사항:\n- " + "\n- ".join(imp_texts)

    if hint_content.get('code_example'):
        code_example = hint_content['code_example']
        # 리스트로 왔을 경우 문자열로 변환
        if isinstance(code_example, list):
            code_example = '\n'.join(code_example)
        # \\n을 실제 줄바꿈으로 변환
        code_example = code_example.replace('\\n', '\n')
        final_hint += f"\n\n💻 코드 예시:\n```python\n{code_example}\n```"

    state['final_hint'] = final_hint
    return state


def save_node(state: HintState) -> HintState:
    """메트릭 저장 및 배지 체크 노드 (code_hash, hint_branch 포함)"""
    # 힌트 기록은 API 엔드포인트에서 저장하지만,
    # 여기서 code_hash와 hint_branch가 state에 있는지 확인
    # (coh_check_node에서 code_hash 설정, branch_node에서 hint_branch 설정)
    return state


# ==================== 병렬 실행 및 스킵 노드 ====================

def parallel_analysis_node(state: HintState) -> HintState:
    """
    병렬 분석 노드: static_analysis와 llm_eval을 동시에 실행
    (Python의 concurrent.futures 사용)
    """
    if state.get('error'):
        return state

    import concurrent.futures

    def run_static():
        return static_analysis_node(state.copy())

    def run_llm_eval():
        return llm_eval_node(state.copy())

    # 병렬 실행
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_static = executor.submit(run_static)
        future_llm = executor.submit(run_llm_eval)

        static_result = future_static.result()
        llm_result = future_llm.result()

    # 결과 병합
    state['static_metrics'] = static_result.get('static_metrics', {})
    state['llm_metrics'] = llm_result.get('llm_metrics', {})

    # 에러 체크
    if static_result.get('error'):
        state['error'] = static_result['error']
    elif llm_result.get('error'):
        state['error'] = llm_result['error']

    return state


# 간단한 케이스 스킵용 정적 힌트 메시지
# 분기 A(문법 오류)는 LLM 힌트 경로로 진행 (SKIP_HINTS에서 제외)
SKIP_HINTS = {
    'C': {  # 첫 정답 축하
        'message': """🎉 축하합니다! 테스트를 처음 통과했습니다!

⭐ 별 1개를 획득했습니다!

💡 다음 단계:
- 별 2개: 코드 품질 70점 이상 달성
- 별 3개: 코드 품질 90점 이상 달성

코드 품질을 높이려면:
- 불필요한 코드 제거
- 변수명 개선
- 효율적인 알고리즘 적용

'힌트 받기'를 다시 눌러 개선점 확인하세요!""",
        'hint_type': 'first_complete'
    },
    'E1': {  # 별 획득 축하
        'message': """🌟 축하합니다! 별을 획득했습니다!

코드 품질이 크게 향상되었습니다.

💡 최고 등급(별 3개)을 위해:
- 시간 복잡도 최적화
- 공간 복잡도 개선
- 더 효율적인 알고리즘 적용

다른 풀이 방법도 시도해보세요!""",
        'hint_type': 'star_achieved'
    }
}


def should_skip_coh(state: HintState) -> str:
    """
    COH 계산을 스킵할지 결정하는 라우터 함수 (branch_node 직후)
    A, C, E1 분기는 정적 메시지를 반환하므로 COH 계산 불필요
    Returns: 'skip' 또는 'continue'
    """
    hint_branch = state.get('hint_branch', '')
    if hint_branch in SKIP_HINTS:
        return 'skip'
    return 'continue'


def should_skip_llm(state: HintState) -> str:
    """
    LLM 호출을 스킵할지 결정하는 라우터 함수
    Returns: 'skip' 또는 'continue'
    """
    hint_branch = state.get('hint_branch', '')

    # 스킵 가능한 분기: A (코드 없음/문법 오류), C (첫 정답), E1 (별 획득)
    if hint_branch in SKIP_HINTS:
        return 'skip'
    return 'continue'


def skip_llm_node(state: HintState) -> HintState:
    """
    LLM 호출 스킵 노드: 정적 메시지로 힌트 생성
    """
    hint_branch = state.get('hint_branch', '')
    skip_config = SKIP_HINTS.get(hint_branch, {})

    # 정적 메시지 사용
    state['hint_content'] = {'summary': skip_config.get('message', '')}
    state['final_hint'] = skip_config.get('message', '')
    state['hint_type'] = skip_config.get('hint_type', 'static')

    return state


# ==================== 그래프 빌드 ====================

def build_hint_graph():
    """
    LangGraph 힌트 그래프 빌드 (solution_code 매칭 + 병렬 분석 + 조건부 COH/LLM 스킵)

    플로우:
    input → solution_match → purpose → parallel_analysis → branch → [조건부 분기 1: should_skip_coh]
        - skip (A,C,E1): skip_llm → save → END
        - continue (B,D,E2,F): coh_check → coh_level → component_filter
                              → prompt → llm_hint → format → save → END

    solution_match 노드:
    - 사용자 코드와 가장 유사한 solution_code를 찾아 매칭
    - 힌트 생성 시 매칭된 솔루션을 기반으로 "다음 단계" 안내
    """
    if not LANGGRAPH_AVAILABLE:
        return None

    workflow = StateGraph(HintState)

    # 노드 추가
    workflow.add_node("input_node", input_node)
    workflow.add_node("solution_match_node", solution_match_node)  # 솔루션 매칭 노드 추가
    workflow.add_node("purpose_node", purpose_node)
    workflow.add_node("parallel_analysis_node", parallel_analysis_node)  # 병렬 분석
    workflow.add_node("branch_node", branch_decision_node)
    # COH 관련 노드 (B, D, E2, F 분기만 사용)
    workflow.add_node("coh_check_node", coh_check_node)
    workflow.add_node("coh_level_node", coh_level_node)
    workflow.add_node("component_filter_node", component_filter_node)
    # LLM 스킵 노드 (A, C, E1 분기용)
    workflow.add_node("skip_llm_node", skip_llm_node)
    # LLM 호출 노드
    workflow.add_node("prompt_node", build_prompt_node)
    workflow.add_node("llm_hint_node", generate_hint_node)
    workflow.add_node("format_node", format_hint_node)
    workflow.add_node("save_node", save_node)

    # 엣지 연결
    workflow.set_entry_point("input_node")
    workflow.add_edge("input_node", "solution_match_node")  # 솔루션 매칭 먼저
    workflow.add_edge("solution_match_node", "purpose_node")
    workflow.add_edge("purpose_node", "parallel_analysis_node")  # 병렬 분석
    workflow.add_edge("parallel_analysis_node", "branch_node")

    # 조건부 분기 1: COH 스킵 여부 (branch_node 직후)
    # A, C, E1 → 정적 메시지 반환 (COH 계산 불필요)
    # B, D, E2, F → COH 계산 필요
    workflow.add_conditional_edges(
        "branch_node",
        should_skip_coh,
        {
            "skip": "skip_llm_node",      # A, C, E1: COH 스킵 → 정적 힌트
            "continue": "coh_check_node"  # B, D, E2, F: COH 계산 진행
        }
    )

    # COH 경로 (B, D, E2, F 분기)
    workflow.add_edge("coh_check_node", "coh_level_node")
    workflow.add_edge("coh_level_node", "component_filter_node")
    workflow.add_edge("component_filter_node", "prompt_node")
    workflow.add_edge("prompt_node", "llm_hint_node")
    workflow.add_edge("llm_hint_node", "format_node")
    workflow.add_edge("format_node", "save_node")

    # 스킵 경로 (A, C, E1 분기)
    workflow.add_edge("skip_llm_node", "save_node")

    workflow.add_edge("save_node", END)

    return workflow.compile()


# 전역 그래프 인스턴스 (싱글톤)
_hint_graph = None

def get_hint_graph():
    """힌트 그래프 인스턴스 반환"""
    global _hint_graph
    if _hint_graph is None:
        _hint_graph = build_hint_graph()
    return _hint_graph


# ==================== 실행 모드 설정 ====================

# 환경변수로 실행 모드 결정
# 'local': Django 서버 내에서 직접 실행 (기본값)
# 'runpod': Runpod Serverless로 위임
HINT_EXECUTION_MODE = os.environ.get('HINT_EXECUTION_MODE', 'local').lower()


def _get_execution_mode() -> str:
    """현재 실행 모드 반환"""
    return HINT_EXECUTION_MODE


def _is_runpod_mode() -> bool:
    """Runpod 모드인지 확인"""
    return HINT_EXECUTION_MODE == 'runpod'


def _run_via_runpod(user, problem_id, user_code, preset, custom_components, previous_hints):
    """
    Runpod Serverless를 통해 힌트 생성

    Django에서 DB 조회 후 Runpod으로 힌트 생성 요청을 전달합니다.
    """
    try:
        from .hint_proxy import request_hint_via_runpod, is_runpod_available

        if not is_runpod_available():
            # Runpod 설정이 없으면 로컬 모드로 폴백
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("[Runpod] Runpod 설정이 없습니다. Local 모드로 폴백합니다.")
            return _run_local_langgraph(user, problem_id, user_code, preset, custom_components, previous_hints)

        # hint_proxy를 통해 Runpod 호출
        success, data, error, status_code = request_hint_via_runpod(
            problem_id=problem_id,
            user_code=user_code,
            user=user,
            preset=preset,
            custom_components=custom_components
        )

        if success:
            # Runpod 응답에 method 표시 추가
            if data:
                data['method'] = 'runpod'
            return (True, data, None, 200)
        else:
            return (False, None, error, status_code)

    except ImportError as e:
        return (False, None, f'hint_proxy 모듈을 찾을 수 없습니다: {str(e)}', 500)
    except Exception as e:
        import traceback
        return (False, None, f'Runpod 호출 오류: {str(e)}\n{traceback.format_exc()}', 500)


def _run_local_langgraph(user, problem_id, user_code, preset, custom_components, previous_hints):
    """
    Local 모드에서 직접 LangGraph 실행 (기존 로직)

    이 함수는 run_langgraph_hint의 Local 모드 로직을 분리한 것입니다.
    """
    if not LANGGRAPH_AVAILABLE:
        return (
            False,
            None,
            'LangGraph가 설치되지 않았습니다. pip install langgraph langchain-core를 실행하세요.',
            503
        )

    if not problem_id:
        return (False, None, '문제 ID가 필요합니다.', 400)

    # 초기 상태 구성 (COH 필드 + solution_code 필드 포함)
    initial_state: HintState = {
        'problem_id': str(problem_id),
        'problem_title': '',
        'problem_description': '',
        'user_code': user_code,
        'code': user_code,
        'previous_hints': previous_hints,
        'preset': preset,
        'custom_components': custom_components,
        'user_id': user.id,
        'solutions': [],
        'matched_solution': None,
        'solution_similarity': 0.0,
        'static_metrics': {},
        'llm_metrics': {},
        'current_star_count': 0,
        'hint_purpose': '',
        'hint_branch': '',
        'purpose_context': '',
        'weak_metrics': [],
        'coh_depth': 0,
        'coh_max_depth': COH_MAX_DEPTH.get(preset, 2),
        'hint_level': COH_BASE_LEVEL.get(preset, 7),
        'code_hash': '',
        'coh_decision': '',
        'filtered_components': {},
        'blocked_components': [],
        'coh_status': {},
        'llm_prompt': '',
        'hint_content': {},
        'final_hint': '',
        'hint_type': '',
        'error': None
    }

    import sys
    import logging
    logger = logging.getLogger(__name__)

    try:
        graph = get_hint_graph()
        if graph is None:
            return (False, None, 'LangGraph 초기화 실패', 500)

        final_state = graph.invoke(initial_state)

        # 힌트 기록 저장
        hint_record = HintRequest.objects.create(
            user=user,
            problem_str_id=problem_id,
            user_code=user_code,
            hint_response=final_state.get('final_hint', ''),
            hint_type=final_state.get('hint_type', 'langgraph'),
            is_langgraph=True,
            code_hash=final_state.get('code_hash', ''),
            hint_branch=final_state.get('hint_branch', ''),
            coh_depth=final_state.get('coh_depth', 0)
        )

        matched_solution = final_state.get('matched_solution')
        solution_info = None
        if matched_solution:
            solution_info = {
                'approach': matched_solution.get('approach', ''),
                'description': matched_solution.get('description', ''),
                'similarity': final_state.get('solution_similarity', 0)
            }

        result_data = {
            'hint': final_state.get('final_hint', ''),
            'hint_content': final_state.get('hint_content', {}),
            'hint_type': final_state.get('hint_type', ''),
            'hint_branch': final_state.get('hint_branch', ''),
            'current_star': final_state.get('current_star_count', 0),
            'hint_purpose': final_state.get('hint_purpose', ''),
            'static_metrics': final_state.get('static_metrics', {}),
            'llm_metrics': final_state.get('llm_metrics', {}),
            'weak_metrics': final_state.get('weak_metrics', []),
            'solution_match': solution_info,
            'solution_similarity': final_state.get('solution_similarity', 0),
            'coh_status': final_state.get('coh_status', {}),
            'hint_level': final_state.get('hint_level', 7),
            'coh_depth': final_state.get('coh_depth', 0),
            'coh_decision': final_state.get('coh_decision', ''),
            'code_hash': final_state.get('code_hash', ''),
            'filtered_components': final_state.get('filtered_components', {}),
            'blocked_components': final_state.get('blocked_components', []),
            'method': 'langgraph_local'
        }

        return (True, result_data, None, 200)

    except Exception as e:
        import traceback
        return (False, None, f'LangGraph 실행 오류: {str(e)}\n{traceback.format_exc()}', 500)


# ==================== 내부 함수 (hint_api.py에서 호출용) ====================

def run_langgraph_hint(user, problem_id, user_code, preset='중급', custom_components=None, previous_hints=None):
    """
    LangGraph 힌트 생성 내부 함수
    hint_api.py에서 직접 호출 가능

    실행 모드에 따라:
    - Local 모드: Django 내에서 직접 LangGraph 실행
    - Runpod 모드: hint_proxy.request_hint_via_runpod 호출

    Returns:
        tuple: (success: bool, data: dict, error: str or None, status_code: int)
    """
    if custom_components is None:
        custom_components = {}
    if previous_hints is None:
        previous_hints = []

    # Runpod 모드인 경우 hint_proxy로 위임
    if _is_runpod_mode():
        return _run_via_runpod(user, problem_id, user_code, preset, custom_components, previous_hints)

    # Local 모드: 기존 로직 실행
    if not LANGGRAPH_AVAILABLE:
        return (
            False,
            None,
            'LangGraph가 설치되지 않았습니다. pip install langgraph langchain-core를 실행하세요.',
            503
        )

    if not problem_id:
        return (False, None, '문제 ID가 필요합니다.', 400)

    # 초기 상태 구성 (COH 필드 + solution_code 필드 포함)
    initial_state: HintState = {
        'problem_id': str(problem_id),
        'problem_title': '',
        'problem_description': '',
        'user_code': user_code,
        'code': user_code,  # coh_check_node에서 code_hash 계산용
        'previous_hints': previous_hints,
        'preset': preset,
        'custom_components': custom_components,
        'user_id': user.id,
        # solution_code 관련 필드 초기화
        'solutions': [],  # input_node에서 로드됨
        'matched_solution': None,  # solution_match_node에서 설정됨
        'solution_similarity': 0.0,  # solution_match_node에서 설정됨
        # 분석 결과 필드
        'static_metrics': {},
        'llm_metrics': {},
        'current_star_count': 0,
        'hint_purpose': '',
        'hint_branch': '',
        'purpose_context': '',
        'weak_metrics': [],
        # COH 관련 필드 초기화
        'coh_depth': 0,
        'coh_max_depth': COH_MAX_DEPTH.get(preset, 2),
        'hint_level': COH_BASE_LEVEL.get(preset, 7),
        'code_hash': '',  # coh_check_node에서 계산됨
        'coh_decision': '',  # COH 결정 이유
        'filtered_components': {},
        'blocked_components': [],
        'coh_status': {},
        # 힌트 생성 필드
        'llm_prompt': '',
        'hint_content': {},
        'final_hint': '',
        'hint_type': '',
        'error': None
    }

    import sys
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.error(f"[LangGraph DEBUG] Starting run_langgraph_hint for user={user.id}, problem={problem_id}")
        sys.stderr.write(f"[LangGraph DEBUG] Starting run_langgraph_hint for user={user.id}, problem={problem_id}\n")
        sys.stderr.flush()

        graph = get_hint_graph()
        if graph is None:
            logger.error("[LangGraph DEBUG] Graph is None!")
            return (False, None, 'LangGraph 초기화 실패', 500)

        logger.error(f"[LangGraph DEBUG] Invoking graph with initial_state...")
        sys.stderr.write(f"[LangGraph DEBUG] Invoking graph...\n")
        sys.stderr.flush()

        # 그래프 실행
        final_state = graph.invoke(initial_state)

        logger.error(f"[LangGraph DEBUG] Graph invoke complete. final_hint length={len(final_state.get('final_hint', ''))}")
        sys.stderr.write(f"[LangGraph DEBUG] Graph invoke complete. final_hint length={len(final_state.get('final_hint', ''))}\n")
        sys.stderr.flush()

        # 힌트 기록 저장 (code_hash, hint_branch, coh_depth 포함)
        logger.error(f"[LangGraph DEBUG] Saving HintRequest...")
        hint_record = HintRequest.objects.create(
            user=user,
            problem_str_id=problem_id,
            user_code=user_code,
            hint_response=final_state.get('final_hint', ''),
            hint_type=final_state.get('hint_type', 'langgraph'),
            is_langgraph=True,
            # COH 관련 필드 저장
            code_hash=final_state.get('code_hash', ''),
            hint_branch=final_state.get('hint_branch', ''),
            coh_depth=final_state.get('coh_depth', 0)
        )
        logger.error(f"[LangGraph DEBUG] HintRequest saved: id={hint_record.id}, branch={final_state.get('hint_branch')}, code_hash={final_state.get('code_hash', '')[:8]}...")

        # 매칭된 솔루션 정보 (민감한 solution_code는 제외)
        matched_solution = final_state.get('matched_solution')
        solution_info = None
        if matched_solution:
            solution_info = {
                'approach': matched_solution.get('approach', ''),
                'description': matched_solution.get('description', ''),
                'similarity': final_state.get('solution_similarity', 0)
            }

        result_data = {
            'hint': final_state.get('final_hint', ''),
            'hint_content': final_state.get('hint_content', {}),
            'hint_type': final_state.get('hint_type', ''),
            'hint_branch': final_state.get('hint_branch', ''),
            'current_star': final_state.get('current_star_count', 0),
            'hint_purpose': final_state.get('hint_purpose', ''),
            'static_metrics': final_state.get('static_metrics', {}),
            'llm_metrics': final_state.get('llm_metrics', {}),
            'weak_metrics': final_state.get('weak_metrics', []),
            # solution_code 매칭 정보
            'solution_match': solution_info,
            'solution_similarity': final_state.get('solution_similarity', 0),
            # COH 관련 정보 추가
            'coh_status': final_state.get('coh_status', {}),
            'hint_level': final_state.get('hint_level', 7),
            'coh_depth': final_state.get('coh_depth', 0),
            'coh_decision': final_state.get('coh_decision', ''),  # COH 결정 이유
            'code_hash': final_state.get('code_hash', ''),  # 코드 해시
            'filtered_components': final_state.get('filtered_components', {}),
            'blocked_components': final_state.get('blocked_components', []),
            'method': 'langgraph'
        }

        logger.error(f"[LangGraph DEBUG] Returning success response")
        sys.stderr.write(f"[LangGraph DEBUG] Returning success response\n")
        sys.stderr.flush()

        return (True, result_data, None, 200)

    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"[LangGraph Error] {error_detail}")
        sys.stderr.write(f"[LangGraph Error] {error_detail}\n")
        sys.stderr.flush()
        return (
            False,
            None,
            f'LangGraph 실행 오류: {str(e)}\n{error_detail}',
            500
        )


# ==================== API 엔드포인트 ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_hint_langgraph(request):
    """
    LangGraph 기반 힌트 요청 API

    Request Body:
    - problem_id: 문제 ID (필수)
    - user_code: 사용자 코드 (필수)
    - preset: 힌트 레벨 ('초급', '중급', '고급') - 기본: '중급'
    - custom_components: 선택할 구성요소 dict
        - libraries: bool
        - code_example: bool
        - step_by_step: bool
        - complexity_hint: bool
        - edge_cases: bool
        - improvements: bool
    - previous_hints: 이전 힌트 목록 (선택)
    """
    problem_id = request.data.get('problem_id')
    user_code = request.data.get('user_code', '')
    preset = request.data.get('preset', '중급')
    custom_components = request.data.get('custom_components', {})
    previous_hints = request.data.get('previous_hints', [])

    success, data, error, status_code = run_langgraph_hint(
        user=request.user,
        problem_id=problem_id,
        user_code=user_code,
        preset=preset,
        custom_components=custom_components,
        previous_hints=previous_hints
    )

    if success:
        return Response({'success': True, 'data': data})
    else:
        return Response({
            'success': False,
            'error': error,
            'fallback_available': True,
            'message': '기존 API 방식(/coding-test/hints/)을 사용해주세요.'
        }, status=status_code)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_langgraph_status(request):
    """LangGraph 시스템 상태 확인 (COH 정보 + Runpod 모드 포함)"""
    # Runpod 가용성 확인
    try:
        from .hint_proxy import is_runpod_available
        runpod_available = is_runpod_available()
    except ImportError:
        runpod_available = False

    return Response({
        'success': True,
        'data': {
            'langgraph_available': LANGGRAPH_AVAILABLE,
            'openai_available': OPENAI_AVAILABLE,
            'graph_initialized': get_hint_graph() is not None if LANGGRAPH_AVAILABLE else False,
            # 실행 모드 정보
            'execution_mode': {
                'current_mode': _get_execution_mode(),
                'is_runpod_mode': _is_runpod_mode(),
                'runpod_available': runpod_available,
                'description': 'Runpod Serverless로 힌트 생성 위임' if _is_runpod_mode() else 'Django 내에서 직접 LangGraph 실행',
                'env_var': 'HINT_EXECUTION_MODE (local|runpod)'
            },
            'nodes': [
                'input_node - 입력 검증 및 문제/솔루션 로드',
                'solution_match_node - 사용자 코드와 가장 유사한 솔루션 매칭',
                'purpose_node - 별점 조회 및 목적 결정',
                'parallel_analysis_node - 정적 분석 + LLM 평가 (병렬)',
                'branch_node - 분기 결정 (A~F)',
                'coh_check_node - COH 깊이 계산',
                'coh_level_node - 힌트 레벨 계산 (1-9)',
                'component_filter_node - 구성요소 필터링',
                'prompt_node - 프롬프트 구성 (solution_code 기반)',
                'llm_hint_node - 힌트 생성 (GPT-4.1)',
                'format_node - 힌트 포맷팅',
                'save_node - 저장'
            ],
            'branches': {
                'A': '문법 오류 수정',
                'B': '코드 완성 힌트',
                'C': '테스트 통과 축하',
                'D': '효율적 완성',
                'E1': '별 획득 축하',
                'E2': '품질 개선',
                'F': '다른 풀이 제안'
            },
            'presets': ['초급', '중급', '고급'],
            'components': ['libraries', 'code_example', 'step_by_step', 'complexity_hint', 'edge_cases', 'improvements'],
            # solution_code 매칭 시스템
            'solution_matching': {
                'description': '사용자 코드와 가장 유사한 solution_code를 찾아 힌트 제공',
                'matching_algorithm': {
                    'code_similarity': '60% 가중치 - difflib.SequenceMatcher 기반 유사도',
                    'pattern_similarity': '40% 가중치 - 코드 패턴 (입력 방식, 자료구조, 알고리즘) 비교'
                },
                'philosophy': [
                    '사용자의 현재 코드를 "틀렸다"고 하지 않음',
                    '사용자의 접근 방식을 존중',
                    '"다음 단계"를 안내하는 방식으로 힌트 제공',
                    'code_example은 매칭된 solution_code를 기반으로 생성'
                ]
            },
            # COH 관련 정보
            'coh_system': {
                'description': 'Chain of Hint - 같은 유형의 힌트 반복 요청 시 점점 상세해지는 시스템',
                'max_depth_per_preset': COH_MAX_DEPTH,
                'base_level_per_preset': COH_BASE_LEVEL,
                'hint_levels': {
                    '1-2': '매우 상세 (거의 정답 수준)',
                    '3-4': '직접적 (초급)',
                    '5-6': '개념적 (중급)',
                    '7-8': '추상적',
                    '9': '소크라테스식 질문 (고급)'
                },
                'component_availability': {
                    'level_1_4': '모든 구성요소 허용',
                    'level_5_6': 'libraries + complexity_hint + edge_cases + improvements',
                    'level_7_9': 'complexity_hint + edge_cases + improvements만'
                }
            }
        }
    })
