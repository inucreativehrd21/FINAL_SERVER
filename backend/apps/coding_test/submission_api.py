"""
코드 제출 API
사용자가 작성한 코드를 숨겨진 테스트 케이스로 검증합니다.
"""
import json
import time
import tracemalloc
from pathlib import Path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .code_executor import CodeExecutor
from .code_analyzer import analyze_code, evaluate_code_with_llm
from .models import Problem, Submission, ProblemStatus
from django.utils import timezone


def load_problem_json():
    """문제 JSON 파일 로드"""
    json_path = Path(__file__).parent / 'data' / 'problems_final_output.json'
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


def calculate_total_score(static_metrics, llm_metrics):
    """
    종합 점수 계산 (0-100점)

    정적 지표 50% + LLM 지표 50%
    """
    # 정적 지표 점수화 (0-100)
    static_score = 0

    # 1. 문법 오류 (0개 = 20점, 1개 이상 = 0점)
    static_score += 20 if static_metrics['syntax_errors'] == 0 else 0

    # 2. 테스트 통과율 (0-25점)
    static_score += (static_metrics['test_pass_rate'] / 100) * 25

    # 3. 실행 시간 (100ms 이하 = 15점, 선형 감소)
    execution_time = static_metrics.get('execution_time', 0)
    if execution_time <= 100:
        static_score += 15
    elif execution_time <= 1000:
        static_score += 15 - ((execution_time - 100) / 900) * 15

    # 4. 메모리 사용량 (1000KB 이하 = 10점, 선형 감소)
    memory_usage = static_metrics.get('memory_usage', 0)
    if memory_usage <= 1000:
        static_score += 10
    elif memory_usage <= 10000:
        static_score += 10 - ((memory_usage - 1000) / 9000) * 10

    # 5. 코드 품질 (0-20점)
    static_score += (static_metrics['code_quality_score'] / 100) * 20

    # 6. PEP8 위반 (0개 = 10점, 선형 감소)
    pep8_violations = static_metrics['pep8_violations']
    if pep8_violations == 0:
        static_score += 10
    elif pep8_violations <= 10:
        static_score += 10 - pep8_violations

    # LLM 지표 점수화 (각 1-5점을 0-100점으로 변환)
    llm_score = sum(llm_metrics.values()) / 6  # 평균 (1-5)
    llm_score = ((llm_score - 1) / 4) * 100  # 0-100 변환

    # 최종 점수 (정적 50% + LLM 50%)
    total_score = (static_score * 0.5) + (llm_score * 0.5)

    return round(total_score, 2)


def calculate_star_count(all_passed, code_quality_score, static_metrics, llm_metrics):
    """
    12개 지표를 기반으로 별점 계산 (힌트 로직과 동일)

    Args:
        all_passed: 모든 테스트 통과 여부
        code_quality_score: 코드 품질 점수 (0-100)
        static_metrics: 정적 지표 6개
        llm_metrics: LLM 지표 6개

    Returns:
        int: 별점 (0-3)
    """
    # 테스트 미통과 시 0점
    if not all_passed:
        return 0

    # 테스트 통과 시 최소 1개
    # 코드 품질 70점 이상: 2개
    # 코드 품질 90점 이상: 3개
    if code_quality_score >= 90:
        return 3
    elif code_quality_score >= 70:
        return 2
    else:
        return 1


