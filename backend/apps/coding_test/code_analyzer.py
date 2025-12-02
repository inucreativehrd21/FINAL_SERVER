"""
코드 분석 유틸리티
정적 지표 6개 계산
"""
import ast
import json
import os
import tempfile
import time
import tracemalloc
from pathlib import Path
from radon.metrics import mi_visit
import pycodestyle


def load_problem_json():
    """문제 JSON 파일 로드"""
    json_path = Path(__file__).parent / 'data' / 'problems_final_output.json'
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def check_syntax_errors(code):
    """
    문법 오류 개수 계산
    Python AST를 사용하여 정확히 감지
    """
    if not code or not code.strip():
        return 0

    try:
        ast.parse(code)
        return 0
    except SyntaxError as e:
        # 단일 문법 오류만 감지 (여러 오류는 연쇄적으로 발생하므로)
        return 1


def measure_execution_time(user_code, execution_results):
    """
    코드 실행 시간 측정 (밀리초)

    Args:
        user_code: 사용자 코드
        execution_results: 테스트 케이스 실행 결과 리스트

    Returns:
        float: 평균 실행 시간 (ms)
    """
    if not user_code or not user_code.strip():
        return 0.0

    if not execution_results:
        return 0.0

    try:
        # execution_results에서 실행 시간 추출
        execution_times = []
        for result in execution_results:
            exec_time = result.get('execution_time', 0)
            if exec_time > 0:
                execution_times.append(exec_time * 1000)  # 초를 밀리초로 변환

        if not execution_times:
            return 0.0

        # 평균 실행 시간 계산
        avg_time = sum(execution_times) / len(execution_times)
        return round(avg_time, 2)
    except:
        return 0.0


def measure_memory_usage(user_code, execution_results):
    """
    메모리 사용량 측정 (KB)

    Args:
        user_code: 사용자 코드
        execution_results: 테스트 케이스 실행 결과 리스트

    Returns:
        float: 평균 메모리 사용량 (KB)
    """
    if not user_code or not user_code.strip():
        return 0.0

    if not execution_results:
        return 0.0

    try:
        # execution_results에서 메모리 사용량 추출
        memory_usages = []
        for result in execution_results:
            memory = result.get('memory_usage', 0)
            if memory > 0:
                memory_usages.append(memory / 1024)  # 바이트를 KB로 변환

        if not memory_usages:
            return 0.0

        # 평균 메모리 사용량 계산
        avg_memory = sum(memory_usages) / len(memory_usages)
        return round(avg_memory, 2)
    except:
        return 0.0


def calculate_quality_score(user_code):
    """
    코드 품질 점수 계산 (Maintainability Index)

    Args:
        user_code: 사용자 코드

    Returns:
        float: 0-100 사이의 품질 점수
    """
    if not user_code or not user_code.strip():
        return 0.0

    try:
        mi_results = mi_visit(user_code, multi=True)
        if not mi_results:
            return 50.0

        # MI 점수는 0-100 범위 (높을수록 좋음)
        return round(mi_results, 2)
    except:
        return 0.0




def count_pep8_violations(user_code):
    """
    PEP8 스타일 가이드 위반 개수 계산

    Args:
        user_code: 사용자 코드

    Returns:
        int: PEP8 위반 개수
    """
    if not user_code or not user_code.strip():
        return 0

    try:
        # 임시 파일 생성
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(user_code)
            tmp_file_path = tmp_file.name

        # pycodestyle 체커 생성
        style_guide = pycodestyle.StyleGuide(quiet=True)
        result = style_guide.check_files([tmp_file_path])

        # 임시 파일 삭제
        os.unlink(tmp_file_path)

        return result.total_errors
    except:
        return 0


def calculate_test_pass_rate(execution_results):
    """
    테스트 통과율 계산

    Args:
        execution_results: 테스트 케이스 실행 결과 리스트

    Returns:
        float: 0-100 사이의 테스트 통과율
    """
    if not execution_results:
        return 0.0

    passed_tests = sum(1 for result in execution_results if result.get('is_correct', False))
    total_tests = len(execution_results)

    return round((passed_tests / total_tests) * 100, 2)


def estimate_logic_errors(execution_results):
    """
    논리 오류 개수 추정 (실행 결과 기반)

    Args:
        execution_results: 테스트 케이스 실행 결과 리스트

    Returns:
        int: 추정되는 논리 오류 개수
    """
    if not execution_results:
        return 0

    failed_tests = sum(1 for result in execution_results if not result.get('is_correct', False))

    # 실패한 테스트 케이스를 기반으로 논리 오류 추정
    # 모든 테스트 실패 = 3개, 일부 실패 = 1-2개
    if failed_tests == 0:
        return 0
    elif failed_tests == len(execution_results):
        return 3
    else:
        return min(failed_tests, 2)


