from django.urls import path
from . import consumers
from courses.consumers import NotificationConsumer

# WebSocket URL patterns
websocket_urlpatterns = [
    # Only private chat and notifications WebSocket
    path('ws/chat/private/<int:user_id>/', consumers.PrivateChatConsumer.as_asgi()),
    path('ws/notifications/', NotificationConsumer.as_asgi()),
]
