from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTPToken, UserInvitation

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """Admin interface for custom User model"""
    
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active', 'date_joined']
    list_filter = ['role', 'is_verified', 'is_active', 'date_joined']
    search_fields = ['email', 'first_name', 'last_name']
    ordering = ['-date_joined']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'role', 'is_verified')
        }),
        ('Genealogy Permissions', {
            'fields': ('can_add_children', 'can_modify_own_info', 'can_view_private_info', 'can_export_data')
        }),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('email', 'first_name', 'last_name', 'role')
        }),
    )

@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    """Admin interface for OTP tokens"""
    
    list_display = ['user', 'token', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['token', 'created_at', 'expires_at']
    ordering = ['-created_at']

@admin.register(UserInvitation)
class UserInvitationAdmin(admin.ModelAdmin):
    """Admin interface for user invitations"""
    
    list_display = ['email', 'invited_by', 'status', 'role', 'created_at', 'expires_at']
    list_filter = ['status', 'role', 'created_at']
    search_fields = ['email', 'invited_by__email']
    readonly_fields = ['token', 'created_at']
    ordering = ['-created_at']