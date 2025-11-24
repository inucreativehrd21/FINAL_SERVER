from django.urls import path
from . import views

app_name = 'mypage'
urlpatterns = [
    path('statistics/', views.user_statistics, name='user_statistics'),
    path('badges/', views.user_badges, name='user_badges'),
]
