"""
코딩 테스트 뷰 (임시 구현)
"""
import json
from pathlib import Path
from datetime import datetime
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.conf import settings
from .code_executor import CodeExecutor
from .models import TestCaseProposal, SolutionProposal, ProblemProposal, Problem, HintMetrics
from .code_analyzer import analyze_code
from .badge_logic import check_and_award_badges
from .serializers import (
    TestCaseProposalSerializer,
    TestCaseProposalCreateSerializer,
    SolutionProposalSerializer,
    SolutionProposalCreateSerializer,
    ProblemProposalSerializer,
    ProblemProposalCreateSerializer
)


class ProblemListView(generics.ListAPIView):
    """문제 목록"""
    permission_classes = []

    def get(self, request):
        try:
            problems = load_problems()
            return Response({
                'success': True,
                'data': problems
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': f'문제 목록 로드 실패: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProblemDetailView(generics.RetrieveAPIView):
    """문제 상세"""
    permission_classes = []

    def get(self, request, problem_id):
        problems = load_problems()
        problem = next((p for p in problems if str(p.get('problem_id')) == str(problem_id)), None)

        if not problem:
            return Response({
                'success': False,
                'message': '문제를 찾을 수 없습니다.'
            }, status=status.HTTP_404_NOT_FOUND)

        return Response(problem)


def load_problems():
    """problems.json 파일 로드"""
    problems_file = Path(__file__).parent / 'data' / 'problems_final_output.json'
    try:
        with open(problems_file, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    except Exception as e:
        return []


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def execute_code(request):
    """
    코드 실행 (다중 예제 입력 지원)
    """
    try:
        problem_id = request.data.get('problem_id')
        code = request.data.get('code')
        language = request.data.get('language', 'python')
        custom_inputs = request.data.get('custom_inputs', [])  # 사용자가 추가한 입력들

        # 입력 검증
        if not code:
            return Response({
                'success': False,
                'message': '코드가 비어있습니다.',
                'data': {'error': '코드를 입력해주세요.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        if language != 'python':
            return Response({
                'success': False,
                'message': '현재 Python만 지원합니다.',
                'data': {'error': '지원하지 않는 언어입니다.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # 예제 입력 수집
        examples_to_run = []

        # 1. 문제의 기본 예제들
        if problem_id:
            problems = load_problems()
            problem = next((p for p in problems if p.get('problem_id') == problem_id), None)
            if problem and problem.get('examples'):
                for idx, example in enumerate(problem['examples']):
                    examples_to_run.append({
                        'label': f'예제 {idx + 1}',
                        'input': example.get('input', ''),
                        'expected_output': example.get('output', '')
                    })

        # 2. 사용자가 추가한 커스텀 입력들
        for idx, custom_input in enumerate(custom_inputs):
            examples_to_run.append({
                'label': f'커스텀 입력 {idx + 1}',
                'input': custom_input,
                'expected_output': None  # 커스텀 입력은 예상 출력이 없음
            })

        # 예제가 하나도 없으면 빈 입력으로 실행
        if not examples_to_run:
            examples_to_run.append({
                'label': '기본 실행',
                'input': '',
                'expected_output': None
            })

        # 모든 예제에 대해 코드 실행
        executor = CodeExecutor()
        results = []

        for example in examples_to_run:
            result = executor.execute_python(code, input_data=example['input'])

            # 정답 여부 판단 (예상 출력이 있는 경우만)
            is_correct = None
            if example['expected_output'] is not None:
                actual_output = result.get('output', '').strip()
                expected_output = example['expected_output'].strip()

                # 숫자 비교: 소수점 처리
                try:
                    # 공백으로 분리하여 각 값 비교
                    actual_parts = actual_output.split()
                    expected_parts = expected_output.split()

                    if len(actual_parts) == len(expected_parts):
                        is_correct = True
                        for a, e in zip(actual_parts, expected_parts):
                            try:
                                # 숫자인 경우 부동소수점 비교 (오차 허용)
                                if '.' in a or '.' in e:
                                    if abs(float(a) - float(e)) > 1e-6:
                                        is_correct = False
                                        break
                                else:
                                    if int(a) != int(e):
                                        is_correct = False
                                        break
                            except (ValueError, TypeError):
                                # 숫자가 아니면 문자열 비교
                                if a != e:
                                    is_correct = False
                                    break
                    else:
                        is_correct = False
                except Exception:
                    # 파싱 실패 시 문자열 정확 비교
                    is_correct = actual_output == expected_output

            results.append({
                'label': example['label'],
                'input': example['input'],
                'output': result.get('output', ''),
                'error': result.get('error', ''),
                'success': result.get('success', False),
                'expected_output': example['expected_output'],
                'is_correct': is_correct
            })

        # 코드 분석 및 지표 저장 (문제 ID가 있고 problem_obj를 가져올 수 있는 경우)
        if problem_id:
            try:
                problem_obj = Problem.objects.filter(problem_id=problem_id).first()
                if problem_obj:
                    # 이전 힌트 요청 횟수 확인
                    previous_hints = HintMetrics.objects.filter(
                        user=request.user,
                        problem=problem_obj
                    ).order_by('-created_at')
                    hint_count = previous_hints.count()

                    # 코드 분석 (execution_results 전달)
                    metrics = analyze_code(code, problem_id, execution_results=results)

                    # HintMetrics 저장
                    HintMetrics.objects.create(
                        user=request.user,
                        problem=problem_obj,
                        code_similarity=metrics['code_similarity'],
                        syntax_errors=metrics['syntax_errors'],
                        logic_errors=metrics['logic_errors'],
                        concept_level=metrics['concept_level'],
                        hint_count=hint_count,
                        hint_level_used=0  # 실행 버튼은 힌트 아님
                    )

                    print(f'[Execute Metrics Saved] User: {request.user.username}, Problem: {problem_id}, Similarity: {metrics["code_similarity"]}%')

                    # 배지 획득 조건 체크
                    try:
                        newly_awarded = check_and_award_badges(request.user)
                        if newly_awarded:
                            print(f'[New Badges] User: {request.user.username} earned {len(newly_awarded)} new badge(s)')
                    except Exception as badge_error:
                        print(f'Failed to check badges: {str(badge_error)}')

            except Exception as metric_error:
                print(f'Failed to save execute metrics: {str(metric_error)}')

        return Response({
            'success': True,
            'message': f'{len(results)}개의 예제가 실행되었습니다.',
            'data': {
                'results': results,
                'total_count': len(results)
            }
        })

    except Exception as e:
        return Response({
            'success': False,
            'message': '서버 오류가 발생했습니다.',
            'data': {'error': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_code(request):
    """
    코드 제출 (테스트 케이스 실행 및 채점)
    """
    try:
        problem_id = request.data.get('problem_id')
        code = request.data.get('code')
        language = request.data.get('language', 'python')

        # 입력 검증
        if not problem_id or not code:
            return Response({
                'success': False,
                'message': '문제 ID와 코드가 필요합니다.',
                'data': {'error': '필수 정보가 누락되었습니다.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        if language != 'python':
            return Response({
                'success': False,
                'message': '현재 Python만 지원합니다.',
                'data': {'error': '지원하지 않는 언어입니다.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # 문제 데이터 로드
        problems = load_problems()
        problem = next((p for p in problems if p.get('problem_id') == problem_id), None)

        if not problem:
            return Response({
                'success': False,
                'message': '문제를 찾을 수 없습니다.',
                'data': {'error': f'문제 ID {problem_id}를 찾을 수 없습니다.'}
            }, status=status.HTTP_404_NOT_FOUND)

        # 테스트 케이스 가져오기
        test_cases = problem.get('test_cases', [])
        if not test_cases:
            return Response({
                'success': False,
                'message': '테스트 케이스가 없습니다.',
                'data': {'error': '이 문제에는 테스트 케이스가 설정되어 있지 않습니다.'}
            }, status=status.HTTP_400_BAD_REQUEST)

        # 코드 실행 및 채점
        executor = CodeExecutor()
        result = executor.run_test_cases(code, test_cases)

        # 코드 분석 및 지표 저장 (정적 6개 + LLM 6개)
        try:
            problem_obj = Problem.objects.filter(problem_id=problem_id).first()
            if problem_obj:
                # 정적 지표 6개 분석
                from .code_analyzer import analyze_code, evaluate_code_with_llm
                static_metrics = analyze_code(code, problem_id, execution_results=result['results'])

                # LLM 지표 6개 평가
                problem_description = problem.get('description', '')
                llm_metrics = evaluate_code_with_llm(code, problem_description, static_metrics)

                # HintMetrics 생성 또는 업데이트
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
                        'hint_count': 0,
                        'hint_config': {'source': 'submit'}
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
                    hint_metrics.save()

                print(f'[Submit Metrics Saved] User: {request.user.username}, Problem: {problem_id}, Passed: {result["success"]}')
                print(f'  정적: syntax_errors={static_metrics["syntax_errors"]}, test_pass={static_metrics["test_pass_rate"]}%')
                print(f'  LLM: efficiency={llm_metrics["algorithm_efficiency"]}, readability={llm_metrics["code_readability"]}')

                # 배지 획득 조건 체크
                try:
                    newly_awarded = check_and_award_badges(request.user)
                    if newly_awarded:
                        print(f'[New Badges] User: {request.user.username} earned {len(newly_awarded)} new badge(s)')
                except Exception as badge_error:
                    print(f'Failed to check badges: {str(badge_error)}')

                # 별점 계산 및 ProblemStatus 업데이트
                # 1별: 테스트 100% 통과 (제출 성공)
                # 2별: 테스트 통과 + 품질 70점 이상
                # 3별: 테스트 통과 + 품질 90점 이상
                try:
                    from .models import ProblemStatus
                    from django.utils import timezone

                    # 테스트 통과 여부
                    test_passed = result['success']  # 모든 테스트 통과
                    quality_score = static_metrics.get('code_quality_score', 0)

                    # 별점 계산
                    if test_passed:
                        if quality_score >= 90:
                            new_star_count = 3
                        elif quality_score >= 70:
                            new_star_count = 2
                        else:
                            new_star_count = 1
                    else:
                        new_star_count = 0  # 테스트 통과 실패

                    # ProblemStatus 업데이트
                    problem_status, ps_created = ProblemStatus.objects.get_or_create(
                        user=request.user,
                        problem=problem_obj,
                        defaults={
                            'status': 'solved' if test_passed else 'upgrade',
                            'best_score': quality_score,
                            'star_count': new_star_count,
                            'first_solved_at': timezone.now() if test_passed else None
                        }
                    )

                    if not ps_created:
                        # 기존 ProblemStatus 업데이트 (더 높은 별점만 저장)
                        if new_star_count > problem_status.star_count:
                            problem_status.star_count = new_star_count
                        if quality_score > problem_status.best_score:
                            problem_status.best_score = quality_score
                        if test_passed and problem_status.status != 'solved':
                            problem_status.status = 'solved'
                            if not problem_status.first_solved_at:
                                problem_status.first_solved_at = timezone.now()
                        problem_status.save()

                    print(f'[Star Count] User: {request.user.username}, Problem: {problem_id}, Stars: {new_star_count}, Quality: {quality_score}')

                except Exception as status_error:
                    print(f'Failed to update problem status: {str(status_error)}')

        except Exception as metric_error:
            print(f'Failed to save submit metrics: {str(metric_error)}')

        # 응답에 별점 정보 포함
        star_count = 0
        if result['success']:
            quality = static_metrics.get('code_quality_score', 0) if 'static_metrics' in dir() else 0
            if quality >= 90:
                star_count = 3
            elif quality >= 70:
                star_count = 2
            else:
                star_count = 1

        return Response({
            'success': True,
            'message': '제출이 완료되었습니다.',
            'data': {
                'passed': result['success'],
                'passed_tests': result['passed'],
                'total_tests': result['total'],
                'results': result['results'],
                'error': result['error'],
                'star_count': star_count,
                'quality_score': static_metrics.get('code_quality_score', 0) if 'static_metrics' in dir() else 0
            }
        })

    except Exception as e:
        return Response({
            'success': False,
            'message': '서버 오류가 발생했습니다.',
            'data': {'error': str(e)}
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def get_hint(request):
    """힌트 요청"""
    return Response({"message": "Hint generation - To be implemented"})


class SubmissionListView(generics.ListAPIView):
    """제출 기록 목록"""
    permission_classes = []

    def get(self, request):
        return Response({"message": "Submission list - To be implemented"})


class SubmissionDetailView(generics.RetrieveAPIView):
    """제출 기록 상세"""
    permission_classes = []

    def get(self, request, pk):
        return Response({"message": f"Submission {pk} detail - To be implemented"})


class BookmarkListView(generics.ListAPIView):
    """문제 북마크 목록"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .models import Bookmark

        bookmarks = Bookmark.objects.filter(
            user=request.user
        ).select_related('problem').order_by('-created_at')

        data = [
            {
                'id': bm.id,
                'problem_id': bm.problem.problem_id,
                'problem_title': bm.problem.title,
                'problem_level': bm.problem.level,
                'problem_tags': bm.problem.tags,
                'created_at': bm.created_at.isoformat()
            }
            for bm in bookmarks
        ]

        return Response({
            'success': True,
            'data': data
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_bookmark(request):
    """문제 북마크 토글 (추가/삭제)"""
    from .models import Bookmark, Problem

    problem_id = request.data.get('problem_id')

    if not problem_id:
        return Response({
            'success': False,
            'message': '문제 ID가 필요합니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 문제 확인
    try:
        problem = Problem.objects.get(problem_id=problem_id)
    except Problem.DoesNotExist:
        return Response({
            'success': False,
            'message': '문제를 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    # 북마크 토글
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user,
        problem=problem
    )

    if not created:
        # 이미 존재하면 삭제
        bookmark.delete()
        return Response({
            'success': True,
            'data': {
                'bookmarked': False,
                'problem_id': problem_id
            },
            'message': '북마크가 해제되었습니다.'
        })

    # 새로 생성됨
    return Response({
        'success': True,
        'data': {
            'bookmarked': True,
            'problem_id': problem_id
        },
        'message': '북마크에 추가되었습니다.'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_bookmark_status(request):
    """사용자의 전체 문제 북마크 상태 조회"""
    from .models import Bookmark

    bookmarks = Bookmark.objects.filter(
        user=request.user
    ).values_list('problem__problem_id', flat=True)

    return Response({
        'success': True,
        'data': list(bookmarks)
    })


# ==================== TestCase Proposal APIs ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def propose_test_case(request):
    """테스트 케이스 제안"""
    serializer = TestCaseProposalCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(proposed_by=request.user)
        return Response({
            'success': True,
            'message': '테스트 케이스가 제안되었습니다. 관리자의 승인을 기다려주세요.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response({
        'success': False,
        'message': '입력 데이터가 유효하지 않습니다.',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_test_case_proposals(request):
    """테스트 케이스 제안 목록 조회"""
    problem_id = request.query_params.get('problem_id')
    proposal_status = request.query_params.get('status', 'all')  # all, pending, approved, rejected

    queryset = TestCaseProposal.objects.all()

    # 문제 ID 필터
    if problem_id:
        queryset = queryset.filter(problem_id=problem_id)

    # 상태 필터
    if proposal_status != 'all':
        queryset = queryset.filter(status=proposal_status)

    # 일반 사용자는 자신이 제안한 것만 조회
    if not (request.user.is_staff or request.user.is_superuser):
        queryset = queryset.filter(proposed_by=request.user)

    serializer = TestCaseProposalSerializer(queryset, many=True)
    return Response({
        'success': True,
        'data': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_approved_test_cases(request, problem_id):
    """승인된 테스트 케이스만 조회 (제출 버튼용)"""
    proposals = TestCaseProposal.objects.filter(
        problem_id=problem_id,
        status='approved'
    ).order_by('created_at')

    # 테스트 케이스 형식으로 변환
    test_cases = [
        {
            'input': proposal.input_data,
            'output': proposal.expected_output
        }
        for proposal in proposals
    ]

    return Response({
        'success': True,
        'data': {
            'problem_id': problem_id,
            'test_cases': test_cases,
            'count': len(test_cases)
        }
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_test_case(request, proposal_id):
    """테스트 케이스 승인 (관리자만)"""
    try:
        proposal = TestCaseProposal.objects.get(id=proposal_id)
    except TestCaseProposal.DoesNotExist:
        return Response({
            'success': False,
            'message': '제안을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    if proposal.status != 'pending':
        return Response({
            'success': False,
            'message': f'이미 {proposal.get_status_display()} 상태입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    review_comment = request.data.get('review_comment', '')

    proposal.status = 'approved'
    proposal.reviewed_by = request.user
    proposal.reviewed_at = datetime.now()
    proposal.review_comment = review_comment
    proposal.save()

    serializer = TestCaseProposalSerializer(proposal)
    return Response({
        'success': True,
        'message': '테스트 케이스가 승인되었습니다.',
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_test_case(request, proposal_id):
    """테스트 케이스 거부 (관리자만)"""
    try:
        proposal = TestCaseProposal.objects.get(id=proposal_id)
    except TestCaseProposal.DoesNotExist:
        return Response({
            'success': False,
            'message': '제안을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    if proposal.status != 'pending':
        return Response({
            'success': False,
            'message': f'이미 {proposal.get_status_display()} 상태입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    review_comment = request.data.get('review_comment', '거부됨')

    proposal.status = 'rejected'
    proposal.reviewed_by = request.user
    proposal.reviewed_at = datetime.now()
    proposal.review_comment = review_comment
    proposal.save()

    serializer = TestCaseProposalSerializer(proposal)
    return Response({
        'success': True,
        'message': '테스트 케이스가 거부되었습니다.',
        'data': serializer.data
    })


# ==================== Solution Proposal APIs ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def propose_solution(request):
    """솔루션 제안 (모든 인증된 사용자)"""
    serializer = SolutionProposalCreateSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(proposed_by=request.user)
        return Response({
            'success': True,
            'message': '솔루션이 제안되었습니다.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_solution_proposals(request):
    """솔루션 제안 목록 조회
    - 관리자: 모든 제안 조회
    - 일반 사용자: 자신이 제안한 것만 조회
    """
    queryset = SolutionProposal.objects.all().order_by('-created_at')

    # 일반 사용자는 자신이 제안한 것만 조회
    if not (request.user.is_staff or request.user.is_superuser):
        queryset = queryset.filter(proposed_by=request.user)

    serializer = SolutionProposalSerializer(queryset, many=True)
    return Response({
        'success': True,
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_solution(request, proposal_id):
    """솔루션 승인 (관리자만)"""
    try:
        proposal = SolutionProposal.objects.get(id=proposal_id)
    except SolutionProposal.DoesNotExist:
        return Response({
            'success': False,
            'message': '제안을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    if proposal.status != 'pending':
        return Response({
            'success': False,
            'message': f'이미 {proposal.get_status_display()} 상태입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    review_comment = request.data.get('review_comment', '')

    proposal.status = 'approved'
    proposal.reviewed_by = request.user
    proposal.reviewed_at = datetime.now()
    proposal.review_comment = review_comment
    proposal.save()

    serializer = SolutionProposalSerializer(proposal)
    return Response({
        'success': True,
        'message': '솔루션이 승인되었습니다.',
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_solution(request, proposal_id):
    """솔루션 거부 (관리자만)"""
    try:
        proposal = SolutionProposal.objects.get(id=proposal_id)
    except SolutionProposal.DoesNotExist:
        return Response({
            'success': False,
            'message': '제안을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    if proposal.status != 'pending':
        return Response({
            'success': False,
            'message': f'이미 {proposal.get_status_display()} 상태입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    review_comment = request.data.get('review_comment', '거부됨')

    proposal.status = 'rejected'
    proposal.reviewed_by = request.user
    proposal.reviewed_at = datetime.now()
    proposal.review_comment = review_comment
    proposal.save()

    serializer = SolutionProposalSerializer(proposal)
    return Response({
        'success': True,
        'message': '솔루션이 거부되었습니다.',
        'data': serializer.data
    })


# ==================== 문제 제안 APIs ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def propose_problem(request):
    """문제 제안 (모든 인증된 사용자)"""
    serializer = ProblemProposalCreateSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save(proposed_by=request.user)
        return Response({
            'success': True,
            'message': '문제가 제안되었습니다. 관리자의 승인을 기다려주세요.',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'success': False,
        'message': '입력 데이터가 유효하지 않습니다.',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_problem_proposals(request):
    """문제 제안 목록 조회
    - 관리자: 모든 제안 조회
    - 일반 사용자: 자신이 제안한 것만 조회
    """
    proposal_status = request.query_params.get('status', 'all')  # all, pending, approved, rejected

    if request.user.is_staff:
        queryset = ProblemProposal.objects.all()
    else:
        queryset = ProblemProposal.objects.filter(proposed_by=request.user)

    # 상태 필터
    if proposal_status != 'all':
        queryset = queryset.filter(status=proposal_status)

    queryset = queryset.order_by('-created_at')
    serializer = ProblemProposalSerializer(queryset, many=True)

    return Response({
        'success': True,
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def approve_problem(request, proposal_id):
    """문제 승인 (관리자만)"""
    try:
        proposal = ProblemProposal.objects.get(id=proposal_id)
    except ProblemProposal.DoesNotExist:
        return Response({
            'success': False,
            'message': '제안을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    if proposal.status != 'pending':
        return Response({
            'success': False,
            'message': f'이미 {proposal.get_status_display()} 상태입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    review_comment = request.data.get('review_comment', '')

    proposal.status = 'approved'
    proposal.reviewed_by = request.user
    proposal.reviewed_at = datetime.now()
    proposal.review_comment = review_comment
    proposal.save()

    serializer = ProblemProposalSerializer(proposal)
    return Response({
        'success': True,
        'message': '문제가 승인되었습니다.',
        'data': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def reject_problem(request, proposal_id):
    """문제 거부 (관리자만)"""
    try:
        proposal = ProblemProposal.objects.get(id=proposal_id)
    except ProblemProposal.DoesNotExist:
        return Response({
            'success': False,
            'message': '제안을 찾을 수 없습니다.'
        }, status=status.HTTP_404_NOT_FOUND)

    if proposal.status != 'pending':
        return Response({
            'success': False,
            'message': f'이미 {proposal.get_status_display()} 상태입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    review_comment = request.data.get('review_comment', '거부됨')

    proposal.status = 'rejected'
    proposal.reviewed_by = request.user
    proposal.reviewed_at = datetime.now()
    proposal.review_comment = review_comment
    proposal.save()

    serializer = ProblemProposalSerializer(proposal)
    return Response({
        'success': True,
        'message': '문제가 거부되었습니다.',
        'data': serializer.data
    })


# ==================== ProblemStatus APIs ====================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_problem_statuses(request):
    """
    사용자의 문제 상태 조회

    Response:
        {
            "success": true,
            "data": [
                {
                    "problem_id": "1000",
                    "status": "solved",  # 'solved', 'upgrade', 'upgrading'
                    "status_display": "내가 푼 문제",
                    "best_score": 92.5,
                    "first_solved_at": "2025-01-15T10:30:00Z"
                },
                ...
            ]
        }
    """
    from .models import ProblemStatus

    problem_statuses = ProblemStatus.objects.filter(
        user=request.user
    ).select_related('problem').order_by('-first_solved_at')

    data = [
        {
            'problem_id': ps.problem.problem_id,
            'status': ps.status,
            'status_display': ps.get_status_display(),
            'best_score': ps.best_score,
            'star_count': ps.star_count,  # 별점 (0-3)
            'first_solved_at': ps.first_solved_at
        }
        for ps in problem_statuses
    ]

    return Response({
        'success': True,
        'data': data
    })
