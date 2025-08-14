from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Avg, Count
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Course, CourseMaterial, Enrollment, Feedback, Notification, MaterialCompletion, CourseCompletion
from .forms import CourseForm, CourseMaterialForm, FeedbackForm
from accounts.models import User


class CourseListView(ListView):
    """List all published courses"""
    model = Course
    template_name = 'courses/course_list.html'
    context_object_name = 'courses'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Course.objects.filter(status='published').select_related('teacher').annotate(
            avg_rating=Avg('feedbacks__rating'),
            total_enrollments=Count('enrollments', filter=Q(enrollments__is_active=True))
        )
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(teacher__first_name__icontains=search_query) |
                Q(teacher__last_name__icontains=search_query)
            )
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Filter by difficulty
        difficulty = self.request.GET.get('difficulty')
        if difficulty:
            queryset = queryset.filter(difficulty_level=difficulty)
        
        # Filter by free/paid
        is_free = self.request.GET.get('free')
        if is_free == 'true':
            queryset = queryset.filter(is_free=True)
        elif is_free == 'false':
            queryset = queryset.filter(is_free=False)
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-created_at')
        if sort_by in ['-created_at', 'title', '-total_enrollments', '-avg_rating']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get unique categories for filter
        context['categories'] = Course.objects.values_list('category', flat=True).distinct()
        context['difficulty_choices'] = Course.DIFFICULTY_CHOICES
        
        # Current filter values
        context['current_search'] = self.request.GET.get('search', '')
        context['current_category'] = self.request.GET.get('category', '')
        context['current_difficulty'] = self.request.GET.get('difficulty', '')
        context['current_free'] = self.request.GET.get('free', '')
        context['current_sort'] = self.request.GET.get('sort', '-created_at')
        
        return context


