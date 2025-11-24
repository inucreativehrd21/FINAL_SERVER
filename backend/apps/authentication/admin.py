from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'rating', 'tendency', 'created_at']
    list_filter = ['role', 'tendency', 'is_active']
    search_fields = ['username', 'email']
    ordering = ['-created_at']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('추가 정보', {'fields': ('role', 'rating', 'tendency')}),
    )
