# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, LoginHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'role', 'is_verified', 'is_active']
    list_filter = ['role', 'is_verified', 'is_active']
    search_fields = ['email', 'username', 'first_name', 'last_name']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('role', 'nim_nip', 'instansi', 'phone', 'avatar', 'is_verified')
        }),
    )


@admin.register(LoginHistory)
class LoginHistoryAdmin(admin.ModelAdmin):
    list_display  = ['user', 'ip_address', 'device_type', 'success', 'login_at']  
    list_filter   = ['success', 'device_type', 'login_at']                         
    search_fields = ['user__email', 'ip_address']
