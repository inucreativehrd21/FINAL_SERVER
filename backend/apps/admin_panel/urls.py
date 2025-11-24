from django.urls import path
from . import views

app_name = 'admin_panel'
urlpatterns = [
    path('current-user/', views.get_current_user, name='get_current_user'),
    path('users/', views.get_users, name='get_users'),
    path('users/<int:user_id>/', views.update_user, name='update_user'),
    path('users/<int:user_id>/skill/', views.update_user_skill, name='update_user_skill'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('statistics/', views.get_statistics, name='get_statistics'),
]
