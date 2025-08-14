from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token
from . import views

app_name = 'api'

urlpatterns = [
    # Authentication URLs
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    
    # User URLs
    path('users/', views.UserListView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # User Profile URLs
    path('profiles/', views.UserProfileListView.as_view(), name='profile-list'),
    path('profiles/<int:pk>/', views.UserProfileDetailView.as_view(), name='profile-detail'),
    
    # Status Update URLs
    path('status-updates/', views.StatusUpdateListView.as_view(), name='status-list'),
    path('status-updates/<int:pk>/', views.StatusUpdateDetailView.as_view(), name='status-detail'),
    
    # Course URLs
    path('courses/', views.CourseListView.as_view(), name='course-list'),
    path('courses/<int:pk>/', views.CourseDetailView.as_view(), name='course-detail'),
    path('courses/<int:course_id>/enroll/', views.enroll_in_course, name='course-enroll'),
    
    # Course Material URLs
    path('materials/', views.CourseMaterialListView.as_view(), name='material-list'),
    path('materials/<int:pk>/', views.CourseMaterialDetailView.as_view(), name='material-detail'),
    
    # Enrollment URLs
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment-list'),
    path('enrollments/<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment-detail'),
    
    # Feedback URLs
    path('feedback/', views.FeedbackListView.as_view(), name='feedback-list'),
    path('feedback/<int:pk>/', views.FeedbackDetailView.as_view(), name='feedback-detail'),
    
    # Notification URLs
    path('notifications/', views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
    path('notifications/<int:pk>/mark-read/', views.mark_notification_read, name='notification-mark-read'),
]
