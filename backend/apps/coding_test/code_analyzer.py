"""
코드 분석 유틸리티
정적 지표 6개 계산
"""
import ast
import json
import os
import tempfile
from pathlib import Path
from radon.complexity import cc_visit
from radon.metrics import mi_visit
import pycodestyle


def load_problem_json():
    """문제 JSON 파일 로드"""
    json_path = Path(__file__).parent / 'data' / 'problems_final_cleaned.json'
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


def calculate_complexity(user_code):
    """
    코드 복잡도 계산 (Cyclomatic Complexity)

    Args:
        user_code: 사용자 코드

    Returns:
        int: 평균 복잡도 (1-50+)
    """
    if not user_code or not user_code.strip():
        return 0

    try:
        complexity_results = cc_visit(user_code)
        if not complexity_results:
            return 1

        # 모든 함수/메서드의 평균 복잡도 계산
        total_complexity = sum(result.complexity for result in complexity_results)
        avg_complexity = total_complexity / len(complexity_results)
        return round(avg_complexity, 1)
    except:
        return 0


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


def calculate_algorithm_pattern_match(user_code, logic_steps):
    """
    알고리즘 패턴 일치도 계산

    Args:
        user_code: 사용자 코드
        logic_steps: 문제의 logic_steps 리스트

    Returns:
        float: 0-100 사이의 패턴 일치도
    """
    if not user_code or not user_code.strip():
        return 0.0

    if not logic_steps:
        # logic_steps가 없으면 기본 패턴 체크
        has_input = 'input(' in user_code
        has_output = 'print(' in user_code
        return 50.0 if (has_input and has_output) else 25.0

    # 알고리즘 패턴 키워드 체크
    pattern_keywords = {
        'loop': ['for ', 'while '],
        'condition': ['if ', 'elif ', 'else:'],
        'data_structure': ['list', 'dict', 'set', 'tuple'],
        'string_manipulation': ['.split(', '.join(', '.strip(', '.replace('],
        'math_operations': ['sum(', 'max(', 'min(', 'abs(', '**'],
        'comprehension': ['[' and 'for' and 'in', '{' and 'for' and 'in']
    }

    matched_patterns = 0
    total_patterns = 0

    for step in logic_steps:
        code_pattern = step.get('code_pattern', '').lower()

        for pattern_type, keywords in pattern_keywords.items():
            if any(kw in code_pattern for kw in keywords):
                total_patterns += 1
                if any(kw in user_code.lower() for kw in keywords):
                    matched_patterns += 1
                break

    if total_patterns == 0:
        return 50.0

    return round((matched_patterns / total_patterns) * 100, 2)


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
            - code_complexity: 코드 복잡도 (1-50+)
            - code_quality_score: 코드 품질 점수 (0-100)
            - algorithm_pattern_match: 알고리즘 패턴 일치도 (0-100%)
            - pep8_violations: PEP8 위반 개수
    """
    # 문제 JSON 로드
    problems_data = load_problem_json()
    problem_data = next((p for p in problems_data if p['problem_id'] == str(problem_id)), None)

    if not problem_data:
        # 문제를 찾을 수 없으면 기본값 반환
        return {
            'syntax_errors': 0,
            'test_pass_rate': 0.0,
            'code_complexity': 0,
            'code_quality_score': 0.0,
            'algorithm_pattern_match': 0.0,
            'pep8_violations': 0
        }

    # 첫 번째 솔루션의 logic_steps 사용
    logic_steps = []
    if problem_data.get('solutions') and len(problem_data['solutions']) > 0:
        logic_steps = problem_data['solutions'][0].get('logic_steps', [])

    # 1. 문법 오류
    syntax_errors = check_syntax_errors(user_code)

    # 2. 테스트 통과율
    test_pass_rate = calculate_test_pass_rate(execution_results) if execution_results else 0.0

    # 3. 코드 복잡도
    code_complexity = calculate_complexity(user_code)

    # 4. 코드 품질 점수
    code_quality_score = calculate_quality_score(user_code)

    # 5. 알고리즘 패턴 일치도
    algorithm_pattern_match = calculate_algorithm_pattern_match(user_code, logic_steps)

    # 6. PEP8 위반 개수
    pep8_violations = count_pep8_violations(user_code)

    return {
        'syntax_errors': syntax_errors,
        'test_pass_rate': test_pass_rate,
        'code_complexity': code_complexity,
        'code_quality_score': code_quality_score,
        'algorithm_pattern_match': algorithm_pattern_match,
        'pep8_violations': pep8_violations
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
                'design_pattern_fit': 3,
                'edge_case_handling': 3,
                'code_conciseness': 3,
                'function_separation': 3
            }

        api_key = ai_config.api_key if ai_config.api_key else os.environ.get('HUGGINGFACE_API_KEY', '')
        if not api_key:
            return {
                'algorithm_efficiency': 3,
                'code_readability': 3,
                'design_pattern_fit': 3,
                'edge_case_handling': 3,
                'code_conciseness': 3,
                'function_separation': 3
            }

        # LLM 평가 프롬프트
        prompt = f"""당신은 Python 코드 평가 전문가입니다.

# 문제 정보
{problem_description}

# 학생 코드
{user_code if user_code else '(작성 안 함)'}

# 정적 분석 결과
- 문법 오류: {static_metrics['syntax_errors']}개
- 테스트 통과율: {static_metrics['test_pass_rate']}%
- 코드 복잡도: {static_metrics['code_complexity']}
- 코드 품질: {static_metrics['code_quality_score']}/100
- 알고리즘 패턴 일치도: {static_metrics['algorithm_pattern_match']}%
- PEP8 위반: {static_metrics['pep8_violations']}개

아래 6가지 기준으로 코드를 평가하세요 (각 1-5점):

1. algorithm_efficiency: 시간/공간 복잡도 최적화
2. code_readability: 변수명, 주석, 구조의 명확성
3. design_pattern_fit: 적절한 알고리즘 패턴과 자료구조 선택
4. edge_case_handling: 경계 조건과 예외 처리
5. code_conciseness: 중복 제거, DRY 원칙 준수
6. function_separation: 모듈화, 단일 책임 원칙

JSON 형식으로만 응답:
{{
  "algorithm_efficiency": 1-5,
  "code_readability": 1-5,
  "design_pattern_fit": 1-5,
  "edge_case_handling": 1-5,
  "code_conciseness": 1-5,
  "function_separation": 1-5
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
                        'design_pattern_fit': llm_data.get('design_pattern_fit', 3),
                        'edge_case_handling': llm_data.get('edge_case_handling', 3),
                        'code_conciseness': llm_data.get('code_conciseness', 3),
                        'function_separation': llm_data.get('function_separation', 3)
                    }
                except json.JSONDecodeError:
                    pass

    except Exception as e:
        print(f'LLM evaluation error: {str(e)}')

    # 기본값 반환
    return {
        'algorithm_efficiency': 3,
        'code_readability': 3,
        'design_pattern_fit': 3,
        'edge_case_handling': 3,
        'code_conciseness': 3,
        'function_separation': 3
    }
