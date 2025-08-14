from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import User, StatusUpdate, UserProfile
from .forms import CustomUserCreationForm, UserProfileForm
import tempfile
from PIL import Image

User = get_user_model()


class UserModelTest(TestCase):
    """Test cases for User model"""
    
    def setUp(self):
        """Set up test data"""
        self.student_data = {
            'username': 'teststudent',
            'email': 'student@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Student',
            'user_type': 'student'
        }
        
        self.teacher_data = {
            'username': 'testteacher',
            'email': 'teacher@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'Teacher',
            'user_type': 'teacher'
        }
    
    def test_create_student(self):
        """Test creating a student user"""
        user = User.objects.create_user(**self.student_data)
        self.assertEqual(user.username, 'teststudent')
        self.assertEqual(user.email, 'student@test.com')
        self.assertEqual(user.user_type, 'student')
        self.assertTrue(user.is_student)
        self.assertFalse(user.is_teacher)
    
    def test_create_teacher(self):
        """Test creating a teacher user"""
        user = User.objects.create_user(**self.teacher_data)
        self.assertEqual(user.username, 'testteacher')
        self.assertEqual(user.email, 'teacher@test.com')
        self.assertEqual(user.user_type, 'teacher')
        self.assertTrue(user.is_teacher)
        self.assertFalse(user.is_student)
    
    def test_get_full_name(self):
        """Test get_full_name method"""
        user = User.objects.create_user(**self.student_data)
        self.assertEqual(user.get_full_name(), 'Test Student')
        
        # Test with no first/last name
        user_no_name = User.objects.create_user(
            username='noname',
            email='noname@test.com',
            password='testpass123'
        )
        self.assertEqual(user_no_name.get_full_name(), 'noname')
    
    def test_str_method(self):
        """Test string representation of User"""
        user = User.objects.create_user(**self.student_data)
        expected_str = f"{user.username} ({user.get_user_type_display()})"
        self.assertEqual(str(user), expected_str)


class UserViewsTest(TestCase):
    """Test cases for User views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.student = User.objects.create_user(
            username='teststudent',
            email='student@test.com',
            password='testpass123',
            user_type='student'
        )
        self.teacher = User.objects.create_user(
            username='testteacher',
            email='teacher@test.com',
            password='testpass123',
            user_type='teacher'
        )
    
    def test_register_view_get(self):
        """Test GET request to register view"""
        response = self.client.get(reverse('accounts:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
    
    def test_register_view_post_valid(self):
        """Test POST request to register view with valid data"""
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'New',
            'last_name': 'User',
            'user_type': 'student'
        }
        response = self.client.post(reverse('accounts:register'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        self.assertTrue(User.objects.filter(username='newuser').exists())
    
    def test_login_view(self):
        """Test login view"""
        response = self.client.post(reverse('accounts:login'), {
            'username': 'teststudent',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after login
    
    def test_profile_view(self):
        """Test profile view"""
        response = self.client.get(
            reverse('accounts:profile', kwargs={'username': self.student.username})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.username)
    
    def test_profile_update_requires_login(self):
        """Test that profile update requires login"""
        response = self.client.get(reverse('accounts:profile_edit'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class StatusUpdateModelTest(TestCase):
    """Test cases for StatusUpdate model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_create_status_update(self):
        """Test creating a status update"""
        status = StatusUpdate.objects.create(
            user=self.user,
            content='This is a test status update'
        )
        self.assertEqual(status.user, self.user)
        self.assertEqual(status.content, 'This is a test status update')
        self.assertTrue(status.is_public)
    
    def test_status_update_str(self):
        """Test string representation of StatusUpdate"""
        status = StatusUpdate.objects.create(
            user=self.user,
            content='Test content'
        )
        # The model's __str__ method returns content[:50] + "..."
        expected_str = f"{self.user.username}: Test content..."
        self.assertEqual(str(status), expected_str)


class UserFormsTest(TestCase):
    """Test cases for User forms"""
    
    def test_user_creation_form_valid(self):
        """Test valid user creation form"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'student'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_user_creation_form_password_mismatch(self):
        """Test user creation form with password mismatch"""
        form_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password1': 'testpass123',
            'password2': 'differentpass',
            'user_type': 'student'
        }
        form = CustomUserCreationForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_user_profile_form(self):
        """Test user profile form"""
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@test.com',  # Use different email to avoid conflicts
            'bio': 'Updated bio',
            'phone_number': '',
            'location': '',
            'qualification': '',
            'experience_years': None
        }
        form = UserProfileForm(data=form_data, instance=user)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())
