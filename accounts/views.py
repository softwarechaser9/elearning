from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, DetailView, UpdateView, ListView
from django.urls import reverse_lazy, reverse
from django.db.models import Q
from django.http import JsonResponse
from django.core.paginator import Paginator

from .models import User, StatusUpdate, UserProfile
from .forms import (
    CustomUserCreationForm, CustomAuthenticationForm, 
    UserProfileForm, UserProfileExtendedForm, 
    StatusUpdateForm, TeacherSearchForm
)


class RegisterView(CreateView):
    """User registration view"""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:login')
    
    def form_valid(self, form):
        """Handle successful form submission"""
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'Account created successfully! Welcome, {self.object.first_name}!'
        )
        return response
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Create Account'
        return context


def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    form = CustomAuthenticationForm()
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            remember_me = form.cleaned_data.get('remember_me', False)
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                
                # Set session expiry based on remember_me
                if not remember_me:
                    request.session.set_expiry(0)  # Browser close
                
                messages.success(request, f'Welcome back, {user.first_name}!')
                
                # Redirect to next or dashboard
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password.')
    
    context = {
        'form': form,
        'title': 'Login'
    }
    return render(request, 'accounts/login.html', context)


@login_required
def logout_view(request):
    """Logout view"""
    user_name = request.user.first_name
    logout(request)
    messages.success(request, f'Goodbye, {user_name}! You have been logged out.')
    return redirect('home')


