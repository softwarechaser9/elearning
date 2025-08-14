from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from courses.models import Course
from chat.models import ChatRoom, ChatMessage

User = get_user_model()


class Command(BaseCommand):
    help = 'Create test chat room and messages'

    def handle(self, *args, **options):
        # Check if we have users and courses
        teacher = User.objects.filter(user_type='teacher').first()
        student = User.objects.filter(user_type='student').first()
        
        if not teacher:
            self.stdout.write('No teacher found. Creating test teacher...')
            teacher = User.objects.create_user(
                username='testteacher',
                email='teacher@example.com',
                password='testpass123',
                user_type='teacher',
                first_name='Test',
                last_name='Teacher'
            )
        
        if not student:
            self.stdout.write('No student found. Creating test student...')
            student = User.objects.create_user(
                username='teststudent',
                email='student@example.com',
                password='testpass123',
                user_type='student',
                first_name='Test',
                last_name='Student'
            )
        
        # Get or create a course
        course = Course.objects.filter(teacher=teacher).first()
        if not course:
            self.stdout.write('No course found. Creating test course...')
            course = Course.objects.create(
                title='Test Course for Chat',
                short_description='Test course description',
                description='This is a test course for testing chat functionality.',
                teacher=teacher,
                price=0,
                is_free=True,
                status='published'
            )
        
        # Create or get chat room
        chat_room = ChatRoom.objects.filter(course=course).first()
        if not chat_room:
            self.stdout.write('Creating test chat room...')
            chat_room = ChatRoom.objects.create(
                name=f'{course.title} - General Chat',
                description='General discussion for the course',
                course=course,
                created_by=teacher
            )
        
        # Create some test messages
        if not ChatMessage.objects.filter(room=chat_room).exists():
            self.stdout.write('Creating test messages...')
            ChatMessage.objects.create(
                room=chat_room,
                user=teacher,
                content='Welcome to the chat room! Feel free to ask any questions about the course.'
            )
            ChatMessage.objects.create(
                room=chat_room,
                user=student,
                content='Thank you! I\'m excited to start learning.'
            )
            ChatMessage.objects.create(
                room=chat_room,
                user=teacher,
                content='Great! Let me know if you need any help with the course materials.'
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created test data!\n'
                f'Chat Room ID: {chat_room.id}\n'
                f'Chat Room Name: {chat_room.name}\n'
                f'Course: {course.title}\n'
                f'Teacher: {teacher.username}\n'
                f'Student: {student.username}\n'
                f'Messages: {ChatMessage.objects.filter(room=chat_room).count()}'
            )
        )
