from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from .models import PrivateChat, PrivateMessage, ChatRoom, ChatMessage, ChatRoomMembership
from courses.models import Course

User = get_user_model()


class PrivateChatModelTest(TestCase):
    """Test cases for PrivateChat model"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
    
    def test_create_private_chat(self):
        """Test creating a private chat"""
        chat = PrivateChat.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
        self.assertEqual(chat.participant1, self.user1)
        self.assertEqual(chat.participant2, self.user2)
    
    def test_private_chat_get_other_user(self):
        """Test get_other_user method"""
        chat = PrivateChat.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
        
        # Note: The PrivateChat model doesn't have get_other_user method in the current implementation
        # Let's test the participants property instead
        participants = chat.get_participants
        self.assertIn(self.user1, participants)
        self.assertIn(self.user2, participants)
    
    def test_private_chat_str_method(self):
        """Test private chat string representation"""
        chat = PrivateChat.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
        expected_str = f"Private chat between {self.user1.username} and {self.user2.username}"
        self.assertEqual(str(chat), expected_str)


class PrivateMessageModelTest(TestCase):
    """Test cases for PrivateMessage model"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
        self.chat = PrivateChat.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
    
    def test_create_private_message(self):
        """Test creating a private message"""
        message = PrivateMessage.objects.create(
            chat=self.chat,
            sender=self.user1,
            content='Hello, this is a test message!'
        )
        self.assertEqual(message.chat, self.chat)
        self.assertEqual(message.sender, self.user1)
        self.assertEqual(message.content, 'Hello, this is a test message!')
        self.assertFalse(message.is_read)
        self.assertEqual(message.message_type, 'text')
    
    def test_private_message_str_method(self):
        """Test private message string representation"""
        message = PrivateMessage.objects.create(
            chat=self.chat,
            sender=self.user1,
            content='Test message'
        )
        expected_str = f"{self.user1.username}: Test message"
        self.assertEqual(str(message), expected_str)


class ChatRoomModelTest(TestCase):
    """Test cases for ChatRoom model"""
    
    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            user_type='teacher'
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher
        )
    
    def test_create_chat_room(self):
        """Test creating a chat room"""
        room = ChatRoom.objects.create(
            name='Course Discussion',
            description='Discussion for the course',
            course=self.course,
            created_by=self.teacher
        )
        self.assertEqual(room.name, 'Course Discussion')
        self.assertEqual(room.course, self.course)
        self.assertEqual(room.created_by, self.teacher)
        self.assertTrue(room.is_active)
    
    def test_chat_room_str_method(self):
        """Test chat room string representation"""
        room = ChatRoom.objects.create(
            name='Course Discussion',
            course=self.course,
            created_by=self.teacher
        )
        expected_str = f"Course Discussion - {self.course.title}"
        self.assertEqual(str(room), expected_str)


class ChatViewsTest(TestCase):
    """Test cases for Chat views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123',
            user_type='student'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123',
            user_type='teacher'
        )
    
    def test_private_chat_list_requires_login(self):
        """Test that private chat list requires login"""
        response = self.client.get(reverse('chat:private_list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_private_chat_list_authenticated(self):
        """Test private chat list for authenticated user"""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('chat:private_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Private Chats')
    
    def test_private_chat_detail_requires_login(self):
        """Test that private chat detail requires login"""
        response = self.client.get(
            reverse('chat:private_detail', kwargs={'user_id': self.user2.id})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_private_chat_detail_authenticated(self):
        """Test private chat detail for authenticated user"""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(
            reverse('chat:private_detail', kwargs={'user_id': self.user2.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.user2.get_full_name())
    
    def test_user_search_requires_login(self):
        """Test that user search requires login"""
        response = self.client.get(reverse('chat:user_search'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_user_search_authenticated(self):
        """Test user search for authenticated user"""
        self.client.login(username='user1', password='testpass123')
        response = self.client.get(reverse('chat:user_search'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Find Users to Chat With')
    
    def test_start_private_chat(self):
        """Test starting a private chat"""
        self.client.login(username='user1', password='testpass123')
        response = self.client.post(
            reverse('chat:start_private_chat', kwargs={'user_id': self.user2.id})
        )
        self.assertEqual(response.status_code, 302)  # Redirect to chat detail
        
        # Check if chat was created
        self.assertTrue(
            PrivateChat.objects.filter(
                participant1=self.user1, participant2=self.user2
            ).exists() or 
            PrivateChat.objects.filter(
                participant1=self.user2, participant2=self.user1
            ).exists()
        )


class ChatIntegrationTest(TestCase):
    """Integration tests for chat functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@test.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@test.com',
            password='testpass123'
        )
    
    def test_chat_flow(self):
        """Test complete chat flow"""
        # Create private chat
        chat = PrivateChat.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
        
        # Send message
        message = PrivateMessage.objects.create(
            chat=chat,
            sender=self.user1,
            content='Hello! How are you?'
        )
        
        # Check message was created
        self.assertTrue(
            PrivateMessage.objects.filter(chat=chat, sender=self.user1).exists()
        )
        
        # Check chat has the message
        self.assertEqual(chat.messages.count(), 1)
        
        # Check last message
        last_message = chat.messages.order_by('-created_at').first()
        self.assertEqual(last_message.content, 'Hello! How are you?')
    
    def test_multiple_messages_ordering(self):
        """Test message ordering in chat"""
        chat = PrivateChat.objects.create(
            participant1=self.user1,
            participant2=self.user2
        )
        
        # Create messages with different times
        message1 = PrivateMessage.objects.create(
            chat=chat,
            sender=self.user1,
            content='First message'
        )
        
        message2 = PrivateMessage.objects.create(
            chat=chat,
            sender=self.user2,
            content='Second message'
        )
        
        # Check ordering (should be by created_at)
        messages = list(chat.messages.all())
        self.assertEqual(messages[0], message1)
        self.assertEqual(messages[1], message2)
        
        # Check latest message
        latest = chat.messages.order_by('-created_at').first()
        self.assertEqual(latest, message2)
