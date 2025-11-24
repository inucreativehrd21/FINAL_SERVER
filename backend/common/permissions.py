"""
Custom permissions for the application.
"""
from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    관리자 권한 체크
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    본인 또는 관리자만 접근 가능
    """
    def has_object_permission(self, request, view, obj):
        # 관리자는 모든 접근 허용
        if request.user.role == 'admin':
            return True

        # 본인의 데이터만 접근 가능
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    인증된 사용자는 모든 작업, 비인증 사용자는 읽기만 가능
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated
