"""
Custom pagination classes.
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    표준 페이지네이션 (20개씩)
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class LargeResultsSetPagination(PageNumberPagination):
    """
    큰 데이터셋용 페이지네이션 (50개씩)
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class SmallResultsSetPagination(PageNumberPagination):
    """
    작은 데이터셋용 페이지네이션 (10개씩)
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
