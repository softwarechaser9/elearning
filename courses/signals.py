from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import CourseMaterial, Enrollment, Notification

User = get_user_model()
channel_layer = get_channel_layer()


@receiver(post_save, sender=CourseMaterial)
def notify_students_new_material(sender, instance, created, **kwargs):
    """
    Notify all enrolled students when a new material is added to their course
    """
    if created:  # Only when a new material is created, not updated
        course = instance.course
        
        # Get all active enrolled students for this course
        enrolled_students = User.objects.filter(
            enrollments__course=course,
            enrollments__is_active=True,
            enrollments__is_blocked=False
        )
        
        # Create notifications for all enrolled students
        notifications = []
        for student in enrolled_students:
            notification = Notification(
                recipient=student,
                sender=course.teacher,
                notification_type='material',
                title=f'New material added to "{course.title}"',
                message=f'"{instance.title}" has been added to your course "{course.title}". Check it out now!',
                course=course,
                is_important=True
            )
            notifications.append(notification)
        
        # Bulk create all notifications for better performance
        if notifications:
            Notification.objects.bulk_create(notifications)
            
            # Send real-time notifications to each student
            for notification in notifications:
                user_group = f"notifications_{notification.recipient.id}"
                async_to_sync(channel_layer.group_send)(
                    user_group,
                    {
                        'type': 'notification_message',
                        'data': {
                            'id': None,  # Will be set after saving
                            'title': notification.title,
                            'message': notification.message,
                            'type': notification.notification_type,
                            'is_important': notification.is_important,
                            'created_at': 'just now'
                        }
                    }
                )


@receiver(post_save, sender=Enrollment)
def notify_teacher_new_enrollment(sender, instance, created, **kwargs):
    """
    Notify the teacher when a new student enrolls in their course
    """
    if created and instance.is_active:  # Only for new active enrollments
        course = instance.course
        student = instance.student
        teacher = course.teacher
        
        # Create notification for the teacher
        notification = Notification.objects.create(
            recipient=teacher,
            sender=student,
            notification_type='enrollment',
            title=f'New student enrolled in "{course.title}"',
            message=f'{student.get_full_name() or student.username} has enrolled in your course "{course.title}". You now have {course.enrollment_count} students.',
            course=course,
            is_important=True
        )
        
        # Send real-time notification to teacher
        teacher_group = f"notifications_{teacher.id}"
        async_to_sync(channel_layer.group_send)(
            teacher_group,
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
