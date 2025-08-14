from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # Private chat URLs only
    path('', views.private_chat_list, name='private_list'),  # Changed default to private chat
    path('private/', views.private_chat_list, name='private_list'),
    path('private/<int:user_id>/', views.private_chat_detail, name='private_detail'),
    path('users/search/', views.user_search, name='user_search'),
    path('start-chat/<int:user_id>/', views.start_private_chat, name='start_private_chat'),
]