def analyze_code(user_code, problem_id, execution_results=None):
    """
    종합 코드 분석

    Args:
        user_code: 학생 코드
        problem_id: 문제 ID
        execution_results: 실행 결과 (옵션)

    Returns:
        dict: 6가지 정적 지표
            - syntax_errors: 문법 오류 개수
            - test_pass_rate: 테스트 통과율 (0-100%)
            - execution_time: 실행 시간 (ms)
            - memory_usage: 메모리 사용량 (KB)
            - code_quality_score: 코드 품질 점수 (0-100)
            - pep8_violations: PEP8 위반 개수
    """
    # 문제 JSON 로드 (필요한 경우)
    problems_data = load_problem_json()
    problem_data = next((p for p in problems_data if p['problem_id'] == str(problem_id)), None)

    if not problem_data:
        # 문제를 찾을 수 없으면 기본값 반환
        return {
            'syntax_errors': 0,
            'test_pass_rate': 0.0,
            'execution_time': 0.0,
            'memory_usage': 0.0,
            'code_quality_score': 0.0,
            'pep8_violations': 0
        }

    # 1. 문법 오류
    syntax_errors = check_syntax_errors(user_code)

    # 2. 테스트 통과율
    test_pass_rate = calculate_test_pass_rate(execution_results) if execution_results else 0.0

    # 3. 실행 시간 (ms)
    execution_time = measure_execution_time(user_code, execution_results) if execution_results else 0.0

    # 4. 메모리 사용량 (KB)
    memory_usage = measure_memory_usage(user_code, execution_results) if execution_results else 0.0

    # 5. 코드 품질 점수
    code_quality_score = calculate_quality_score(user_code)

    # 6. PEP8 위반 개수
    pep8_violations = count_pep8_violations(user_code)

    return {
        'syntax_errors': syntax_errors,
        'test_pass_rate': test_pass_rate,
        'execution_time': execution_time,
        'memory_usage': memory_usage,
        'code_quality_score': code_quality_score,
        'pep8_violations': pep8_violations
    }


def detect_complexity_patterns(user_code):
    """
    코드에서 복잡도와 관련된 패턴을 검사합니다.

    Returns:
        dict: 검사 결과
            - has_nested_loops: 중첩 반복문 여부
            - nested_loop_depth: 중첩 깊이 (최대)
            - has_recursive_calls: 재귀 호출 여부
            - complexity_hints: LLM에게 제공할 컨텍스트 리스트
    """
    import ast
    import re

    complexity_hints = []
    has_nested_loops = False
    nested_loop_depth = 0
    has_recursive_calls = False

    if not user_code or not user_code.strip():
        return {
            'has_nested_loops': False,
            'nested_loop_depth': 0,
            'has_recursive_calls': False,
            'complexity_hints': []
        }

    try:
        # AST 파싱
        tree = ast.parse(user_code)

        # 중첩 반복문 검사
        class LoopAnalyzer(ast.NodeVisitor):
            def __init__(self):
                self.max_depth = 0
                self.current_depth = 0

            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1

        loop_analyzer = LoopAnalyzer()
        loop_analyzer.visit(tree)
        nested_loop_depth = loop_analyzer.max_depth
        has_nested_loops = nested_loop_depth >= 2

        if nested_loop_depth >= 3:
            complexity_hints.append(f"중첩 반복문 {nested_loop_depth}중 발견 → O(n^{nested_loop_depth}) 의심")
        elif nested_loop_depth == 2:
            complexity_hints.append("중첩 반복문 2중 발견 → O(n²) 의심")

        # 재귀 호출 검사 (함수 내에서 자기 자신을 호출하는지)
        class RecursionAnalyzer(ast.NodeVisitor):
            def __init__(self):
                self.has_recursion = False
                self.function_names = set()
                self.current_function = None

            def visit_FunctionDef(self, node):
                self.function_names.add(node.name)
                prev_function = self.current_function
                self.current_function = node.name
                self.generic_visit(node)
                self.current_function = prev_function

            def visit_Call(self, node):
                if isinstance(node.func, ast.Name):
                    if self.current_function and node.func.id == self.current_function:
                        self.has_recursion = True
                self.generic_visit(node)

        recursion_analyzer = RecursionAnalyzer()
        recursion_analyzer.visit(tree)
        has_recursive_calls = recursion_analyzer.has_recursion

        if has_recursive_calls:
            complexity_hints.append("재귀 함수 사용 발견 → 깊이/분기에 따른 복잡도 분석 필요")

        # 특정 비효율적 패턴 검사 (정규식)
        # 1. 리스트 내포문 내 반복문
        if re.search(r'\[.*for.*for.*\]', user_code):
            complexity_hints.append("리스트 내포문 내 중첩 반복 발견")

        # 2. 반복문 내 리스트 확장 (append in loop)
        if re.search(r'for\s+.*:\s*\n.*\.append\(', user_code, re.MULTILINE):
            complexity_hints.append("반복문 내 append 사용 (리스트 내포문 고려 가능)")

    except SyntaxError:
        # 문법 오류가 있으면 패턴 검사 불가
        complexity_hints.append("문법 오류로 인해 복잡도 패턴 분석 불가")
    except Exception as e:
        # 기타 오류
        complexity_hints.append(f"패턴 분석 중 오류: {str(e)}")

    return {
        'has_nested_loops': has_nested_loops,
        'nested_loop_depth': nested_loop_depth,
        'has_recursive_calls': has_recursive_calls,
        'complexity_hints': complexity_hints
    }


