"""
URL configuration for hint system project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include


def api_root(_request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1', api_root),
    path('api/v1/', api_root),

    # API v1 엔드포인트 (탭별 모듈화)
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/coding-test/', include('apps.coding_test.urls')),
    path('api/v1/chatbot/', include('apps.chatbot.urls')),
    path('api/v1/mypage/', include('apps.mypage.urls')),
    path('api/v1/admin/', include('apps.admin_panel.urls')),
]

# Static and Media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
