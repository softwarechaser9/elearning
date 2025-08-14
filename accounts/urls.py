from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Profile URLs
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('profile-edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Status updates
    path('status/create/', views.create_status_update, name='create_status'),
    
    # User search (for teachers)
    path('search/', views.UserSearchView.as_view(), name='user_search'),
]
