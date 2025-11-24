from django.contrib import admin
from .models import Problem, Submission, Bookmark, HintRequest


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ['problem_id', 'title', 'level', 'step_title', 'created_at']
    list_filter = ['level']
    search_fields = ['problem_id', 'title', 'step_title']
    ordering = ['problem_id']


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem', 'result', 'execution_count', 'rating_earned', 'created_at']
    list_filter = ['result', 'created_at']
    search_fields = ['user__username', 'problem__title']
    ordering = ['-created_at']


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem', 'created_at']
    search_fields = ['user__username', 'problem__title']
    ordering = ['-created_at']


@admin.register(HintRequest)
class HintRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'problem', 'hint_level', 'model_used', 'created_at']
    list_filter = ['hint_level', 'created_at']
    search_fields = ['user__username', 'problem__title']
    ordering = ['-created_at']
