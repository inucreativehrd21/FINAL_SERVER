"""
힌트 챗봇 API - 정적 지표 6개 + LLM 지표 6개 사용
"""
import json
import requests
import os
from pathlib import Path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from .models import HintRequest, Problem, AIModelConfig, HintMetrics
from .code_analyzer import analyze_code
from .badge_logic import check_and_award_badges, get_user_metrics_summary


def load_problem_json():
    """문제 JSON 파일 로드"""
    json_path = Path(__file__).parent / 'data' / 'problems_final_output.json'
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def format_code_indentation(code_text):
    """
    LLM 응답에서 코드 블록의 들여쓰기를 정리합니다.
    JSON 문자열로 전달되면서 들여쓰기가 사라지는 문제를 보정합니다.

    Args:
        code_text: LLM이 생성한 코드 문자열

    Returns:
        str: 적절한 들여쓰기가 적용된 코드
    """
    if not code_text:
        return code_text

    lines = code_text.strip().split('\n')
    formatted_lines = []
    indent_level = 0

    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted_lines.append('')
            continue

        # 들여쓰기 감소: elif, else, except, finally 등
        if stripped.startswith(('elif ', 'else:', 'except', 'except:', 'finally:')):
            indent_level = max(0, indent_level - 1)

        # 현재 줄 추가 (들여쓰기 적용)
        formatted_lines.append('    ' * indent_level + stripped)

        # 다음 줄 들여쓰기 증가: def, class, if, for, while, try 등으로 끝나는 경우
        if stripped.endswith(':'):
            indent_level += 1
        # 들여쓰기 감소: return, break, continue, pass, raise로 블록이 끝나는 경우도 고려
        # (단, 함수 내에서 return이 나와도 함수는 계속되므로 조심해야 함)

    return '\n'.join(formatted_lines)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_hint(request):
    """힌트 요청 API - 두 가지 목적별 힌트 제공 (완료/최적화)

    관리자 설정(hint_engine)에 따라:
    - 'api': 기존 API 방식으로 힌트 생성
    - 'langgraph': LangGraph 워크플로우로 힌트 생성
    """
    problem_id = request.data.get('problem_id')
    user_code = request.data.get('user_code', '')
    previous_hints = request.data.get('previous_hints', [])  # Chain of Hints
    manual_purpose = request.data.get('hint_purpose')  # 관리자 화면용 수동 목적 설정

    # AI 설정 가져오기
    try:
        ai_config = AIModelConfig.objects.first()
        if not ai_config:
            return Response({
                'success': False,
                'error': 'AI 모델 설정이 없습니다. 관리자에게 문의하세요.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    except Exception as e:
        return Response({
            'success': False,
            'error': f'AI 설정 로드 실패: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 힌트 엔진 설정 확인 - LangGraph 방식이면 해당 함수로 위임
    hint_engine = getattr(ai_config, 'hint_engine', 'api')
    if hint_engine == 'langgraph':
        import sys
        sys.stderr.write(f"[hint_api DEBUG] Using LangGraph engine\n")
        sys.stderr.flush()

        from .langgraph_hint import run_langgraph_hint
        try:
            success, data, error, status_code = run_langgraph_hint(
                user=request.user,
                problem_id=problem_id,
                user_code=user_code,
                preset=request.data.get('preset', '중급'),
                custom_components=request.data.get('custom_components', {}),
                previous_hints=request.data.get('previous_hints', [])
            )
            sys.stderr.write(f"[hint_api DEBUG] run_langgraph_hint returned: success={success}, status={status_code}\n")
            sys.stderr.flush()

            if success:
                sys.stderr.write(f"[hint_api DEBUG] Building success Response...\n")
                sys.stderr.flush()
                response = Response({'success': True, 'data': data})
                sys.stderr.write(f"[hint_api DEBUG] Response built successfully\n")
                sys.stderr.flush()
                return response
            else:
                return Response({
                    'success': False,
                    'error': error,
                    'fallback_available': True,
                    'message': '기존 API 방식을 사용할 수 없습니다.'
                }, status=status_code)
        except Exception as e:
            import traceback
            sys.stderr.write(f"[hint_api ERROR] Exception in LangGraph call: {traceback.format_exc()}\n")
            sys.stderr.flush()
            return Response({
                'success': False,
                'error': f'LangGraph 호출 중 오류: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 문제 JSON에서 문제 정보 가져오기
    problems = load_problem_json()
    problem = next((p for p in problems if p['problem_id'] == str(problem_id)), None)

    if not problem:
        return Response({
            'success': False,
            'error': f'문제 ID {problem_id}를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    problem_title = problem.get('title', '')
    problem_description = problem.get('description', '')

    # 0단계: 별점 기반 목적 설정
    # 별점(star_count): 0=미해결, 1=테스트통과, 2=품질70+, 3=품질90+
    hint_purpose = manual_purpose  # 수동 설정이 있으면 우선 사용
    current_star_count = 0
    max_star = 3

    if not hint_purpose:
        try:
            from .models import Problem, ProblemStatus
            problem_obj = Problem.objects.filter(problem_id=problem_id).first()
            if problem_obj:
                problem_status = ProblemStatus.objects.filter(
                    user=request.user,
                    problem=problem_obj
                ).first()

                if not problem_status:
                    # 첫 풀이 - 별 0개
                    current_star_count = 0
                    hint_purpose = 'completion'
                else:
                    # 현재 별점 가져오기
                    current_star_count = getattr(problem_status, 'star_count', 0) or 0

                    if current_star_count == 0:
                        # 별 0개: 완성 목적 (테스트 통과 필요)
                        hint_purpose = 'completion'
                    elif current_star_count < max_star:
                        # 별 1-2개: 다음 별 획득 목적 (최적화)
                        hint_purpose = 'optimization'
                    else:
                        # 별 3개 (최고): 이미 최적 - 다른 풀이 제안
                        hint_purpose = 'optimal'
            else:
                hint_purpose = 'completion'
        except Exception as e:
            print(f'Failed to determine hint_purpose: {str(e)}')
            hint_purpose = 'completion'

    # 힌트 구성 가져오기 (커스텀 또는 프리셋)
    preset = request.data.get('preset')  # '초급', '중급', '고급', None
    custom_components = request.data.get('custom_components', {})

    # 커스텀 컴포넌트가 있으면 그것을 사용, 없으면 프리셋에 따라 기본값 설정
    # 요약(summary)은 항상 True
    if custom_components:
        # 커스텀 컴포넌트가 있으면 그것을 사용하고 요약만 항상 True로 설정
        components = custom_components.copy()
        components['summary'] = True
    elif preset == '초급':
        components = {
            'summary': True, 'libraries': True, 'code_example': True,
            'step_by_step': False, 'complexity_hint': False,
            'edge_cases': False, 'improvements': False
        }
    elif preset == '중급':
        components = {
            'summary': True, 'libraries': True, 'code_example': False,
            'step_by_step': False, 'complexity_hint': False,
            'edge_cases': False, 'improvements': False
        }
    elif preset == '고급':
        components = {
            'summary': True, 'libraries': False, 'code_example': False,
            'step_by_step': False, 'complexity_hint': False,
            'edge_cases': False, 'improvements': False
        }
    else:
        # 기본값
        components = {
            'summary': True, 'libraries': False, 'code_example': False,
            'step_by_step': False, 'complexity_hint': False,
            'edge_cases': False, 'improvements': False
        }

    # 4단계: 정적 분석 (12개 메트릭: 정적 6개 + LLM 6개)
    try:
        static_metrics = analyze_code(user_code, problem_id, execution_results=None)
    except Exception as e:
        print(f'Failed to analyze code: {str(e)}')
        static_metrics = {
            'syntax_errors': 0, 'test_pass_rate': 0.0,
            'execution_time': 0.0, 'memory_usage': 0.0,
            'code_quality_score': 0.0, 'pep8_violations': 0
        }

    try:
        from .code_analyzer import evaluate_code_with_llm
        llm_metrics = evaluate_code_with_llm(user_code, problem_description, static_metrics)
    except Exception as e:
        print(f'Failed to evaluate with LLM: {str(e)}')
        llm_metrics = {
            'algorithm_efficiency': 3,
            'code_readability': 3,
            'edge_case_handling': 3,
            'code_conciseness': 3,
            'test_coverage_estimate': 3,
            'security_awareness': 3
        }

    # 3단계: 힌트 분기 결정 로직
    # 분기 A: 문법 오류 있음 → 오류 수정 힌트만
    # 분기 B: 목적이 completion + 로직 미완성 → 완성 힌트
    # 분기 C: 목적이 completion + 로직 완성 → 완성 축하 + 별 평가
    # 분기 D: 목적이 optimization + 로직 미완성 → 효율적 완성 힌트
    # 분기 E: 목적이 optimization + 다음 별 달성 → 축하 + 별 재평가
    # 분기 F: 목적이 optimal → 다른 풀이 제안
    weak_metrics = []
    purpose_context = ""
    hint_branch = ""  # 분기 추적용

    # 로직 완성 여부 판단 (테스트 통과율 기반)
    is_logic_complete = static_metrics['test_pass_rate'] >= 100

    # 분기 A: 문법 오류가 있으면 오류 수정 힌트만 제공 (최우선)
    if static_metrics['syntax_errors'] > 0:
        hint_branch = 'A'
        purpose_context = f"""
[힌트 목적: 문법 오류 수정] (접근법 A)
현재 코드에 문법 오류가 {static_metrics['syntax_errors']}개 있습니다.
오류 수정에만 집중하세요. 최적화나 다른 힌트는 제공하지 마세요.
- 어떤 문법 오류인지 구체적으로 설명
- 어떻게 수정해야 하는지 명확히 제시
- 수정 예시 코드 제공
"""
    elif hint_purpose == 'completion':
        if not is_logic_complete:
            # 분기 B: 완성 목적 + 로직 미완성
            hint_branch = 'B'
            purpose_context = """
[힌트 목적: 코드 완성] (접근법 B)
문법 오류는 없지만 테스트를 통과하지 못하고 있습니다.
코드를 완성하여 테스트를 통과하도록 돕는 힌트를 제공하세요:
- 입력 처리 방법
- 필요한 자료구조 선택
- 핵심 로직 구현 방향
- 출력 형식 맞추기
"""
        else:
            # 분기 C: 완성 목적 + 로직 완성 → 별 1개 획득!
            hint_branch = 'C'
            purpose_context = f"""
[축하! 테스트 통과!] (접근법 C)
🌟 별 1개를 획득했습니다! (현재: {current_star_count} → 1)

코드가 테스트를 통과했습니다. 다음 단계로:
- 현재 코드 품질 점수: {static_metrics['code_quality_score']}/100
- 별 2개 조건: 코드 품질 70점 이상
- 별 3개 조건: 코드 품질 90점 이상

더 높은 별을 받으려면 코드 품질을 개선해보세요!
"""
    elif hint_purpose == 'optimization':
        if not is_logic_complete:
            # 분기 D: 효율 목적인데 로직 미완성
            hint_branch = 'D'
            purpose_context = f"""
[힌트 목적: 효율적 완성] (접근법 D)
현재 별점: {current_star_count}개 (목표: {current_star_count + 1}개)

먼저 테스트를 통과해야 합니다. 효율성도 고려하면서 완성하세요:
- 효율적인 알고리즘 선택
- 적절한 자료구조 사용
- 불필요한 연산 피하기
"""
        else:
            # 분기 E: 효율 목적 + 로직 완성
            # 12개 메트릭 중 약점 파악
            metric_scores = []

            test_pass_score = (static_metrics['test_pass_rate'] / 100) * 5
            if test_pass_score < 4:
                metric_scores.append(('test_pass_rate', test_pass_score, f"테스트 통과율 {static_metrics['test_pass_rate']}%"))

            if static_metrics.get('execution_time', 0) > 100:
                exec_score = max(1, 5 - (static_metrics['execution_time'] / 200))
                metric_scores.append(('execution_time', exec_score, f"실행 시간 {static_metrics['execution_time']}ms"))

            if static_metrics.get('memory_usage', 0) > 1000:
                mem_score = max(1, 5 - (static_metrics['memory_usage'] / 2000))
                metric_scores.append(('memory_usage', mem_score, f"메모리 사용량 {static_metrics['memory_usage']}KB"))

            quality_score = (static_metrics['code_quality_score'] / 100) * 5
            if quality_score < 3.5:
                metric_scores.append(('code_quality', quality_score, f"코드 품질 {static_metrics['code_quality_score']}/100"))

            if static_metrics['pep8_violations'] > 3:
                pep8_score = max(1, 5 - (static_metrics['pep8_violations'] / 2))
                metric_scores.append(('pep8', pep8_score, f"PEP8 위반 {static_metrics['pep8_violations']}개"))

            # LLM 지표 (이미 1-5 스케일)
            for key, value in llm_metrics.items():
                if value < 3.5:
                    metric_scores.append((key, value, f"{key}: {value}/5"))

            metric_scores.sort(key=lambda x: x[1])
            weak_metrics = metric_scores[:2]

            # 다음 별 달성 조건 체크
            next_star_achieved = False
            if current_star_count == 1 and static_metrics['code_quality_score'] >= 70:
                next_star_achieved = True
            elif current_star_count == 2 and static_metrics['code_quality_score'] >= 90:
                next_star_achieved = True

            if next_star_achieved:
                hint_branch = 'E1'
                new_star = current_star_count + 1
                purpose_context = f"""
[축하! 별 {new_star}개 달성!] (접근법 E1)
🌟🌟{'🌟' if new_star >= 3 else ''} 별 {new_star}개를 획득했습니다!

현재 코드 상태:
- 코드 품질: {static_metrics['code_quality_score']}/100
- 테스트 통과율: {static_metrics['test_pass_rate']}%

{'최고 등급 달성! 다른 풀이 방법도 시도해보세요.' if new_star >= 3 else f'다음 목표: 별 {new_star + 1}개 (품질 90점 필요)'}
"""
            else:
                hint_branch = 'E2'
                if weak_metrics:
                    weak_desc = "\n".join([f"- {desc}" for _, _, desc in weak_metrics])
                    purpose_context = f"""
[힌트 목적: 코드 품질 개선] (접근법 E2)

✅ 좋은 소식: 코드가 정상적으로 동작합니다! 테스트를 모두 통과했습니다.
현재 별점: {current_star_count}개 ⭐

🎯 다음 별({current_star_count + 1}개)을 획득하려면 아래 부분을 개선해야 합니다:
{weak_desc}

📍 힌트 제공 시 반드시 포함할 내용:
1. "코드가 정상 동작한다"는 칭찬을 먼저 해주세요
2. 개선이 필요한 **구체적인 코드 위치**(몇 번째 줄, 어떤 함수/변수)를 명시하세요
3. 왜 그 부분이 문제인지 설명하세요
4. 어떻게 수정하면 되는지 구체적인 방법을 제시하세요

다음 별 조건:
- 별 2개: 코드 품질 70점 이상 (현재: {static_metrics['code_quality_score']}점)
- 별 3개: 코드 품질 90점 이상
"""
                else:
                    purpose_context = f"""
[힌트 목적: 코드 품질 개선] (접근법 E2)

✅ 훌륭합니다! 코드가 정상적으로 동작하고, 품질도 우수합니다!
현재 별점: {current_star_count}개 ⭐

코드가 이미 좋은 상태이지만, 더 나은 코드를 위한 추가 개선점을 찾아보세요.
힌트 제공 시 "코드가 잘 작성되었다"는 점을 먼저 인정해주세요.
"""
    elif hint_purpose == 'optimal':
        # 분기 F: 이미 최적 (별 3개)
        hint_branch = 'F'
        purpose_context = f"""
[최고 등급 달성!] (접근법 F)
🌟🌟🌟 별 3개 (최적)를 이미 달성했습니다!

현재 코드 상태:
- 코드 품질: {static_metrics['code_quality_score']}/100
- 테스트 통과율: {static_metrics['test_pass_rate']}%

다른 풀이 방법을 제안해주세요:
- 다른 알고리즘 접근법
- 다른 자료구조 활용
- 더 Pythonic한 방식
- 학습 목적의 대안적 풀이
"""

    # 3단계: 이전 지표 평균 계산 (Chain of Hints)
    try:
        problem_obj = Problem.objects.filter(problem_id=problem_id).first()
        if problem_obj:
            previous_metrics = HintMetrics.objects.filter(
                user=request.user,
                problem=problem_obj
            ).order_by('-created_at')[:5]  # 최근 5개 지표

            if previous_metrics.exists():
                # 정적 지표 평균
                avg_static = {
                    'syntax_errors': sum(m.syntax_errors for m in previous_metrics) / len(previous_metrics),
                    'test_pass_rate': sum(m.test_pass_rate for m in previous_metrics) / len(previous_metrics),
                    'code_complexity': sum(m.code_complexity for m in previous_metrics) / len(previous_metrics),
                    'code_quality_score': sum(m.code_quality_score for m in previous_metrics) / len(previous_metrics),
                    'algorithm_pattern_match': sum(m.algorithm_pattern_match for m in previous_metrics) / len(previous_metrics),
                    'pep8_violations': sum(m.pep8_violations for m in previous_metrics) / len(previous_metrics),
                }
                # LLM 지표 평균
                avg_llm = {
                    'algorithm_efficiency': sum(m.algorithm_efficiency for m in previous_metrics) / len(previous_metrics),
                    'code_readability': sum(m.code_readability for m in previous_metrics) / len(previous_metrics),
                    'design_pattern_fit': sum(m.design_pattern_fit for m in previous_metrics) / len(previous_metrics),
                    'edge_case_handling': sum(m.edge_case_handling for m in previous_metrics) / len(previous_metrics),
                    'code_conciseness': sum(m.code_conciseness for m in previous_metrics) / len(previous_metrics),
                    'function_separation': sum(m.function_separation for m in previous_metrics) / len(previous_metrics),
                }
            else:
                avg_static = None
                avg_llm = None
        else:
            avg_static = None
            avg_llm = None
    except Exception as e:
        print(f'Failed to calculate average metrics: {str(e)}')
        avg_static = None
        avg_llm = None

    # 레벨별 요약 스타일 정의
    summary_style = ""
    if preset == '초급':
        summary_style = """
💡 요약 (summary): 1-2줄로 핵심 개념을 초보자 친화적으로 설명
  ⚠️ 반드시 지켜야 할 규칙:
  - 필요한 함수명이나 라이브러리명을 직접적으로 언급하세요 (예: "collections.Counter를 사용하여 각 문자의 빈도를 세고...")
  - 구체적인 작업이 무엇인지 단계별로 명확히 설명하세요
  - "어떻게"를 중심으로 구체적인 방법을 제시하세요
  - 추상적인 개념이나 질문은 절대 사용하지 마세요"""
    elif preset == '중급':
        summary_style = """
💡 요약 (summary): 1-2줄로 핵심 개념을 중급자에게 설명
  ⚠️ 반드시 지켜야 할 규칙:
  - 함수명이나 라이브러리명을 직접 언급하지 말고, 자료구조나 알고리즘 개념으로만 설명하세요 (예: "해시 테이블을 활용하여 빈도를 추적하고...")
  - "무엇을" 사용해야 하는지에 집중하세요
  - 구체적인 함수명 대신 개념적 접근법을 제시하세요
  - 질문 형식은 사용하지 마세요"""
    elif preset == '고급':
        summary_style = """
💡 요약 (summary): 소크라테스식 질문으로 사고를 유도
  ⚠️ 반드시 지켜야 할 규칙:
  - 반드시 질문 형식으로만 작성하세요 (반드시 '?'로 끝나야 합니다)
  - 직접적인 답이나 해결책을 절대 제시하지 마세요
  - 구체적인 함수명이나 라이브러리명을 절대 언급하지 마세요
  - 학습자가 스스로 사고하도록 핵심 질문으로만 유도하세요 (예: "이 문제에서 중복 계산을 피하려면 어떤 자료구조가 필요할까요?")
  - 2개 이상의 연계된 질문을 사용하여 사고의 흐름을 유도하세요"""
    else:
        summary_style = "💡 요약 (summary): 1-2줄로 핵심 개념 설명"

    # 커스텀 구성 기반 프롬프트 생성
    prompt_components = [summary_style]  # 요약은 항상 포함

    if components.get('libraries'):
        prompt_components.append("""📚 사용 라이브러리 (libraries): 필요한 Python 라이브러리/함수 목록
  ⚠️ 중요: 코드 예시(code_example)에서 실제로 사용하는 라이브러리만 추천하세요
  - 코드 예시가 없거나 표준 내장 함수만 사용한다면, 이 항목은 null로 반환하세요""")
    if components.get('code_example'):
        if preset == '고급':
            prompt_components.append("""📝 코드 예시 (code_example): 학생이 작성한 코드에 이어서 사용할 수 있는 핵심 로직
  ⚠️ 중요 규칙:
  - 학생이 이미 작성한 코드는 절대 중복해서 제시하지 마세요
  - 학생 코드가 틀렸다면: 틀린 부분만 수정하는 방법 제시
  - 학생 코드가 맞다면: 다음 단계 로직만 제시 (예: 입력 처리 후 → 계산 로직)
  - "..."이나 생략 기호를 절대 사용하지 마세요
  - 완전하고 실행 가능한 코드를 작성하세요
  - 함수 분리와 알고리즘적 사고를 유도하는 구조로 작성하세요
  - 코드 블록은 반드시 올바른 Python 들여쓰기(4칸 스페이스)를 포함해야 합니다

  예시:
  - 학생 코드: "a, b = input().split()" (맞음)
    → 다음 단계: "# 입력을 정수로 변환\na, b = int(a), int(b)\n# 계산 로직\nresult = a + b\nprint(result)"
  - 학생 코드: "a, b = input().split()" (틀림 - 정수 변환 누락)
    → 수정: "a, b = map(int, input().split())  # int로 변환 필요" """)
        else:
            prompt_components.append("""📝 코드 예시 (code_example): 간단한 코드 예제 (5-10줄, 핵심 로직 포함)
  ⚠️ 중요 규칙:
  - 학생이 이미 작성한 코드는 절대 중복해서 제시하지 마세요
  - 학생 코드가 틀렸다면: 틀린 부분만 수정
  - 학생 코드가 맞다면: 다음 단계 로직만 제시
  - 코드 블록은 반드시 올바른 Python 들여쓰기(4칸 스페이스)를 포함해야 합니다""")
    if components.get('step_by_step'):
        prompt_components.append("📋 단계별 해결 방법 (step_by_step): 문제 해결 단계를 순서대로 나열")
    if components.get('complexity_hint'):
        prompt_components.append("⏱️ 시간/공간 복잡도 힌트 (complexity_hint): 목표 복잡도와 최적화 방법")
    if components.get('edge_cases'):
        prompt_components.append("⚠️ 엣지 케이스 (edge_cases): 고려해야 할 특수 케이스 목록")
    if components.get('improvements'):
        prompt_components.append("✨ 개선 사항 (improvements): 현재 코드의 개선점 제안")

    components_str = "\n".join(prompt_components)

    # 요약에 포함할 구성 안내 로직
    # 선택한 구성: "→ 더 자세한 내용은 아래 'X' 를 참고하세요."
    # 선택 안 한 구성: "→ 'X' 구성을 선택하면 더 자세한 힌트를 받을 수 있습니다."
    component_guidance = []
    component_names = {
        'libraries': '사용 라이브러리',
        'code_example': '코드 예시',
        'step_by_step': '단계별 해결 방법',
        'complexity_hint': '시간/공간 복잡도',
        'edge_cases': '엣지 케이스',
        'improvements': '개선 사항'
    }

    selected_components = []
    unselected_components = []

    for comp_key, comp_name in component_names.items():
        if components.get(comp_key):
            selected_components.append(comp_name)
        else:
            unselected_components.append(comp_name)

    if selected_components:
        component_guidance.append(f"→ 더 자세한 내용은 아래 '{', '.join(selected_components)}' 를 참고하세요.")
    if unselected_components:
        component_guidance.append(f"→ '{', '.join(unselected_components)}' 구성을 선택하면 더 자세한 힌트를 받을 수 있습니다.")

    component_guidance_str = "\n".join(component_guidance)

    # 이전 힌트 컨텍스트 생성 (Chain of Hints)
    previous_hints_str = ""
    if previous_hints:
        hints_list = []
        for i, prev_hint in enumerate(previous_hints, 1):
            hint_text = prev_hint.get('hint_text', '')
            level = prev_hint.get('level', '커스텀')
            timestamp = prev_hint.get('timestamp', '')
            hints_list.append(f"{i}. [{level}] {hint_text[:100]}...")
        previous_hints_str = f"""
# 이전 힌트 이력 (참고용)
학생이 이미 받은 힌트들입니다. 이를 바탕으로 더 발전된 힌트를 제공하세요:
{chr(10).join(hints_list)}

⚠️ 중요: 위 힌트들에서 언급한 내용은 반복하지 말고, 다음 단계나 새로운 관점의 힌트를 제공하세요.
"""

    # 지표 평균 컨텍스트 생성 (Chain of Hints)
    metrics_history_str = ""
    if avg_static and avg_llm:
        metrics_history_str = f"""
# 이전 지표 평균 (최근 5회)
학생의 이전 코드 평가 결과입니다. 현재 코드와 비교하여 개선/악화 여부를 파악하세요:

## 정적 지표 평균
- 문법 오류: {avg_static['syntax_errors']:.1f}개 (현재: {static_metrics['syntax_errors']}개)
- 테스트 통과율: {avg_static['test_pass_rate']:.1f}% (현재: {static_metrics['test_pass_rate']}%)
- 실행 시간: {avg_static.get('execution_time', 0):.1f}ms (현재: {static_metrics.get('execution_time', 0)}ms)
- 메모리 사용량: {avg_static.get('memory_usage', 0):.1f}KB (현재: {static_metrics.get('memory_usage', 0)}KB)
- 코드 품질: {avg_static['code_quality_score']:.1f}/100 (현재: {static_metrics['code_quality_score']})
- PEP8 위반: {avg_static['pep8_violations']:.1f}개 (현재: {static_metrics['pep8_violations']}개)

## LLM 지표 평균
- 알고리즘 효율성: {avg_llm['algorithm_efficiency']:.1f}/5 (현재: {llm_metrics['algorithm_efficiency']}/5)
- 코드 가독성: {avg_llm['code_readability']:.1f}/5 (현재: {llm_metrics['code_readability']}/5)
- 엣지 케이스 처리: {avg_llm['edge_case_handling']:.1f}/5 (현재: {llm_metrics['edge_case_handling']}/5)
- 코드 간결성: {avg_llm['code_conciseness']:.1f}/5 (현재: {llm_metrics['code_conciseness']}/5)
- 테스트 커버리지 추정: {avg_llm.get('test_coverage_estimate', 3):.1f}/5 (현재: {llm_metrics.get('test_coverage_estimate', 3)}/5)
- 보안 인식: {avg_llm.get('security_awareness', 3):.1f}/5 (현재: {llm_metrics.get('security_awareness', 3)}/5)

💡 개선된 지표는 칭찬하고, 악화된 지표는 구체적인 개선 방향을 제시하세요.
"""

    # 사용자 전체 역량 프로필 (마이페이지 방사형 그래프 데이터) - 힌트 생성 시 10% 반영
    user_profile_str = ""
    try:
        user_profile = get_user_metrics_summary(request.user)
        if user_profile.get('total_problems', 0) > 0:
            # 약한 지표 식별 (3점 미만)
            weak_areas = []
            if user_profile['avg_algorithm_efficiency'] < 3:
                weak_areas.append(f"알고리즘 효율성 ({user_profile['avg_algorithm_efficiency']:.1f}/5)")
            if user_profile['avg_code_readability'] < 3:
                weak_areas.append(f"코드 가독성 ({user_profile['avg_code_readability']:.1f}/5)")
            if user_profile['avg_edge_case_handling'] < 3:
                weak_areas.append(f"엣지 케이스 처리 ({user_profile['avg_edge_case_handling']:.1f}/5)")
            if user_profile['avg_code_conciseness'] < 3:
                weak_areas.append(f"코드 간결성 ({user_profile['avg_code_conciseness']:.1f}/5)")
            if user_profile['avg_code_quality_score'] < 50:
                weak_areas.append(f"코드 품질 ({user_profile['avg_code_quality_score']:.1f}/100)")
            if user_profile['avg_test_pass_rate'] < 80:
                weak_areas.append(f"테스트 통과율 ({user_profile['avg_test_pass_rate']:.1f}%)")

            weak_areas_str = "\n".join([f"  - {area}" for area in weak_areas]) if weak_areas else "  - 모든 영역이 양호합니다."

            user_profile_str = f"""
# 학생 역량 프로필 (평균 지표, 힌트 방향 결정에 10% 반영)
이 학생의 평소 코딩 역량입니다. 약한 부분은 더 쉽게 설명하고, 강한 부분은 간략히 다루세요:

## 정적 지표 평균 (6개)
- 문법 오류 평균: {user_profile['avg_syntax_errors']:.1f}개
- 테스트 통과율 평균: {user_profile['avg_test_pass_rate']:.1f}%
- 코드 복잡도 평균: {user_profile['avg_code_complexity']:.1f}
- 코드 품질 평균: {user_profile['avg_code_quality_score']:.1f}/100
- 알고리즘 패턴 일치도 평균: {user_profile['avg_algorithm_pattern_match']:.1f}%
- PEP8 위반 평균: {user_profile['avg_pep8_violations']:.1f}개

## LLM 지표 평균 (6개, 각 1-5점)
- 알고리즘 효율성 평균: {user_profile['avg_algorithm_efficiency']:.1f}/5
- 코드 가독성 평균: {user_profile['avg_code_readability']:.1f}/5
- 설계 패턴 적합도 평균: {user_profile['avg_design_pattern_fit']:.1f}/5
- 엣지 케이스 처리 평균: {user_profile['avg_edge_case_handling']:.1f}/5
- 코드 간결성 평균: {user_profile['avg_code_conciseness']:.1f}/5
- 함수 분리 평균: {user_profile['avg_function_separation']:.1f}/5

## 약한 영역 (더 자세한 설명 필요)
{weak_areas_str}

⚠️ 위 평균 지표에서 약한 부분은 힌트에서 더 자세히 설명해주세요.
"""
    except Exception as e:
        print(f'Failed to get user profile metrics: {str(e)}')
        user_profile_str = ""

    # 통합 프롬프트 생성 (6단계: LLM 힌트 생성)
    prompt = f"""당신은 Python 코딩 교육 전문가입니다.

# 문제 정보
{problem_description}

# 학생 코드
{user_code if user_code else '(아직 작성하지 않음)'}

{purpose_context}

# 현재 코드 분석 결과 (12개 지표)

## 정적 지표 (6개)
- 문법 오류: {static_metrics['syntax_errors']}개
- 테스트 통과율: {static_metrics['test_pass_rate']}%
- 실행 시간: {static_metrics.get('execution_time', 0)}ms
- 메모리 사용량: {static_metrics.get('memory_usage', 0)}KB
- 코드 품질 점수: {static_metrics['code_quality_score']}/100
- PEP8 위반: {static_metrics['pep8_violations']}개

## LLM 평가 지표 (6개, 각 1-5점)
- 알고리즘 효율성: {llm_metrics['algorithm_efficiency']}/5
- 코드 가독성: {llm_metrics['code_readability']}/5
- 엣지 케이스 처리: {llm_metrics['edge_case_handling']}/5
- 코드 간결성: {llm_metrics['code_conciseness']}/5
- 테스트 커버리지 추정: {llm_metrics.get('test_coverage_estimate', 3)}/5
- 보안 인식: {llm_metrics.get('security_awareness', 3)}/5
{metrics_history_str}{user_profile_str}{previous_hints_str}
# 요청 사항
위 힌트 목적과 12개 지표를 모두 반영하여 다음 항목만 포함한 힌트를 제공하세요:
{components_str}

⚠️ 중요:
- **힌트 목적에 따라 초점을 맞추세요** (완료: 동작하게 만들기 / 최적화: 효율적으로 만들기 / 최적: 다른 풀이 제안)
- 12개 지표를 모두 고려하여 종합적인 피드백을 제공하세요
- 이전 지표 평균이 있다면 개선/악화 여부를 명확히 언급하세요
- 가장 시급한 개선 사항을 우선적으로 다루세요
- **요약(summary) 마지막에 반드시 다음 안내를 포함하세요:**
{component_guidance_str}

# 응답 형식 (JSON)
{{
  "hint_content": {{
    "summary": "..." or null,
    "libraries": [...] or null,
    "code_example": "..." or null,
    "step_by_step": [...] or null,
    "complexity_hint": "..." or null,
    "edge_cases": [...] or null,
    "improvements": [...] or null
  }}
}}

위 구성만 포함하여 응답하세요. 선택되지 않은 항목은 null로 반환하세요.
"""

    # AI 설정에 따라 힌트 생성 방식 결정
    hint_response = ""

    if ai_config.mode == 'api':
        # API 방식: Hugging Face Inference API 사용
        api_key = ai_config.api_key if ai_config.api_key else os.environ.get('HUGGINGFACE_API_KEY', '')

        # 디버깅: API 키 상태 로깅
        print(f'[DEBUG] DB API Key exists: {bool(ai_config.api_key)}')
        print(f'[DEBUG] DB API Key length: {len(ai_config.api_key) if ai_config.api_key else 0}')
        print(f'[DEBUG] Final API Key exists: {bool(api_key)}')
        print(f'[DEBUG] Model: {ai_config.model_name}')

        if not api_key:
            # API 키가 없으면 간단한 fallback 힌트 제공
            if not user_code or len(user_code.strip()) < 10:
                hint_response = "먼저 문제를 단계별로 나누어 생각해보세요. 입력을 어떻게 처리하고, 어떤 연산을 해야 할까요?"
            else:
                hint_response = "작성하신 코드를 보니 좋은 시작입니다! 다음 단계로, 엣지 케이스(예: 빈 입력, 최소값/최대값)를 고려해보셨나요?"
        else:
            try:
                headers = {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': 'application/json'
                }
                # OpenAI 호환 Chat Completion 형식으로 변경 (2025년 7월부터 필수)
                payload = {
                    'model': ai_config.model_name,
                    'messages': [
                        {'role': 'system', 'content': '당신은 코딩 교육 전문가입니다. 12개 지표를 모두 반영하여 JSON 형식으로 힌트를 반환해야 합니다.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 1000,
                    'temperature': 0.3,
                    'top_p': 0.9
                }

                # Hugging Face Inference Providers (최신 API)
                response = requests.post(
                    'https://router.huggingface.co/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    # Chat Completion 응답 형식 처리
                    if 'choices' in result and len(result['choices']) > 0:
                        llm_response_text = result['choices'][0]['message']['content'].strip()

                        # JSON 파싱 시도
                        try:
                            llm_data = json.loads(llm_response_text)
                            hint_content = llm_data.get('hint_content', {})

                            # 코드 예시 처리 (리스트 → 문자열 변환 및 코드 블록 포맷팅)
                            if hint_content.get('code_example'):
                                code_example = hint_content['code_example']
                                # 리스트로 왔을 경우 문자열로 변환
                                if isinstance(code_example, list):
                                    code_example = '\n'.join(code_example)
                                # \\n을 실제 줄바꿈으로 변환
                                code_example = code_example.replace('\\n', '\n')
                                # 들여쓰기 보정
                                code_example = format_code_indentation(code_example)
                                hint_content['code_example'] = code_example

                            # 힌트 내용 구성 (LLM 지표는 이미 evaluate_code_with_llm에서 계산됨)
                            hint_parts = []
                            if hint_content.get('summary'):
                                hint_parts.append(f"💡 {hint_content['summary']}")
                            if hint_content.get('libraries'):
                                hint_parts.append(f"📚 사용 라이브러리: {', '.join(hint_content['libraries'])}")
                            if hint_content.get('code_example'):
                                hint_parts.append(f"📝 코드 예시:\n```python\n{hint_content['code_example']}\n```")
                            if hint_content.get('step_by_step'):
                                steps = '\n'.join(f"{i+1}. {step}" for i, step in enumerate(hint_content['step_by_step']))
                                hint_parts.append(f"📋 단계별 방법:\n{steps}")
                            if hint_content.get('complexity_hint'):
                                hint_parts.append(f"⏱️ 복잡도: {hint_content['complexity_hint']}")
                            if hint_content.get('edge_cases'):
                                cases = '\n'.join(f"- {case}" for case in hint_content['edge_cases'])
                                hint_parts.append(f"⚠️ 엣지 케이스:\n{cases}")
                            if hint_content.get('improvements'):
                                improvements = '\n'.join(f"- {imp}" for imp in hint_content['improvements'])
                                hint_parts.append(f"✨ 개선 사항:\n{improvements}")

                            hint_response = '\n\n'.join(hint_parts) if hint_parts else "힌트를 생성하는 중 오류가 발생했습니다."

                        except json.JSONDecodeError:
                            # JSON 파싱 실패 시 원문 반환
                            hint_response = llm_response_text
                    else:
                        hint_response = "힌트를 생성하는 중 오류가 발생했습니다. 문제를 다시 읽고 예제를 분석해보세요."
                else:
                    error_detail = response.text
                    print(f'Hugging Face API Error (Status {response.status_code}): {error_detail}')
                    hint_response = f"힌트 생성 실패 (상태 코드: {response.status_code}). 문제의 입출력 예시를 먼저 분석해보세요."
            except Exception as e:
                print(f'API Error: {str(e)}')
                hint_response = "힌트: 문제의 입력과 출력 형식을 먼저 파악하고, 단계별로 로직을 구성해보세요."

    elif ai_config.mode == 'local':
        # 로컬 모드: 모델이 로드되어 있는지 확인
        if not ai_config.is_model_loaded:
            hint_response = "모델이 로드되지 않았습니다. 관리자에게 문의하세요."
        else:
            hint_response = "[로컬 모델] 문제를 단계별로 나누어 생각해보세요."

    elif ai_config.mode == 'runpod':
        # Runpod vLLM 모드: OpenAI SDK를 사용하여 vLLM 서버에 요청
        try:
            from openai import OpenAI

            if not ai_config.runpod_endpoint:
                hint_response = "Runpod 엔드포인트가 설정되지 않았습니다. 관리자에게 문의하세요."
            else:
                # OpenAI 클라이언트 생성 (base_url을 Runpod 엔드포인트로 설정)
                client = OpenAI(
                    base_url=f"{ai_config.runpod_endpoint}/v1",
                    api_key=ai_config.runpod_api_key or "EMPTY"  # vLLM은 API 키 불필요할 수 있음
                )

                # Qwen 2.5 Coder에 최적화된 시스템 프롬프트
                system_prompt = """You are Qwen, created by Alibaba Cloud. You are a helpful coding assistant specialized in:
- Code analysis and debugging
- Algorithm explanation
- Best practices in Python
- Step-by-step problem solving guidance

당신은 코딩 교육 전문가입니다. 12개 지표를 모두 반영하여 JSON 형식으로 힌트를 반환해야 합니다."""

                # vLLM에 Chat Completion 요청
                response = client.chat.completions.create(
                    model=ai_config.model_name,
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': prompt}
                    ],
                    temperature=0.3,
                    top_p=0.9,
                    max_tokens=1000
                )

                # 응답 파싱
                llm_response_text = response.choices[0].message.content.strip()

                # JSON 파싱 시도
                try:
                    llm_data = json.loads(llm_response_text)
                    hint_response = llm_data.get('hint', llm_response_text)

                    # LLM 지표 업데이트
                    if 'metrics' in llm_data:
                        metrics_from_llm = llm_data['metrics']
                        llm_metrics['algorithm_efficiency'] = metrics_from_llm.get('algorithm_efficiency', 3)
                        llm_metrics['code_readability'] = metrics_from_llm.get('code_readability', 3)
                        llm_metrics['edge_case_handling'] = metrics_from_llm.get('edge_case_handling', 3)
                        llm_metrics['code_conciseness'] = metrics_from_llm.get('code_conciseness', 3)
                        llm_metrics['test_coverage_estimate'] = metrics_from_llm.get('test_coverage_estimate', 3)
                        llm_metrics['security_awareness'] = metrics_from_llm.get('security_awareness', 3)
                except json.JSONDecodeError:
                    # JSON 파싱 실패 시 원본 텍스트 사용
                    hint_response = llm_response_text

        except ImportError:
            hint_response = "OpenAI SDK가 설치되지 않았습니다. pip install openai를 실행하세요."
        except Exception as e:
            print(f'Runpod vLLM Error: {str(e)}')
            hint_response = f"Runpod 연결 오류: {str(e)}. 엔드포인트 URL과 네트워크 연결을 확인하세요."

    else:
        hint_response = "알 수 없는 AI 모드입니다."

    # Save hint request to database
    try:
        problem_obj, _ = Problem.objects.get_or_create(
            problem_id=problem_id,
            defaults={
                'title': problem_title,
                'description': problem_description,
                'level': problem.get('level', 1),
                'step_title': problem.get('step_title', ''),
                'input_description': problem.get('input_description', ''),
                'output_description': problem.get('output_description', ''),
                'tags': problem.get('tags', []),
                'examples': problem.get('examples', []),
                'solutions': problem.get('solutions', [])
            }
        )

        model_used = f"{ai_config.get_mode_display()}: {ai_config.model_name}"
        HintRequest.objects.create(
            user=request.user,
            problem=problem_obj,
            hint_level=preset or 'custom',
            user_code=user_code or '(empty)',
            hint_response=hint_response,
            model_used=model_used
        )

        # HintMetrics 저장 (정적 6개 + LLM 6개)
        try:
            # 기존 메트릭 가져오거나 새로 생성
            hint_metrics, created = HintMetrics.objects.get_or_create(
                user=request.user,
                problem=problem_obj,
                defaults={
                    # 정적 지표
                    'syntax_errors': static_metrics['syntax_errors'],
                    'test_pass_rate': static_metrics['test_pass_rate'],
                    'code_complexity': static_metrics['code_complexity'],
                    'code_quality_score': static_metrics['code_quality_score'],
                    'algorithm_pattern_match': static_metrics['algorithm_pattern_match'],
                    'pep8_violations': static_metrics['pep8_violations'],
                    # LLM 지표
                    'algorithm_efficiency': llm_metrics['algorithm_efficiency'],
                    'code_readability': llm_metrics['code_readability'],
                    'design_pattern_fit': llm_metrics['design_pattern_fit'],
                    'edge_case_handling': llm_metrics['edge_case_handling'],
                    'code_conciseness': llm_metrics['code_conciseness'],
                    'function_separation': llm_metrics['function_separation'],
                    # 메타
                    'hint_count': 1,
                    'hint_config': hint_config
                }
            )

            if not created:
                # 기존 메트릭 업데이트
                hint_metrics.syntax_errors = static_metrics['syntax_errors']
                hint_metrics.test_pass_rate = static_metrics['test_pass_rate']
                hint_metrics.code_complexity = static_metrics['code_complexity']
                hint_metrics.code_quality_score = static_metrics['code_quality_score']
                hint_metrics.algorithm_pattern_match = static_metrics['algorithm_pattern_match']
                hint_metrics.pep8_violations = static_metrics['pep8_violations']
                hint_metrics.algorithm_efficiency = llm_metrics['algorithm_efficiency']
                hint_metrics.code_readability = llm_metrics['code_readability']
                hint_metrics.design_pattern_fit = llm_metrics['design_pattern_fit']
                hint_metrics.edge_case_handling = llm_metrics['edge_case_handling']
                hint_metrics.code_conciseness = llm_metrics['code_conciseness']
                hint_metrics.function_separation = llm_metrics['function_separation']
                hint_metrics.hint_count += 1
                hint_metrics.hint_config = hint_config
                hint_metrics.save()

            print(f'[Metrics Saved] User: {request.user.username}, Problem: {problem_id}')
            print(f'  정적: syntax_errors={static_metrics["syntax_errors"]}, test_pass_rate={static_metrics["test_pass_rate"]}%, complexity={static_metrics["code_complexity"]}')
            print(f'  LLM: efficiency={llm_metrics["algorithm_efficiency"]}, readability={llm_metrics["code_readability"]}')

            # 배지 획득 조건 체크
            try:
                newly_awarded = check_and_award_badges(request.user)
                if newly_awarded:
                    print(f'[New Badges] User: {request.user.username} earned {len(newly_awarded)} new badge(s): {[b.name for b in newly_awarded]}')
            except Exception as badge_error:
                print(f'Failed to check badges: {str(badge_error)}')

        except Exception as metric_error:
            print(f'Failed to save metrics: {str(metric_error)}')

    except Exception as e:
        print(f'Failed to save hint request: {str(e)}')

    # 7단계: 응답 반환
    response_data = {
        'hint': hint_response,
        'problem_id': problem_id,
        'hint_purpose': hint_purpose,  # 'completion', 'optimization', 'optimal'
        'hint_branch': hint_branch,  # 'A', 'B', 'C', 'D', 'E1', 'E2', 'F'
        'current_star_count': current_star_count,  # 현재 별점 (0-3)
        'max_star': max_star,  # 최대 별점 (3)
        'is_logic_complete': is_logic_complete,  # 테스트 통과 여부
        'static_metrics': static_metrics,
        'llm_metrics': llm_metrics,
        'selected_components': selected_components,  # 선택한 구성 목록
        'unselected_components': unselected_components  # 미선택 구성 목록
    }

    # optimization인 경우 약한 메트릭 정보 포함
    if hint_purpose == 'optimization' and weak_metrics:
        response_data['weak_metrics'] = [
            {'metric': metric_name, 'score': score, 'description': desc}
            for metric_name, score, desc in weak_metrics
        ]

    return Response({
        'success': True,
        'data': response_data
    })
