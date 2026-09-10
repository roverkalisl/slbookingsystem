"""
Django admin configuration for core app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, UserProfile, Role, UserRole, Permission, RolePermission, SystemSetting


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('phone', 'avatar_url', 'bio', 'preferred_language')}),
        ('Verification', {'fields': ('email_verified', 'phone_verified')}),
        ('Notifications', {'fields': ('notification_email', 'notification_sms')}),
    )
    list_display = ['email', 'first_name', 'last_name', 'is_staff', 'is_active', 'created_at']
    list_filter = ['is_staff', 'is_active', 'email_verified', 'phone_verified', 'created_at']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-created_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """User profile admin"""

    list_display = ['user', 'country', 'city', 'created_at']
    search_fields = ['user__email', 'country', 'city']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Role admin"""

    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """User role admin"""

    list_display = ['user', 'role', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['user__email', 'role__name']


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Permission admin"""

    list_display = ['name', 'description']
    search_fields = ['name']


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Role permission admin"""

    list_display = ['role', 'permission']
    list_filter = ['role']
    search_fields = ['role__name', 'permission__name']


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """System settings admin"""

    list_display = ['setting_key', 'setting_value', 'updated_at']
    search_fields = ['setting_key']
    readonly_fields = ['created_at', 'updated_at']
