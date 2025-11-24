"""
Custom exception handlers.
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    커스텀 예외 핸들러
    """
    # 기본 DRF 예외 핸들러 호출
    response = exception_handler(exc, context)

    if response is not None:
        # 에러 응답 포맷 통일
        custom_response_data = {
            'success': False,
            'error': {
                'message': str(exc),
                'details': response.data
            }
        }
        response.data = custom_response_data

    return response


class CodeExecutionError(Exception):
    """코드 실행 관련 에러"""
    pass


class HintGenerationError(Exception):
    """힌트 생성 관련 에러"""
    pass


class VectorDBError(Exception):
    """벡터 DB 관련 에러"""
    pass
