"""
AI 모델 설정 API
"""
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from .models import AIModelConfig


@api_view(['GET'])
@permission_classes([IsAdminUser])
def get_ai_config(request):
    """AI 모델 설정 조회 (관리자 전용)"""
    config = AIModelConfig.get_config()
    return Response({
        'success': True,
        'data': {
            'mode': config.mode,
            'hint_engine': getattr(config, 'hint_engine', 'api'),
            'api_key': config.api_key if config.api_key else '',
            'openai_api_key': getattr(config, 'openai_api_key', '') or '',
            'model_name': config.model_name,
            'is_model_loaded': config.is_model_loaded,
            'runpod_endpoint': config.runpod_endpoint if config.runpod_endpoint else '',
            'runpod_api_key': config.runpod_api_key if config.runpod_api_key else '',
            'updated_at': config.updated_at
        }
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def update_ai_config(request):
    """AI 모델 설정 업데이트 (관리자 전용)"""
    config = AIModelConfig.get_config()

    mode = request.data.get('mode')
    hint_engine = request.data.get('hint_engine')
    api_key = request.data.get('api_key')
    openai_api_key = request.data.get('openai_api_key')
    model_name = request.data.get('model_name')
    runpod_endpoint = request.data.get('runpod_endpoint')
    runpod_api_key = request.data.get('runpod_api_key')

    if mode and mode not in ['api', 'openai', 'local', 'runpod']:
        return Response({
            'success': False,
            'message': '올바르지 않은 모드입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    if hint_engine and hint_engine not in ['api', 'langgraph']:
        return Response({
            'success': False,
            'message': '올바르지 않은 힌트 엔진입니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # 모드 변경
    if mode:
        old_mode = config.mode
        config.mode = mode

        # 로컬 모드에서 API 모드로 변경 시 모델 언로드
        if old_mode == 'local' and mode in ['api', 'openai']:
            config.is_model_loaded = False
            # TODO: 실제 모델 언로드 로직

    # 힌트 엔진 변경
    if hint_engine:
        config.hint_engine = hint_engine

    # HuggingFace API 키 업데이트
    if api_key is not None:
        config.api_key = api_key
        # .env 파일 업데이트
        update_env_file('HUGGINGFACE_API_KEY', api_key)

    # OpenAI API 키 업데이트
    if openai_api_key is not None:
        config.openai_api_key = openai_api_key
        update_env_file('OPENAI_API_KEY', openai_api_key)

    # 모델 이름 업데이트
    if model_name:
        config.model_name = model_name

    # Runpod 설정 업데이트
    if runpod_endpoint is not None:
        config.runpod_endpoint = runpod_endpoint

    if runpod_api_key is not None:
        config.runpod_api_key = runpod_api_key

    config.save()

    return Response({
        'success': True,
        'message': 'AI 모델 설정이 업데이트되었습니다.',
        'data': {
            'mode': config.mode,
            'hint_engine': getattr(config, 'hint_engine', 'api'),
            'api_key': config.api_key if config.api_key else '',
            'openai_api_key': getattr(config, 'openai_api_key', '') or '',
            'model_name': config.model_name,
            'is_model_loaded': config.is_model_loaded,
            'runpod_endpoint': config.runpod_endpoint if config.runpod_endpoint else '',
            'runpod_api_key': config.runpod_api_key if config.runpod_api_key else ''
        }
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def load_local_model(request):
    """로컬 모델 로드 (관리자 전용)"""
    config = AIModelConfig.get_config()

    if config.mode != 'local':
        return Response({
            'success': False,
            'message': '로컬 모드가 아닙니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    if config.is_model_loaded:
        return Response({
            'success': False,
            'message': '모델이 이미 로드되어 있습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # TODO: 실제 모델 로드 로직 구현
    # from transformers import AutoModelForCausalLM, AutoTokenizer
    # model = AutoModelForCausalLM.from_pretrained(...)

    config.is_model_loaded = True
    config.save()

    return Response({
        'success': True,
        'message': '모델이 로드되었습니다.'
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def unload_local_model(request):
    """로컬 모델 언로드 (관리자 전용)"""
    config = AIModelConfig.get_config()

    if config.mode != 'local':
        return Response({
            'success': False,
            'message': '로컬 모드가 아닙니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not config.is_model_loaded:
        return Response({
            'success': False,
            'message': '모델이 로드되어 있지 않습니다.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # TODO: 실제 모델 언로드 로직

    config.is_model_loaded = False
    config.save()

    return Response({
        'success': True,
        'message': '모델이 언로드되었습니다.'
    })


def update_env_file(key, value):
    """
    .env 파일 업데이트
    """
    from pathlib import Path
    import re

    env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'

    if not env_path.exists():
        return

    with open(env_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    key_found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f'{key}='):
            lines[i] = f'{key}={value}\n'
            key_found = True
            break

    if not key_found:
        lines.append(f'{key}={value}\n')

    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
