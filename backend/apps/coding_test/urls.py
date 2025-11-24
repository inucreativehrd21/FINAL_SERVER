"""
코딩 테스트 URL 설정
"""
from django.urls import path
from . import views
from .hint_api import request_hint
from .ai_config_api import (
    get_ai_config,
    update_ai_config,
    load_local_model,
    unload_local_model
)
from .roadmap_api import (
    submit_survey,
    get_roadmap,
    list_roadmaps,
    delete_roadmap,
    activate_roadmap,
    get_badges,
    get_user_badges,
    get_user_goals
)

app_name = 'coding_test'

urlpatterns = [
    # 문제 관리
    path('problems/', views.ProblemListView.as_view(), name='problem_list'),
    path('problems/<str:problem_id>/', views.ProblemDetailView.as_view(), name='problem_detail'),

    # 코드 실행
    path('execute/', views.execute_code, name='execute_code'),
    path('submit/', views.submit_code, name='submit_code'),

    # 힌트
    path('hints/', request_hint, name='request_hint'),

    # 제출 기록
    path('submissions/', views.SubmissionListView.as_view(), name='submission_list'),
    path('submissions/<int:pk>/', views.SubmissionDetailView.as_view(), name='submission_detail'),

    # 북마크
    path('bookmarks/', views.BookmarkListView.as_view(), name='bookmark_list'),
    path('bookmarks/toggle/', views.toggle_bookmark, name='toggle_bookmark'),

    # 테스트 케이스 제안
    path('test-cases/propose/', views.propose_test_case, name='propose_test_case'),
    path('test-cases/', views.list_test_case_proposals, name='list_test_cases'),
    path('test-cases/<str:problem_id>/approved/', views.get_approved_test_cases, name='get_approved_test_cases'),
    path('test-cases/<int:proposal_id>/approve/', views.approve_test_case, name='approve_test_case'),
    path('test-cases/<int:proposal_id>/reject/', views.reject_test_case, name='reject_test_case'),

    # 솔루션 제안
    path('solutions/propose/', views.propose_solution, name='propose_solution'),
    path('solutions/', views.list_solution_proposals, name='list_solutions'),
    path('solutions/<int:proposal_id>/approve/', views.approve_solution, name='approve_solution'),
    path('solutions/<int:proposal_id>/reject/', views.reject_solution, name='reject_solution'),

    # AI 모델 설정
    path('ai-config/', get_ai_config, name='get_ai_config'),
    path('ai-config/update/', update_ai_config, name='update_ai_config'),
    path('ai-config/load-model/', load_local_model, name='load_local_model'),
    path('ai-config/unload-model/', unload_local_model, name='unload_local_model'),

    # 설문조사 & 로드맵
    path('survey/', submit_survey, name='submit_survey'),
    path('roadmap/', get_roadmap, name='get_roadmap'),
    path('roadmaps/', list_roadmaps, name='list_roadmaps'),
    path('roadmaps/<int:roadmap_id>/delete/', delete_roadmap, name='delete_roadmap'),
    path('roadmaps/<int:roadmap_id>/activate/', activate_roadmap, name='activate_roadmap'),

    # 뱃지 & 목표
    path('badges/', get_badges, name='get_badges'),
    path('user-badges/', get_user_badges, name='get_user_badges'),
    path('user-goals/', get_user_goals, name='get_user_goals'),
]
