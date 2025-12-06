"""
인증 URL 설정
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

app_name = 'authentication'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('send-verification-email/', views.send_verification_email, name='send_verification_email'),
    path('verify-email-code/', views.verify_email_code, name='verify_email_code'),
    path('kakao/login/', views.kakao_login, name='kakao_login'),
    path('user/', views.get_user_info, name='user_info'),
    path('user/update/', views.update_user_info, name='update_user'),
    path('user/password/', views.change_password, name='change_password'),
    path('user/delete/', views.delete_account, name='delete_account'),
    path('users/', views.list_users, name='list_users'),
    path('users/<int:user_id>/permissions/', views.update_user_permissions, name='update_user_permissions'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
]