class ProfileView(DetailView):
    """User profile view"""
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile_user = self.get_object()
        
        # Get recent status updates
        status_updates = profile_user.status_updates.filter(
            is_public=True
        )[:5]
        
        # If viewing own profile, show all status updates
        if self.request.user == profile_user:
            status_updates = profile_user.status_updates.all()[:5]
        
        # Update profile views count if viewing someone else's profile
        if self.request.user.is_authenticated and self.request.user != profile_user:
            profile, created = UserProfile.objects.get_or_create(user=profile_user)
            profile.profile_views += 1
            profile.save()
        
        context.update({
            'status_updates': status_updates,
            'is_own_profile': self.request.user == profile_user,
            'title': f"{profile_user.get_full_name()}'s Profile"
        })
        
        # Add course-related context for teachers and students
        if profile_user.is_teacher:
            context['taught_courses'] = profile_user.get_courses_as_teacher()[:3]
        elif profile_user.is_student:
            context['enrolled_courses'] = profile_user.get_enrolled_courses()[:3]
        
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update user profile"""
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        return reverse('accounts:profile', kwargs={'username': self.request.user.username})
    
    def form_valid(self, form):
        messages.success(self.request, 'Profile updated successfully!')
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Profile'
        
        # Add extended profile form
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        if self.request.method == 'POST':
            context['profile_form'] = UserProfileExtendedForm(
                self.request.POST, 
                instance=profile
            )
        else:
            context['profile_form'] = UserProfileExtendedForm(instance=profile)
        
        return context
    
    def form_valid(self, form):
        # Handle extended profile form
        profile, created = UserProfile.objects.get_or_create(user=self.request.user)
        profile_form = UserProfileExtendedForm(self.request.POST, instance=profile)
        
        if profile_form.is_valid():
            profile_form.save()
        
        return super().form_valid(form)


@login_required
@login_required
def dashboard_view(request):
    """User dashboard view"""
    user = request.user
    print(f"DEBUG: Dashboard view called for user: {user.username}, user_type: {user.user_type}")
    print(f"DEBUG: is_teacher: {user.is_teacher}, is_student: {user.is_student}")
    
    context = {
        'user': user,
        'title': 'Dashboard'
    }
    
    # Get recent status updates from followed users (for now, just show recent public updates)
    recent_status_updates = StatusUpdate.objects.filter(
        is_public=True
    ).select_related('user')[:10]
    
    context['recent_status_updates'] = recent_status_updates
    
    # Add user-specific dashboard data
    if user.is_teacher:
        print("DEBUG: Processing teacher dashboard")
        # Teacher dashboard data
        from courses.models import Course, Enrollment
        taught_courses = Course.objects.filter(teacher=user)
        courses_count = taught_courses.count()
        print(f"DEBUG: Teacher {user.username} has {courses_count} courses")
        
        context['taught_courses'] = taught_courses[:5]
        context['courses_created_count'] = courses_count
        
        # Get total students across all courses (count unique students)
        total_students = Enrollment.objects.filter(
            course__teacher=user, 
            is_active=True
        ).values('student').distinct().count()
        print(f"DEBUG: Teacher {user.username} has {total_students} total students")
        context['total_students'] = total_students
    
    elif user.is_student:
        print("DEBUG: Processing student dashboard")
        # Student dashboard data
        from courses.models import Enrollment, CourseCompletion
        enrolled_courses = Enrollment.objects.filter(student=user, is_active=True)
        total_enrolled = enrolled_courses.count()
        print(f"DEBUG: Student {user.username} is enrolled in {total_enrolled} courses")
        
        context['enrolled_courses'] = [enrollment.course for enrollment in enrolled_courses[:5]]
        
        # Calculate completion statistics - CourseCompletion has direct student field
        completed_courses = CourseCompletion.objects.filter(
            student=user
        ).count()
        print(f"DEBUG: Student {user.username} has completed {completed_courses} courses")
        
        context['courses_enrolled_count'] = total_enrolled
        context['courses_completed_count'] = completed_courses
    else:
        print(f"DEBUG: User {user.username} is neither teacher nor student")
        # Set default values for other user types
        context['courses_created_count'] = 0
        context['total_students'] = 0
        context['courses_enrolled_count'] = 0
        context['courses_completed_count'] = 0
        
    # Status updates count
    status_count = user.status_updates.count()
    print(f"DEBUG: User {user.username} has {status_count} status updates")
    context['status_updates_count'] = status_count
    
    print(f"DEBUG: Final context keys: {list(context.keys())}")
    return render(request, 'dashboard.html', context)


@login_required
def create_status_update(request):
    """Create a new status update"""
    if request.method == 'POST':
        form = StatusUpdateForm(request.POST)
        if form.is_valid():
            status_update = form.save(commit=False)
            status_update.user = request.user
            status_update.save()
            messages.success(request, 'Status update posted!')
            
            # Return JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Status update posted!',
                    'redirect': reverse('accounts:profile', kwargs={'username': request.user.username})
                })
            
            return redirect('accounts:profile', username=request.user.username)
        else:
            messages.error(request, 'Error posting status update.')
    
    return redirect('accounts:profile', username=request.user.username)


class UserSearchView(LoginRequiredMixin, ListView):
    """Search for users (teachers can search for students and other teachers)"""
    model = User
    template_name = 'accounts/user_search.html'
    context_object_name = 'users'
    paginate_by = 12
    
    def get_queryset(self):
        """Filter users based on search criteria"""
        queryset = User.objects.filter(is_active=True).select_related('profile')
        
        # Only teachers can search for users
        if not self.request.user.is_teacher:
            return User.objects.none()
        
        form = TeacherSearchForm(self.request.GET)
        if form.is_valid():
            search_query = form.cleaned_data.get('search_query')
            user_type = form.cleaned_data.get('user_type')
            is_verified = form.cleaned_data.get('is_verified')
            
            if search_query:
                queryset = queryset.filter(
                    Q(username__icontains=search_query) |
                    Q(first_name__icontains=search_query) |
                    Q(last_name__icontains=search_query) |
                    Q(email__icontains=search_query)
                )
            
            if user_type:
                queryset = queryset.filter(user_type=user_type)
            
            if is_verified:
                queryset = queryset.filter(is_verified=True)
        
        # Exclude the current user from results
        queryset = queryset.exclude(id=self.request.user.id)
        
        return queryset.order_by('-date_joined')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = TeacherSearchForm(self.request.GET)
        context['title'] = 'Search Users'
        return context


def home_view(request):
    """Home page view"""
    context = {
        'title': 'Welcome to eLearning Platform'
    }
    
    # Show some statistics
    context['total_users'] = User.objects.filter(is_active=True).count()
    context['total_teachers'] = User.objects.filter(user_type='teacher', is_active=True).count()
    context['total_students'] = User.objects.filter(user_type='student', is_active=True).count()
    
    # Show recent public status updates
    context['recent_updates'] = StatusUpdate.objects.filter(
        is_public=True
    ).select_related('user')[:5]
    
    return render(request, 'home.html', context)
