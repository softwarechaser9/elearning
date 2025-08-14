from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, StatusUpdate, UserProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin interface for custom User model"""
    
    # Fields to display in the admin list view
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'user_type', 'is_verified', 'is_active', 'date_joined'
    ]
    
    # Fields to filter by
    list_filter = [
        'user_type', 'is_verified', 'is_active', 
        'is_staff', 'is_superuser', 'date_joined'
    ]
    
    # Fields to search by
    search_fields = ['username', 'email', 'first_name', 'last_name']
    
    # Default ordering
    ordering = ['-date_joined']
    
    # Fields that can be edited inline
    list_editable = ['is_verified', 'is_active']
    
    # Number of items per page
    list_per_page = 25
    
    # Add custom fieldsets for the edit form
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Profile Information', {
            'fields': (
                'user_type', 'bio', 'profile_picture', 
                'phone_number', 'location'
            )
        }),
        ('Professional Information', {
            'fields': ('qualification', 'experience_years'),
            'classes': ('collapse',)  # Make this section collapsible
        }),
        ('Account Settings', {
            'fields': ('is_verified',)
        }),
    )
    
    # Fields to display when adding a new user
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Profile Information', {
            'fields': (
                'email', 'first_name', 'last_name', 
                'user_type', 'bio'
            )
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queries by selecting related fields"""
        return super().get_queryset(request).select_related('profile')


@admin.register(StatusUpdate)
class StatusUpdateAdmin(admin.ModelAdmin):
    """Admin interface for StatusUpdate model"""
    
    list_display = ['user', 'content_preview', 'is_public', 'created_at']
    list_filter = ['is_public', 'created_at', 'user__user_type']
    search_fields = ['user__username', 'content']
    ordering = ['-created_at']
    list_per_page = 25
    
    # Make some fields read-only
    readonly_fields = ['created_at', 'updated_at']
    
    def content_preview(self, obj):
        """Show a preview of the content"""
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content Preview'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin interface for UserProfile model"""
    
    list_display = [
        'user', 'email_notifications', 'course_notifications', 
        'profile_views', 'last_activity'
    ]
    list_filter = [
        'email_notifications', 'course_notifications', 
        'marketing_notifications', 'created_at'
    ]
    search_fields = ['user__username', 'user__email']
    ordering = ['-last_activity']
    list_per_page = 25
    
    # Organize fields into sections
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Social Links', {
            'fields': ('website', 'linkedin', 'twitter'),
            'classes': ('collapse',)
        }),
        ('Notification Preferences', {
            'fields': (
                'email_notifications', 'course_notifications', 
                'marketing_notifications'
            )
        }),
        ('Privacy Settings', {
            'fields': ('show_email', 'show_phone'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('profile_views', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['profile_views', 'last_activity', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('user')


# Customize admin site headers
admin.site.site_header = "eLearning Administration"
admin.site.site_title = "eLearning Admin"
admin.site.index_title = "Welcome to eLearning Administration Portal"
