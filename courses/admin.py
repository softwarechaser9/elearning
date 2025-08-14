from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from .models import Course, CourseMaterial, Enrollment, Feedback, Notification, MaterialCompletion, CourseCompletion


class CourseMaterialInline(admin.TabularInline):
    """Inline admin for course materials"""
    model = CourseMaterial
    extra = 1
    fields = ['title', 'material_type', 'file', 'external_link', 'order', 'is_downloadable']
    ordering = ['order']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin interface for Course model"""
    
    list_display = [
        'title', 'teacher', 'status', 'difficulty_level', 
        'enrollment_count_display', 'is_free', 'created_at'
    ]
    list_filter = [
        'status', 'difficulty_level', 'is_free', 'created_at', 
        'teacher__username'
    ]
    search_fields = ['title', 'description', 'teacher__username', 'teacher__first_name']
    ordering = ['-created_at']
    list_per_page = 25
    
    # Organize fields into sections
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'teacher', 'status')
        }),
        ('Course Content', {
            'fields': ('description', 'short_description', 'course_image')
        }),
        ('Course Settings', {
            'fields': (
                'category', 'difficulty_level', 'max_students', 
                'is_free', 'price'
            ),
            'classes': ('collapse',)
        }),
        ('Learning Information', {
            'fields': ('prerequisites', 'learning_outcomes'),
            'classes': ('collapse',)
        }),
        ('SEO & Tags', {
            'fields': ('meta_description', 'tags'),
            'classes': ('collapse',)
        }),
    )
    
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['created_at', 'updated_at']
    
    # Add inline for course materials
    inlines = [CourseMaterialInline]
    
    def enrollment_count_display(self, obj):
        """Display enrollment count with color coding"""
        count = obj.enrollment_count
        max_students = obj.max_students
        
        if count >= max_students:
            color = 'red'
        elif count >= max_students * 0.8:
            color = 'orange'
        else:
            color = 'green'
        
        return format_html(
            '<span style="color: {};">{}/{}</span>',
            color, count, max_students
        )
    enrollment_count_display.short_description = 'Enrollments'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('teacher').prefetch_related('enrollments')
    
    def save_model(self, request, obj, form, change):
        """Auto-assign teacher if creating new course"""
        if not change and not obj.teacher:
            if request.user.is_teacher:
                obj.teacher = request.user
        super().save_model(request, obj, form, change)


@admin.register(CourseMaterial)
class CourseMaterialAdmin(admin.ModelAdmin):
    """Admin interface for CourseMaterial model"""
    
    list_display = [
        'title', 'course', 'material_type', 'file_size_display', 
        'is_downloadable', 'is_public', 'created_at'
    ]
    list_filter = [
        'material_type', 'is_downloadable', 'is_public', 
        'created_at', 'course__teacher'
    ]
    search_fields = ['title', 'description', 'course__title']
    ordering = ['course', 'order', '-created_at']
    list_per_page = 50
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('course', 'title', 'description', 'material_type')
        }),
        ('Content', {
            'fields': ('file', 'external_link', 'duration')
        }),
        ('Settings', {
            'fields': ('order', 'is_downloadable', 'is_public')
        }),
    )
    
    readonly_fields = ['file_size', 'created_at', 'updated_at']
    
    def file_size_display(self, obj):
        """Display formatted file size"""
        return obj.formatted_file_size or 'N/A'
    file_size_display.short_description = 'File Size'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('course', 'course__teacher')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """Admin interface for Enrollment model"""
    
    list_display = [
        'student', 'course', 'date_enrolled', 'progress', 
        'is_active', 'is_completed'
    ]
    list_filter = [
        'is_active', 'date_enrolled', 'progress', 
        'course__teacher', 'student__user_type'
    ]
    search_fields = [
        'student__username', 'student__first_name', 
        'course__title', 'course__teacher__username'
    ]
    ordering = ['-date_enrolled']
    list_per_page = 50
    
    fieldsets = (
        ('Enrollment Details', {
            'fields': ('student', 'course', 'is_active')
        }),
        ('Progress Tracking', {
            'fields': ('progress', 'date_completed', 'certificate_issued')
        }),
        ('Notes', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['date_enrolled', 'created_at', 'updated_at']
    
    def is_completed(self, obj):
        """Display completion status"""
        if obj.is_completed:
            return format_html('<span style="color: green;">✓ Completed</span>')
        return format_html('<span style="color: orange;">In Progress</span>')
    is_completed.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('student', 'course')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    """Admin interface for Feedback model"""
    
    list_display = [
        'student_display', 'course', 'rating_display', 
        'is_approved', 'helpful_votes', 'created_at'
    ]
    list_filter = [
        'rating', 'is_approved', 'is_anonymous', 
        'created_at', 'course__teacher'
    ]
    search_fields = [
        'student__username', 'course__title', 
        'title', 'content'
    ]
    ordering = ['-created_at']
    list_per_page = 50
    
    fieldsets = (
        ('Feedback Details', {
            'fields': ('course', 'student', 'rating', 'title', 'content')
        }),
        ('Settings', {
            'fields': ('is_anonymous', 'is_approved', 'helpful_votes')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'helpful_votes']
    
    def student_display(self, obj):
        """Display student name or anonymous"""
        if obj.is_anonymous:
            return format_html('<em>Anonymous</em>')
        return obj.student.get_full_name()
    student_display.short_description = 'Student'
    
    def rating_display(self, obj):
        """Display rating with stars"""
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span title="{}/5 stars">{}</span>', obj.rating, stars)
    rating_display.short_description = 'Rating'
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related('student', 'course')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin interface for Notification model"""
    
    list_display = [
        'title', 'recipient', 'notification_type', 
        'is_read', 'is_important', 'created_at'
    ]
    list_filter = [
        'notification_type', 'is_read', 'is_important', 
        'created_at', 'course'
    ]
    search_fields = [
        'title', 'message', 'recipient__username', 
        'sender__username'
    ]
    ordering = ['-created_at']
    list_per_page = 100
    
    fieldsets = (
        ('Notification Details', {
            'fields': ('recipient', 'sender', 'notification_type', 'title', 'message')
        }),
        ('Related Objects', {
            'fields': ('course',),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'is_important')
        }),
    )
    
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        """Optimize queries"""
        return super().get_queryset(request).select_related(
            'recipient', 'sender', 'course'
        )


@admin.register(MaterialCompletion)
class MaterialCompletionAdmin(admin.ModelAdmin):
    """Admin for Material Completion"""
    list_display = ('student', 'material', 'completed_at')
    list_filter = ('completed_at', 'material__course')
    search_fields = ('student__username', 'material__title')
    readonly_fields = ('completed_at',)


@admin.register(CourseCompletion)
class CourseCompletionAdmin(admin.ModelAdmin):
    """Admin for Course Completion"""
    list_display = ('student', 'course', 'completion_percentage', 'completed_at')
    list_filter = ('completed_at', 'course')
    search_fields = ('student__username', 'course__title')
    readonly_fields = ('completed_at',)
