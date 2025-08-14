from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Course listing and detail
    path('', views.CourseListView.as_view(), name='list'),
    path('course/<slug:slug>/', views.CourseDetailView.as_view(), name='detail'),
    
    # Course management (teachers)
    path('create/', views.CourseCreateView.as_view(), name='create'),
    path('course/<slug:slug>/edit/', views.CourseUpdateView.as_view(), name='edit'),
    path('course/<slug:slug>/delete/', views.CourseDeleteView.as_view(), name='delete'),
    path('teacher-dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('manage-students/', views.select_course_for_management, name='select_course_management'),
    
    # Course enrollment
    path('course/<slug:slug>/enroll/', views.enroll_course, name='enroll'),
    path('course/<slug:slug>/unenroll/', views.unenroll_course, name='unenroll'),
    
    # User's courses
    path('my-courses/', views.MyCoursesView.as_view(), name='my_courses'),
    
    # Course feedback
    path('course/<slug:slug>/feedback/', views.submit_feedback, name='submit_feedback'),
    
    # Course materials management (teachers)
    path('course/<slug:slug>/materials/', views.CourseMaterialListView.as_view(), name='materials'),
    path('course/<slug:slug>/materials/add/', views.CourseMaterialCreateView.as_view(), name='add_material'),
    path('material/<int:pk>/edit/', views.CourseMaterialUpdateView.as_view(), name='edit_material'),
    path('material/<int:pk>/delete/', views.CourseMaterialDeleteView.as_view(), name='delete_material'),
    
    # Material completion (students)
    path('material/<int:material_id>/complete/', views.mark_material_complete, name='mark_material_complete'),
    path('course/<slug:slug>/progress/', views.course_progress, name='course_progress'),
    
    # Student management (teachers)
    path('course/<slug:slug>/students/', views.manage_course_students, name='manage_students'),
    path('course/<slug:slug>/block/<int:student_id>/', views.block_student, name='block_student'),
    path('course/<slug:slug>/unblock/<int:student_id>/', views.unblock_student, name='unblock_student'),
    
    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
]