def evaluate_code_with_llm(user_code, problem_description, static_metrics):
    """
    LLM을 사용하여 코드를 6가지 기준으로 평가 (1-5점)

    Args:
        user_code: 학생 코드
        problem_description: 문제 설명
        static_metrics: 정적 지표 dict

    Returns:
        dict: 6가지 LLM 평가 지표 (각 1-5점)
    """
    import requests
    import json
    import os
    from django.conf import settings

    # AI 설정 가져오기
    try:
        from .models import AIModelConfig
        ai_config = AIModelConfig.objects.first()
        if not ai_config or ai_config.mode != 'api':
            # API 모드가 아니면 기본값 반환
            return {
                'algorithm_efficiency': 3,
                'code_readability': 3,
                'edge_case_handling': 3,
                'code_conciseness': 3,
                'test_coverage_estimate': 3,
                'security_awareness': 3
            }

        api_key = ai_config.api_key if ai_config.api_key else os.environ.get('HUGGINGFACE_API_KEY', '')
        if not api_key:
            return {
                'algorithm_efficiency': 3,
                'code_readability': 3,
                'edge_case_handling': 3,
                'code_conciseness': 3,
                'test_coverage_estimate': 3,
                'security_awareness': 3
            }

        # 복잡도 패턴 검사
        complexity_patterns = detect_complexity_patterns(user_code)
        complexity_context = ""
        if complexity_patterns['complexity_hints']:
            complexity_context = "\n# 복잡도 패턴 분석\n"
            for hint in complexity_patterns['complexity_hints']:
                complexity_context += f"- {hint}\n"

        # LLM 평가 프롬프트
        prompt = f"""당신은 Python 코드 평가 전문가입니다.

# 문제 정보
{problem_description}

# 학생 코드
{user_code if user_code else '(작성 안 함)'}

# 정적 분석 결과
- 문법 오류: {static_metrics['syntax_errors']}개
- 테스트 통과율: {static_metrics['test_pass_rate']}%
- 실행 시간: {static_metrics['execution_time']}ms
- 메모리 사용량: {static_metrics['memory_usage']}KB
- 코드 품질: {static_metrics['code_quality_score']}/100
- PEP8 위반: {static_metrics['pep8_violations']}개
{complexity_context}
아래 6가지 기준으로 코드를 평가하세요 (각 1-5점):

1. algorithm_efficiency: 시간/공간 복잡도 최적화 수준
   - 위 복잡도 패턴 분석을 참고하세요
   - 중첩 반복문이 있다면 더 효율적인 알고리즘(해시맵, 정렬 등)이 가능한지 평가하세요
   - 재귀 함수가 있다면 메모이제이션이나 DP로 개선 가능한지 평가하세요
2. code_readability: 변수명, 주석, 구조의 명확성
3. edge_case_handling: 경계 조건과 예외 처리
4. code_conciseness: 중복 제거, DRY 원칙 준수
5. test_coverage_estimate: 테스트 케이스 커버리지 추정
6. security_awareness: 보안 취약점 인식 및 안전한 코딩

JSON 형식으로만 응답:
{{
  "algorithm_efficiency": 1-5,
  "code_readability": 1-5,
  "edge_case_handling": 1-5,
  "code_conciseness": 1-5,
  "test_coverage_estimate": 1-5,
  "security_awareness": 1-5
}}"""

        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        payload = {
            'model': ai_config.model_name,
            'messages': [
                {'role': 'system', 'content': '당신은 코드 평가 전문가입니다. JSON 형식으로만 응답하세요.'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 300,
            'temperature': 0.3,
            'top_p': 0.9
        }

        response = requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code == 200:
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                llm_response_text = result['choices'][0]['message']['content'].strip()
                try:
                    llm_data = json.loads(llm_response_text)
                    return {
                        'algorithm_efficiency': llm_data.get('algorithm_efficiency', 3),
                        'code_readability': llm_data.get('code_readability', 3),
                        'edge_case_handling': llm_data.get('edge_case_handling', 3),
                        'code_conciseness': llm_data.get('code_conciseness', 3),
                        'test_coverage_estimate': llm_data.get('test_coverage_estimate', 3),
                        'security_awareness': llm_data.get('security_awareness', 3)
                    }
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        print(f'LLM evaluation error: {str(e)}')

    # 기본값 반환
    return {
        'algorithm_efficiency': 3,
        'code_readability': 3,
        'edge_case_handling': 3,
        'code_conciseness': 3,
        'test_coverage_estimate': 3,
        'security_awareness': 3
    }
