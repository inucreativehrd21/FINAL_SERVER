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
from .badge_logic import check_and_award_badges


def load_problem_json():
    """문제 JSON 파일 로드"""
    json_path = Path(__file__).parent / 'data' / 'problems_final_cleaned.json'
    with open(json_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_hint(request):
    """힌트 요청 API - 커스텀 구성 지원 (정적 6개 + LLM 6개 지표) + Chain of Hints"""
    problem_id = request.data.get('problem_id')
    user_code = request.data.get('user_code', '')
    previous_hints = request.data.get('previous_hints', [])  # Chain of Hints

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

    # 힌트 구성 가져오기 (커스텀 또는 프리셋)
    hint_config = request.data.get('hint_config', {})
    preset = hint_config.get('preset')  # '초급', '중급', '고급', None
    components = hint_config.get('components', {})

    # 프리셋이 지정된 경우 기본 구성 설정
    if preset == '초급':
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

    # 코드 분석 (정적 지표 계산)
    try:
        static_metrics = analyze_code(user_code, problem_id, execution_results=None)
    except Exception as e:
        print(f'Failed to analyze code: {str(e)}')
        static_metrics = {
            'syntax_errors': 0, 'test_pass_rate': 0.0,
            'code_complexity': 0, 'code_quality_score': 0.0,
            'algorithm_pattern_match': 0.0, 'pep8_violations': 0
        }

    # 커스텀 구성 기반 프롬프트 생성
    prompt_components = []
    if components.get('summary'):
        prompt_components.append("요약된 설명 한 줄 (핵심만)")
    if components.get('libraries'):
        prompt_components.append("사용되는 라이브러리/함수 목록")
    if components.get('code_example'):
        prompt_components.append("코드 예시 (1-3줄)")
    if components.get('step_by_step'):
        prompt_components.append("단계별 해결 방법")
    if components.get('complexity_hint'):
        prompt_components.append("시간/공간 복잡도 힌트")
    if components.get('edge_cases'):
        prompt_components.append("엣지 케이스 체크리스트")
    if components.get('improvements'):
        prompt_components.append("개선 사항 제안")

    components_str = "\n".join(f"- {comp}" for comp in prompt_components)

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

    # 통합 프롬프트 생성
    prompt = f"""당신은 Python 코딩 교육 전문가입니다.

# 문제 정보
{problem_description}

# 학생 코드
{user_code if user_code else '(아직 작성하지 않음)'}

# 코드 분석 결과 (정적 지표)
- 문법 오류: {static_metrics['syntax_errors']}개
- 테스트 통과율: {static_metrics['test_pass_rate']}%
- 코드 복잡도: {static_metrics['code_complexity']} (10 이하 권장)
- 코드 품질 점수: {static_metrics['code_quality_score']}/100
- 알고리즘 패턴 일치도: {static_metrics['algorithm_pattern_match']}%
- PEP8 위반: {static_metrics['pep8_violations']}개
{previous_hints_str}
# 요청 사항
다음 항목만 포함하여 힌트를 제공하세요:
{components_str}

아래 6가지 기준으로 코드를 평가하고 (각 1-5점), 위에서 요청한 항목만 포함한 힌트를 작성하세요:

1. algorithm_efficiency (알고리즘 효율성): 시간/공간 복잡도
2. code_readability (코드 가독성): 변수명, 주석 품질
3. design_pattern_fit (설계 패턴 적합성): 알고리즘 패턴, 자료구조 적합성
4. edge_case_handling (엣지 케이스 처리): 경계 조건, 예외 처리
5. code_conciseness (코드 간결성): 중복 제거, DRY 원칙
6. function_separation (함수 분리도): 모듈화, 단일 책임 원칙

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
  }},
  "llm_metrics": {{
    "algorithm_efficiency": 1-5,
    "code_readability": 1-5,
    "design_pattern_fit": 1-5,
    "edge_case_handling": 1-5,
    "code_conciseness": 1-5,
    "function_separation": 1-5
  }}
}}

위 구성만 포함하여 응답하세요. 선택되지 않은 항목은 null로 반환하세요.
"""

    # AI 설정에 따라 힌트 생성 방식 결정
    hint_response = ""
    llm_metrics = {
        'algorithm_efficiency': 0,
        'code_readability': 0,
        'design_pattern_fit': 0,
        'edge_case_handling': 0,
        'code_conciseness': 0,
        'function_separation': 0
    }

    # RunPod AI 서버 URL 가져오기
    runpod_url = os.environ.get('RUNPOD_AI_URL', '')

    if ai_config.mode == 'runpod' or (ai_config.mode == 'api' and runpod_url):
        # RunPod AI 모델 서버 사용
        if not runpod_url:
            hint_response = "RunPod AI 서버 URL이 설정되지 않았습니다. 관리자에게 문의하세요."
        else:
            try:
                # RunPod AI 서버에 요청
                payload = {
                    'problem_description': problem_description,
                    'user_code': user_code,
                    'previous_hints': previous_hints,
                    'components': components,
                    'static_metrics': static_metrics
                }

                print(f'[INFO] Calling RunPod AI: {runpod_url}/api/v1/generate-hint')
                response = requests.post(
                    f"{runpod_url}/api/v1/generate-hint",
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()

                    if result.get('success'):
                        hint_content = result.get('hint_content', {})
                        llm_metrics_raw = result.get('llm_metrics', {})

                        # LLM 지표 추출
                        llm_metrics = {
                            'algorithm_efficiency': llm_metrics_raw.get('algorithm_efficiency', 3),
                            'code_readability': llm_metrics_raw.get('code_readability', 3),
                            'design_pattern_fit': llm_metrics_raw.get('design_pattern_fit', 3),
                            'edge_case_handling': llm_metrics_raw.get('edge_case_handling', 3),
                            'code_conciseness': llm_metrics_raw.get('code_conciseness', 3),
                            'function_separation': llm_metrics_raw.get('function_separation', 3)
                        }

                        # 힌트 내용 구성
                        hint_parts = []
                        if hint_content.get('summary'):
                            hint_parts.append(f"💡 {hint_content['summary']}")
                        if hint_content.get('libraries'):
                            hint_parts.append(f"📚 사용 라이브러리: {', '.join(hint_content['libraries'])}")
                        if hint_content.get('code_example'):
                            hint_parts.append(f"📝 코드 예시:\n{hint_content['code_example']}")
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
                    else:
                        error = result.get('error', 'Unknown error')
                        print(f'RunPod AI Error: {error}')
                        hint_response = f"AI 힌트 생성 실패: {error}"
                else:
                    error_detail = response.text
                    print(f'RunPod API Error (Status {response.status_code}): {error_detail}')
                    hint_response = f"힌트 생성 실패 (상태 코드: {response.status_code}). 문제의 입출력 예시를 먼저 분석해보세요."
            except Exception as e:
                print(f'RunPod API Error: {str(e)}')
                hint_response = "힌트: 문제의 입력과 출력 형식을 먼저 파악하고, 단계별로 로직을 구성해보세요."

    elif ai_config.mode == 'api':
        # Hugging Face API (Fallback)
        api_key = ai_config.api_key if ai_config.api_key else os.environ.get('HUGGINGFACE_API_KEY', '')

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
                payload = {
                    'model': ai_config.model_name,
                    'messages': [
                        {'role': 'system', 'content': '당신은 코딩 교육 전문가입니다. JSON 형식으로 힌트와 평가 지표를 반환해야 합니다.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 800,
                    'temperature': 0.7,
                    'top_p': 0.9
                }

                response = requests.post(
                    'https://router.huggingface.co/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    if 'choices' in result and len(result['choices']) > 0:
                        llm_response_text = result['choices'][0]['message']['content'].strip()

                        try:
                            llm_data = json.loads(llm_response_text)
                            hint_content = llm_data.get('hint_content', {})
                            llm_metrics_raw = llm_data.get('llm_metrics', {})

                            llm_metrics = {
                                'algorithm_efficiency': llm_metrics_raw.get('algorithm_efficiency', 3),
                                'code_readability': llm_metrics_raw.get('code_readability', 3),
                                'design_pattern_fit': llm_metrics_raw.get('design_pattern_fit', 3),
                                'edge_case_handling': llm_metrics_raw.get('edge_case_handling', 3),
                                'code_conciseness': llm_metrics_raw.get('code_conciseness', 3),
                                'function_separation': llm_metrics_raw.get('function_separation', 3)
                            }

                            hint_parts = []
                            if hint_content.get('summary'):
                                hint_parts.append(f"💡 {hint_content['summary']}")
                            if hint_content.get('libraries'):
                                hint_parts.append(f"📚 사용 라이브러리: {', '.join(hint_content['libraries'])}")
                            if hint_content.get('code_example'):
                                hint_parts.append(f"📝 코드 예시:\n{hint_content['code_example']}")
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

    return Response({
        'success': True,
        'data': {
            'hint': hint_response,
            'problem_id': problem_id,
            'static_metrics': static_metrics,
            'llm_metrics': llm_metrics
        }
    })
