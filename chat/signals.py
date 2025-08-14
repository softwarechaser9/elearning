from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import PrivateMessage
from courses.models import Notification

User = get_user_model()
channel_layer = get_channel_layer()


# Removed course chat room notification signal since we're removing course chat rooms


@receiver(post_save, sender=PrivateMessage)
def notify_private_message(sender, instance, created, **kwargs):
    """
    Notify the recipient of a private message
    """
    if created:
        chat = instance.chat
        sender_user = instance.sender
        
        # Get the recipient (the other participant in the chat)
        recipient = chat.participant2 if sender_user == chat.participant1 else chat.participant1
        
        # Create notification for the recipient
        notification = Notification.objects.create(
            recipient=recipient,
            sender=sender_user,
            notification_type='system',
            title=f'New private message from {sender_user.get_full_name() or sender_user.username}',
            message=f'{sender_user.get_full_name() or sender_user.username} sent you a message: "{instance.content[:50]}{"..." if len(instance.content) > 50 else ""}"',
            is_important=False
        )
        
        # Send real-time notification to recipient
        recipient_group = f"notifications_{recipient.id}"
        async_to_sync(channel_layer.group_send)(
            recipient_group,
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