def determine_problem_status(all_passed, total_score):
    """
    문제 상태 결정

    Args:
        all_passed: 모든 테스트 통과 여부
        total_score: 종합 점수 (0-100)

    Returns:
        str: 'solved' (최적) or 'upgrade' (개선 가능)
    """
    if not all_passed:
        return None  # 아직 정답이 아님 (상태 저장 안함)

    # 모든 테스트 통과한 경우
    # 종합 점수 85점 이상 = "내가 푼 문제" (최적)
    # 종합 점수 85점 미만 = "업그레이드" (개선 가능)
    if total_score >= 85:
        return 'solved'
    else:
        return 'upgrade'


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_code(request):
    """
    코드 제출 API

    Request Body:
        - problem_id: 문제 ID
        - code: 제출할 코드

    Response:
        - success: 성공 여부
        - all_passed: 모든 테스트 통과 여부
        - test_results: 각 테스트 케이스별 pass/fail (입출력 값은 숨김)
        - passed_count: 통과한 테스트 개수
        - total_count: 전체 테스트 개수
        - metrics: 코드 분석 지표 (12개)
    """
    problem_id = request.data.get('problem_id')
    user_code = request.data.get('code', '')

    if not problem_id:
        return Response({
            'success': False,
            'error': '문제 ID가 필요합니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not user_code or not user_code.strip():
        return Response({
            'success': False,
            'error': '코드를 입력해주세요.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 문제 정보 로드
    problems = load_problem_json()
    problem = next((p for p in problems if p['problem_id'] == str(problem_id)), None)

    if not problem:
        return Response({
            'success': False,
            'error': f'문제 ID {problem_id}를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 숨겨진 테스트 케이스 로드 (problems_final_output.json에 포함된 데이터 사용)
    hidden_test_cases = problem.get('hidden_test_cases', [])

    if not hidden_test_cases:
        return Response({
            'success': False,
            'error': '이 문제에 대한 테스트 케이스가 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 코드 실행 및 테스트
    executor = CodeExecutor(timeout=5)
    test_results = []
    execution_results = []  # 메트릭 계산용
    passed_count = 0

    for idx, test_case in enumerate(hidden_test_cases):
        test_input = test_case.get('input', '')
        expected_output = test_case.get('output', '').strip()

        # 실행 시간 및 메모리 측정
        tracemalloc.start()
        start_time = time.time()

        try:
            result = executor.execute_python(user_code, test_input)
            execution_time = time.time() - start_time
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            actual_output = result.get('output', '').strip()
            is_correct = (actual_output == expected_output and result.get('success', False))

            if is_correct:
                passed_count += 1

            # 사용자에게 보여줄 결과 (입출력 값은 숨김)
            test_results.append({
                'test_number': idx + 1,
                'passed': is_correct,
                'description': test_case.get('description', f'테스트 {idx + 1}'),
                'error': result.get('error', '') if not is_correct else ''
            })

            # 메트릭 계산용 결과
            execution_results.append({
                'is_correct': is_correct,
                'execution_time': execution_time,
                'memory_usage': peak,
                'input': test_input,
                'expected_output': expected_output,
                'actual_output': actual_output,
                'error': result.get('error', '')
            })

        except Exception as e:
            tracemalloc.stop()
            test_results.append({
                'test_number': idx + 1,
                'passed': False,
                'description': test_case.get('description', f'테스트 {idx + 1}'),
                'error': f'실행 오류: {str(e)}'
            })

            execution_results.append({
                'is_correct': False,
                'execution_time': 0,
                'memory_usage': 0,
                'input': test_input,
                'expected_output': expected_output,
                'actual_output': '',
                'error': str(e)
            })

    all_passed = (passed_count == len(hidden_test_cases))

    # 코드 분석 (정적 지표 6개 + LLM 지표 6개)
    try:
        static_metrics = analyze_code(user_code, problem_id, execution_results)
    except Exception as e:
        print(f'Failed to analyze code: {str(e)}')
        static_metrics = {
            'syntax_errors': 0,
            'test_pass_rate': 0.0,
            'execution_time': 0.0,
            'memory_usage': 0.0,
            'code_quality_score': 0.0,
            'pep8_violations': 0
        }

    try:
        llm_metrics = evaluate_code_with_llm(
            user_code,
            problem.get('description', ''),
            static_metrics
        )
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

    # 종합 점수 계산 (맞춘 문제 수 / 총 문제 수 * 100, 반올림)
    total_count = len(hidden_test_cases)
    total_score = round((passed_count / total_count) * 100) if total_count > 0 else 0

    # 별점 계산 (12개 지표 기반 - 힌트 로직과 동일)
    code_quality = static_metrics.get('code_quality_score', 0)
    star_count = calculate_star_count(all_passed, code_quality, static_metrics, llm_metrics)

    # DB에 제출 기록 저장
    try:
        problem_obj, _ = Problem.objects.get_or_create(
            problem_id=problem_id,
            defaults={
                'title': problem.get('title', ''),
                'description': problem.get('description', ''),
                'level': problem.get('level', 1),
                'step_title': problem.get('step_title', ''),
                'input_description': problem.get('input_description', ''),
                'output_description': problem.get('output_description', ''),
                'tags': problem.get('tags', []),
                'examples': problem.get('examples', []),
                'solutions': problem.get('solutions', [])
            }
        )

        Submission.objects.create(
            user=request.user,
            problem=problem_obj,
            code=user_code,
            is_correct=all_passed,
            passed_tests=passed_count,
            total_tests=len(hidden_test_cases),
            # 정적 지표
            syntax_errors=static_metrics['syntax_errors'],
            test_pass_rate=static_metrics['test_pass_rate'],
            execution_time=static_metrics.get('execution_time', 0),
            memory_usage=static_metrics.get('memory_usage', 0),
            code_quality_score=static_metrics['code_quality_score'],
            pep8_violations=static_metrics['pep8_violations'],
            # LLM 지표
            algorithm_efficiency=llm_metrics['algorithm_efficiency'],
            code_readability=llm_metrics['code_readability'],
            edge_case_handling=llm_metrics['edge_case_handling'],
            code_conciseness=llm_metrics['code_conciseness'],
            test_coverage_estimate=llm_metrics.get('test_coverage_estimate', 3),
            security_awareness=llm_metrics.get('security_awareness', 3)
        )

        print(f'[Submission] User: {request.user.username}, Problem: {problem_id}, Passed: {passed_count}/{len(hidden_test_cases)}, Score: {total_score}, Stars: {star_count}')

        # 문제 상태 업데이트 (정답일 때만)
        new_status = determine_problem_status(all_passed, total_score)
        if new_status:
            problem_status, created = ProblemStatus.objects.get_or_create(
                user=request.user,
                problem=problem_obj,
                defaults={
                    'status': new_status,
                    'best_score': total_score,
                    'star_count': star_count,
                    'first_solved_at': timezone.now()
                }
            )

            if not created:
                # 기존 상태 업데이트
                old_status = problem_status.status

                # 점수 갱신 (더 높은 점수로만)
                if total_score > problem_status.best_score:
                    problem_status.best_score = total_score

                # 별점 갱신 (더 높은 별점으로만)
                if star_count > (problem_status.star_count or 0):
                    problem_status.star_count = star_count
                    print(f'[Star] {problem_id}: {problem_status.star_count - star_count if problem_status.star_count else 0} → {star_count}개')

                # 상태 전환 로직
                if old_status == 'upgrade':
                    # '업그레이드' 문제를 다시 풀기 시작 → '업그레이드(푸는 중)'으로 변경
                    # (단, 이번 제출이 'solved'면 바로 '내가 푼 문제'로)
                    if new_status == 'solved':
                        problem_status.status = 'solved'
                        print(f'[Status] {problem_id}: upgrade → solved (점수: {total_score})')
                    else:
                        # 아직 최적이 아니면 '업그레이드(푸는 중)'
                        problem_status.status = 'upgrading'
                        print(f'[Status] {problem_id}: upgrade → upgrading (다시 풀기 시작)')

                elif old_status == 'upgrading':
                    # '업그레이드(푸는 중)'에서 최적 달성 → '내가 푼 문제'
                    if new_status == 'solved':
                        problem_status.status = 'solved'
                        print(f'[Status] {problem_id}: upgrading → solved (점수: {total_score})')
                    # 아직 최적 아니면 'upgrading' 유지

                elif old_status == 'solved':
                    # 이미 '내가 푼 문제'면 유지
                    pass

                # 최초 정답 시간 기록 (없으면)
                if not problem_status.first_solved_at:
                    problem_status.first_solved_at = timezone.now()

                problem_status.save()
            else:
                print(f'[Status] {problem_id}: NEW → {new_status} (점수: {total_score})')

    except Exception as e:
        print(f'Failed to save submission: {str(e)}')

    # 현재 문제 상태 조회
    current_status = None
    try:
        problem_status = ProblemStatus.objects.filter(
            user=request.user,
            problem=problem_obj
        ).first()
        if problem_status:
            current_status = {
                'status': problem_status.status,
                'status_display': problem_status.get_status_display(),
                'best_score': problem_status.best_score,
                'star_count': problem_status.star_count or 0
            }
    except:
        pass

    return Response({
        'success': True,
        'all_passed': all_passed,
        'test_results': test_results,
        'passed_count': passed_count,
        'total_count': len(hidden_test_cases),
        'total_score': total_score,
        'star_count': star_count,
        'problem_status': current_status,
        'metrics': {
            'static': static_metrics,
            'llm': llm_metrics
        }
    })
