"""
문제 데이터 검증 API - problems_final_output.json 검증
"""
import json
from pathlib import Path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .code_executor import CodeExecutor


def load_problems_with_tests():
    """problems_final_output.json 로드"""
    json_path = Path(__file__).parent / 'data' / 'problems_final_output.json'
    try:
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        print(f"Failed to load problems_final_output.json: {str(e)}")
        return []


@api_view(['GET'])
@permission_classes([IsAdminUser])
def list_problems_for_validation(request):
    """검증 가능한 문제 목록 반환"""
    problems = load_problems_with_tests()

    # 문제 요약 정보만 반환
    problem_summaries = []
    for problem in problems:
        # solutions 배열에서 solution_code 확인
        solutions = problem.get('solutions', [])
        has_solution = bool(solutions and solutions[0].get('solution_code'))

        problem_summaries.append({
            'problem_id': problem.get('problem_id'),
            'title': problem.get('title'),
            'level': problem.get('level'),
            'has_solution': has_solution,
            'examples_count': len(problem.get('examples', [])),
            'hidden_tests_count': len(problem.get('hidden_test_cases', []))
        })

    return Response({
        'success': True,
        'data': problem_summaries
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def validate_problem_data(request):
    """특정 문제의 데이터 검증"""
    problem_id = request.data.get('problem_id')

    if not problem_id:
        return Response({
            'success': False,
            'error': 'problem_id가 필요합니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 문제 찾기
    problems = load_problems_with_tests()
    problem = next((p for p in problems if p['problem_id'] == str(problem_id)), None)

    if not problem:
        return Response({
            'success': False,
            'error': f'문제 ID {problem_id}를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # solutions 배열에서 모든 솔루션 검증
    solutions = problem.get('solutions', [])
    if not solutions:
        return Response({
            'success': False,
            'error': '이 문제에는 solution이 없습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 각 솔루션별로 테스트 수행
    solution_results = []
    executor = CodeExecutor()
    examples = problem.get('examples', [])
    hidden_tests = problem.get('hidden_test_cases', [])

    for sol_idx, solution in enumerate(solutions):
        solution_code = solution.get('solution_code', '')
        if not solution_code:
            continue

        # \n 이스케이프 문자를 실제 개행으로 변환
        solution_code = solution_code.replace('\\n', '\n')
        solution_name = solution.get('solution_name', f'풀이 {sol_idx + 1}')

        # examples 테스트
        example_results = []
        for idx, example in enumerate(examples):
            test_input = example.get('input', '')
            expected_output = example.get('output', '')

            try:
                result = executor.execute_python(solution_code, test_input)
                actual_output = result.get('output', '').strip()
                expected_output_stripped = expected_output.strip()
                is_correct = actual_output == expected_output_stripped

                example_results.append({
                    'label': f'예제 {idx + 1}',
                    'input': test_input,
                    'expected_output': expected_output,
                    'actual_output': actual_output,
                    'is_correct': is_correct,
                    'error': result.get('error'),
                    'execution_time': result.get('execution_time', 0),
                    'memory_usage': result.get('memory_usage', 0)
                })
            except Exception as e:
                example_results.append({
                    'label': f'예제 {idx + 1}',
                    'input': test_input,
                    'expected_output': expected_output,
                    'actual_output': '',
                    'is_correct': False,
                    'error': str(e),
                    'execution_time': 0,
                    'memory_usage': 0
                })

        # hidden_test_cases 테스트
        hidden_results = []
        for idx, test_case in enumerate(hidden_tests):
            test_input = test_case.get('input', '')
            expected_output = test_case.get('output', '')
            description = test_case.get('description', f'테스트 {idx + 1}')

            try:
                result = executor.execute_python(solution_code, test_input)
                actual_output = result.get('output', '').strip()
                expected_output_stripped = expected_output.strip()
                is_correct = actual_output == expected_output_stripped

                hidden_results.append({
                    'label': description,
                    'input': test_input,
                    'expected_output': expected_output,
                    'actual_output': actual_output,
                    'is_correct': is_correct,
                    'error': result.get('error'),
                    'execution_time': result.get('execution_time', 0),
                    'memory_usage': result.get('memory_usage', 0)
                })
            except Exception as e:
                hidden_results.append({
                    'label': description,
                    'input': test_input,
                    'expected_output': expected_output,
                    'actual_output': '',
                    'is_correct': False,
                    'error': str(e),
                    'execution_time': 0,
                    'memory_usage': 0
                })

        # 솔루션별 통계
        total_tests = len(example_results) + len(hidden_results)
        passed_tests = sum(1 for r in example_results + hidden_results if r['is_correct'])

        solution_results.append({
            'solution_name': solution_name,
            'solution_code': solution_code,
            'example_results': example_results,
            'hidden_results': hidden_results,
            'statistics': {
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'pass_rate': round((passed_tests / total_tests * 100) if total_tests > 0 else 0, 1)
            }
        })

    # 전체 통계
    all_total = sum(s['statistics']['total_tests'] for s in solution_results)
    all_passed = sum(s['statistics']['passed_tests'] for s in solution_results)

    return Response({
        'success': True,
        'data': {
            'problem_id': problem_id,
            'title': problem.get('title'),
            'solutions_count': len(solution_results),
            'solution_results': solution_results,
            'overall_statistics': {
                'total_tests': all_total,
                'passed_tests': all_passed,
                'failed_tests': all_total - all_passed,
                'pass_rate': round((all_passed / all_total * 100) if all_total > 0 else 0, 1)
            }
        }
    })