class CourseDetailView(DetailView):
    """Detailed view of a course"""
    model = Course
    template_name = 'courses/course_detail.html'
    context_object_name = 'course'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def get_queryset(self):
        return Course.objects.select_related('teacher').prefetch_related(
            'materials', 'feedbacks__student', 'enrollments'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        
        # Check if user can enroll
        if self.request.user.is_authenticated:
            can_enroll, message = course.can_enroll(self.request.user)
            context['can_enroll'] = can_enroll
            context['enroll_message'] = message
            
            # Check if user is enrolled
            is_enrolled = course.enrollments.filter(
                student=self.request.user, 
                is_active=True
            ).exists()
            context['is_enrolled'] = is_enrolled
            
            # Get enrollment data for progress tracking
            if is_enrolled:
                enrollment = course.enrollments.filter(
                    student=self.request.user, 
                    is_active=True
                ).first()
                context['enrollment'] = enrollment
                
                # Update progress
                if enrollment:
                    enrollment.update_progress()
                
                # Get completed materials for this user
                completed_materials = MaterialCompletion.objects.filter(
                    student=self.request.user,
                    material__course=course
                ).values_list('material_id', flat=True)
                context['completed_materials'] = list(completed_materials)
            
            # Check if user has already left feedback
            context['user_feedback'] = course.feedbacks.filter(
                student=self.request.user
            ).first()
        
        # Get course materials (public or enrolled students)
        if (self.request.user.is_authenticated and 
            (course.enrollments.filter(student=self.request.user, is_active=True).exists() or
             self.request.user == course.teacher)):
            context['materials'] = course.materials.all()
        else:
            context['materials'] = course.materials.filter(is_public=True)
        
        # Get course statistics
        context['avg_rating'] = course.feedbacks.aggregate(
            avg=Avg('rating')
        )['avg'] or 0
        context['total_feedbacks'] = course.feedbacks.count()
        
        # Get recent feedbacks
        context['recent_feedbacks'] = course.feedbacks.filter(
            is_approved=True
        ).select_related('student')[:5]
        
        # Calculate enrollment percentage for progress bar
        if course.max_students > 0:
            context['enrollment_percentage'] = min(100, (course.enrollment_count * 100) // course.max_students)
        else:
            context['enrollment_percentage'] = 0
        
        return context


class TeacherRequiredMixin(UserPassesTestMixin):
    """Mixin to require teacher permissions"""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_teacher


class CourseCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    """Create a new course (teachers only)"""
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    
    def form_valid(self, form):
        form.instance.teacher = self.request.user
        messages.success(self.request, 'Course created successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create New Course'
        context['submit_text'] = 'Create Course'
        return context


class CourseUpdateView(LoginRequiredMixin, TeacherRequiredMixin, UpdateView):
    """Update a course (only by the teacher who created it)"""
    model = Course
    form_class = CourseForm
    template_name = 'courses/course_form.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    
    def test_func(self):
        course = self.get_object()
        return (super().test_func() and 
                (course.teacher == self.request.user or self.request.user.is_superuser))
    
    def form_valid(self, form):
        messages.success(self.request, 'Course updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Edit {self.get_object().title}'
        context['submit_text'] = 'Update Course'
        return context


class CourseDeleteView(LoginRequiredMixin, TeacherRequiredMixin, DeleteView):
    """Delete a course (only by the teacher who created it)"""
    model = Course
    template_name = 'courses/course_confirm_delete.html'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'
    success_url = reverse_lazy('courses:teacher_dashboard')
    
    def test_func(self):
        course = self.get_object()
        return (super().test_func() and 
                (course.teacher == self.request.user or self.request.user.is_superuser))
    
    def delete(self, request, *args, **kwargs):
        course = self.get_object()
        messages.success(request, f'Course "{course.title}" deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Delete {self.get_object().title}'
        return context


@login_required
def enroll_course(request, slug):
    """Enroll a student in a course"""
    course = get_object_or_404(Course, slug=slug, status='published')
    
    if not request.user.is_student:
        messages.error(request, 'Only students can enroll in courses.')
        return redirect('courses:detail', slug=slug)
    
    can_enroll, message = course.can_enroll(request.user)
    
    if can_enroll:
        # Create enrollment
        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course,
            defaults={'is_active': True}
        )
        
        if created:
            messages.success(request, f'Successfully enrolled in "{course.title}"!')
            
            # Create notification for teacher
            Notification.objects.create(
                recipient=course.teacher,
                sender=request.user,
                notification_type='enrollment',
                title='New Student Enrollment',
                message=f'{request.user.get_full_name()} has enrolled in your course "{course.title}".',
                course=course
            )
        else:
            # Reactivate if was previously inactive
            if not enrollment.is_active:
                enrollment.is_active = True
                enrollment.save()
                messages.success(request, f'Re-enrolled in "{course.title}"!')
            else:
                messages.info(request, 'You are already enrolled in this course.')
    else:
        messages.error(request, message)
    
    return redirect('courses:detail', slug=slug)


@login_required
def unenroll_course(request, slug):
    """Unenroll a student from a course"""
    course = get_object_or_404(Course, slug=slug)
    
    try:
        enrollment = Enrollment.objects.get(
            student=request.user,
            course=course,
            is_active=True
        )
        enrollment.is_active = False
        enrollment.save()
        messages.success(request, f'Successfully unenrolled from "{course.title}".')
    except Enrollment.DoesNotExist:
        messages.error(request, 'You are not enrolled in this course.')
    
    return redirect('courses:detail', slug=slug)


class MyCoursesView(LoginRequiredMixin, ListView):
    """View for user's courses (enrolled for students, taught for teachers)"""
    template_name = 'courses/my_courses.html'
    paginate_by = 12
    
    def get_queryset(self):
        if self.request.user.is_teacher:
            # Teachers see their created courses
            return Course.objects.filter(teacher=self.request.user).order_by('-created_at')
        else:
            # Students see their enrollments (not just courses)
            return Enrollment.objects.filter(
                student=self.request.user,
                is_active=True
            ).select_related('course', 'course__teacher').order_by('-date_enrolled')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_type'] = 'teacher' if self.request.user.is_teacher else 'student'
        
        if self.request.user.is_teacher:
            context['courses'] = context['object_list']
        else:
            context['enrollments'] = context['object_list']
        
        return context


@login_required
def submit_feedback(request, slug):
    """Submit feedback for a course"""
    course = get_object_or_404(Course, slug=slug)
    
    # Check if user is enrolled in the course
    if not course.enrollments.filter(student=request.user, is_active=True).exists():
        messages.error(request, 'You must be enrolled in this course to leave feedback.')
        return redirect('courses:detail', slug=slug)
    
    # Check if user has already submitted feedback
    if Feedback.objects.filter(course=course, student=request.user).exists():
        messages.error(request, 'You have already submitted feedback for this course.')
        return redirect('courses:detail', slug=slug)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if not rating:
            messages.error(request, 'Please select a rating.')
            return redirect('courses:detail', slug=slug)
        
        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError("Rating must be between 1 and 5")
        except (ValueError, TypeError):
            messages.error(request, 'Please select a valid rating.')
            return redirect('courses:detail', slug=slug)
        
        # Create the feedback
        Feedback.objects.create(
            course=course,
            student=request.user,
            rating=rating,
            title=f"Feedback for {course.title}",
            content=comment or "No additional comments provided."
        )
        
        messages.success(request, 'Thank you for your feedback!')
        
        # Notify the teacher
        Notification.objects.create(
            recipient=course.teacher,
            sender=request.user,
            notification_type='feedback',
            title='New Course Feedback',
            message=f'{request.user.get_full_name() or request.user.username} left feedback for "{course.title}".',
            course=course
        )
    
    return redirect('courses:detail', slug=slug)


class TeacherDashboardView(LoginRequiredMixin, TeacherRequiredMixin, ListView):
    """Dashboard for teachers to manage their courses"""
    template_name = 'courses/teacher_dashboard.html'
    context_object_name = 'courses'
    
    def get_queryset(self):
        return Course.objects.filter(teacher=self.request.user).annotate(
            total_enrollments=Count('enrollments', filter=Q(enrollments__is_active=True)),
            avg_rating=Avg('feedbacks__rating'),
            total_materials=Count('materials')
        ).order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics
        courses = self.get_queryset()
        total_courses = courses.count()
        published_courses = courses.filter(status='published').count()
        
        total_students = Enrollment.objects.filter(
            course__teacher=self.request.user,
            is_active=True
        ).count()
        
        # Calculate average rating across all courses
        avg_rating = courses.aggregate(
            avg=Avg('feedbacks__rating')
        )['avg'] or 0
        
        context.update({
            'total_students': total_students,
            'published_courses': published_courses,
            'avg_rating': avg_rating,
            'recent_enrollments': Enrollment.objects.filter(
                course__teacher=self.request.user,
                is_active=True
            ).select_related('student', 'course').order_by('-date_enrolled')[:10],
            'recent_feedbacks': Feedback.objects.filter(
                course__teacher=self.request.user
            ).select_related('student', 'course').order_by('-created_at')[:5]
        })
        
        return context


# Course Material Management Views

class CourseMaterialListView(LoginRequiredMixin, TeacherRequiredMixin, ListView):
    """List course materials for a specific course (teachers only)"""
    model = CourseMaterial
    template_name = 'courses/materials/material_list.html'
    context_object_name = 'materials'
    paginate_by = 20
    
    def get_queryset(self):
        self.course = get_object_or_404(
            Course, 
            slug=self.kwargs['slug'], 
            teacher=self.request.user
        )
        return CourseMaterial.objects.filter(course=self.course).order_by('order', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.course
        return context


class CourseMaterialCreateView(LoginRequiredMixin, TeacherRequiredMixin, CreateView):
    """Add new course material (teachers only)"""
    model = CourseMaterial
    form_class = CourseMaterialForm
    template_name = 'courses/materials/material_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        self.course = get_object_or_404(
            Course, 
            slug=self.kwargs['slug'], 
            teacher=self.request.user
        )
        context['course'] = self.course
        return context
    
    def form_valid(self, form):
        self.course = get_object_or_404(
            Course, 
            slug=self.kwargs['slug'], 
            teacher=self.request.user
        )
        form.instance.course = self.course
        
        # Save the material first
        response = super().form_valid(form)
        
        # Create notifications for enrolled students
        enrolled_students = User.objects.filter(
            enrollments__course=self.course,
            enrollments__is_active=True,
            user_type='student'
        ).distinct()
        
        for student in enrolled_students:
            Notification.objects.create(
                recipient=student,
                sender=self.request.user,
                notification_type='material',
                title=f'New Material Added: {form.instance.title}',
                message=f'Your teacher has added new material "{form.instance.title}" to the course "{self.course.title}".',
                course=self.course
            )
        
        messages.success(self.request, f'Material "{form.instance.title}" added successfully!')
        if enrolled_students.exists():
            messages.info(self.request, f'Notifications sent to {enrolled_students.count()} enrolled student(s).')
        
        return response
    
    def get_success_url(self):
        return reverse('courses:materials', kwargs={'slug': self.course.slug})


class CourseMaterialUpdateView(LoginRequiredMixin, TeacherRequiredMixin, UpdateView):
    """Edit course material (teachers only)"""
    model = CourseMaterial
    form_class = CourseMaterialForm
    template_name = 'courses/materials/material_form.html'
    
    def get_queryset(self):
        return CourseMaterial.objects.filter(course__teacher=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f'Material "{form.instance.title}" updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('courses:materials', kwargs={'slug': self.object.course.slug})


class CourseMaterialDeleteView(LoginRequiredMixin, TeacherRequiredMixin, DeleteView):
    """Delete course material (teachers only)"""
    model = CourseMaterial
    template_name = 'courses/materials/material_confirm_delete.html'
    
    def get_queryset(self):
        return CourseMaterial.objects.filter(course__teacher=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['course'] = self.object.course
        return context
    
    def delete(self, request, *args, **kwargs):
        material = self.get_object()
        messages.success(request, f'Material "{material.title}" deleted successfully!')
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse('courses:materials', kwargs={'slug': self.object.course.slug})


@login_required
def mark_material_complete(request, material_id):
    """Mark a material as completed by a student"""
    if not request.user.is_student:
        messages.error(request, "Only students can mark materials as completed.")
        return redirect('courses:list')
    
    material = get_object_or_404(CourseMaterial, id=material_id)
    
    # Check if student is enrolled in the course
    enrollment = get_object_or_404(
        Enrollment, 
        student=request.user, 
        course=material.course, 
        is_active=True
    )
    
    # Mark material as completed
    completion, created = MaterialCompletion.objects.get_or_create(
        student=request.user,
        material=material
    )
    
    if created:
        messages.success(request, f'Material "{material.title}" marked as completed!')
        
        # Update enrollment progress
        enrollment.update_progress()
        
        # Check if course is now completed
        if enrollment.is_completed:
            messages.success(
                request, 
                f'Congratulations! You have completed the course "{material.course.title}"!'
            )
    else:
        messages.info(request, f'Material "{material.title}" was already marked as completed.')
    
    return redirect('courses:detail', slug=material.course.slug)


@login_required
def course_progress(request, slug):
    """View to show detailed course progress"""
    course = get_object_or_404(Course, slug=slug)
    
    if not request.user.is_student:
        messages.error(request, "Only students can view progress.")
        return redirect('courses:detail', slug=slug)
    
    try:
        enrollment = Enrollment.objects.get(
            student=request.user,
            course=course,
            is_active=True
        )
    except Enrollment.DoesNotExist:
        messages.error(request, "You are not enrolled in this course.")
        return redirect('courses:detail', slug=slug)
    
    # Get all materials for this course
    materials = CourseMaterial.objects.filter(course=course).order_by('order', 'created_at')
    
    # Get completed materials for this student
    completed_materials = MaterialCompletion.objects.filter(
        student=request.user,
        material__course=course
    ).values_list('material_id', flat=True)
    
    # Create list with material and completion status
    materials_with_status = []
    for material in materials:
        materials_with_status.append({
            'material': material,
            'is_completed': material.id in completed_materials
        })
    
    # Calculate progress percentage
    total_materials = materials.count()
    completed_count = len(completed_materials)
    progress_percentage = round((completed_count / total_materials * 100) if total_materials > 0 else 0)
    
    # Check if course is completed
    is_completed = enrollment.is_completed
    
    context = {
        'course': course,
        'enrollment': enrollment,
        'materials_with_status': materials_with_status,
        'completed_count': completed_count,
        'total_materials': total_materials,
        'progress_percentage': progress_percentage,
        'is_completed': is_completed,
        'title': f'Progress - {course.title}'
    }
    
    return render(request, 'courses/course_progress.html', context)


@login_required
@require_http_methods(["POST"])
def block_student(request, slug, student_id):
    """Block a student from a course (teachers only)"""
    if not request.user.is_teacher:
        messages.error(request, "Only teachers can block students.")
        return redirect('courses:list')

    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    student = get_object_or_404(User, id=student_id, user_type='student')
    
    try:
        enrollment = Enrollment.objects.get(student=student, course=course)
        enrollment.is_blocked = True
        enrollment.is_active = False
        enrollment.save()
        
        # Create notification for student
        notification = Notification.objects.create(
            recipient=student,
            sender=request.user,
            notification_type='system',
            title='Course Access Blocked',
            message=f'Your access to the course "{course.title}" has been blocked by the teacher.',
            course=course,
            is_important=True
        )
        
        # Send real-time notification to student
        channel_layer = get_channel_layer()
        student_group = f"notifications_{student.id}"
        async_to_sync(channel_layer.group_send)(
            student_group,
            {
                'type': 'notification_message',
                'data': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'is_important': notification.is_important,
                    'created_at': 'just now'
                }
            }
        )
        
        messages.success(request, f'Student {student.get_full_name()} has been blocked from "{course.title}".')
    except Enrollment.DoesNotExist:
        messages.error(request, 'Student is not enrolled in this course.')
    
    return redirect('courses:detail', slug=slug)


@login_required
@require_http_methods(["POST"])
def unblock_student(request, slug, student_id):
    """Unblock a student from a course (teachers only)"""
    if not request.user.is_teacher:
        messages.error(request, "Only teachers can unblock students.")
        return redirect('courses:list')

    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    student = get_object_or_404(User, id=student_id, user_type='student')
    
    try:
        enrollment = Enrollment.objects.get(student=student, course=course)
        enrollment.is_blocked = False
        enrollment.is_active = True
        enrollment.save()
        
        # Create notification for student
        notification = Notification.objects.create(
            recipient=student,
            sender=request.user,
            notification_type='system',
            title='Course Access Restored',
            message=f'Your access to the course "{course.title}" has been restored by the teacher.',
            course=course
        )
        
        # Send real-time notification to student
        channel_layer = get_channel_layer()
        student_group = f"notifications_{student.id}"
        async_to_sync(channel_layer.group_send)(
            student_group,
            {
                'type': 'notification_message',
                'data': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'type': notification.notification_type,
                    'is_important': notification.is_important,
                    'created_at': 'just now'
                }
            }
        )
        
        messages.success(request, f'Student {student.get_full_name()} has been unblocked from "{course.title}".')
    except Enrollment.DoesNotExist:
        messages.error(request, 'Student is not enrolled in this course.')
    
    return redirect('courses:detail', slug=slug)


@login_required
def manage_course_students(request, slug):
    """Manage enrolled students for a course (teachers only)"""
    if not request.user.is_teacher:
        messages.error(request, "Only teachers can manage course students.")
        return redirect('courses:list')
    
    course = get_object_or_404(Course, slug=slug, teacher=request.user)
    
    # Get all enrollments for this course
    enrollments = Enrollment.objects.filter(course=course).select_related('student').order_by(
        '-is_active', '-is_blocked', '-date_enrolled'
    )
    
    context = {
        'course': course,
        'enrollments': enrollments,
        'title': f'Manage Students - {course.title}'
    }
    
    return render(request, 'courses/manage_students.html', context)


@login_required
def select_course_for_management(request):
    """View to select which course to manage students for"""
    if not request.user.is_teacher:
        messages.error(request, "Only teachers can access this feature.")
        return redirect('courses:list')
    
    courses = Course.objects.filter(teacher=request.user).select_related('teacher').prefetch_related('enrollments', 'materials')
    
    context = {
        'courses': courses,
        'title': 'Select Course to Manage Students'
    }
    
    return render(request, 'courses/select_course_for_management.html', context)


@login_required
def notifications_view(request):
    """View user's notifications"""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:20]  # Get latest 20 notifications
    
    # Mark all notifications as read when user visits the page
    Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).update(is_read=True)
    
    return render(request, 'courses/notifications.html', {
        'notifications': notifications
    })


@login_required
def mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    if request.method == 'POST':
        notification = get_object_or_404(
            Notification, 
            id=notification_id, 
            recipient=request.user
        )
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})
