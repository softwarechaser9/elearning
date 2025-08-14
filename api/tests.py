from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from accounts.models import UserProfile, StatusUpdate
from courses.models import Course, Enrollment, Feedback, Notification, CourseMaterial
from .serializers import (
    UserSerializer, CourseSerializer, EnrollmentSerializer, 
    FeedbackSerializer, NotificationSerializer
)
from decimal import Decimal

User = get_user_model()


class APIAuthenticationTest(APITestCase):
    """Test API authentication endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.register_url = reverse('api:register')
        self.login_url = reverse('api:login')
        self.logout_url = reverse('api:logout')
        
        self.user_data = {
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'testpass123',
            'password_confirm': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'user_type': 'student'
        }
    
    def test_user_registration(self):
        """Test user registration via API"""
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_user_registration_invalid_data(self):
        """Test user registration with invalid data"""
        invalid_data = self.user_data.copy()
        invalid_data['email'] = 'invalid-email'
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_user_login(self):
        """Test user login via API"""
        # Create user first
        User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        login_data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, login_data)
        if response.status_code != status.HTTP_200_OK:
            print(f"Login failed with status {response.status_code}")
            print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
    
    def test_user_login_invalid_credentials(self):
        """Test user login with invalid credentials"""
        login_data = {
            'username': 'nonexistent',
            'password': 'wrongpass'
        }
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_logout(self):
        """Test user logout via API"""
        # Create user and get token
        user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        token = Token.objects.create(user=user)
        
        # Set authentication
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token.key)
        
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Token should be deleted
        self.assertFalse(Token.objects.filter(key=token.key).exists())


class UserAPITest(APITestCase):
    """Test User API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            user_type='student'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
    
    def test_get_user_list(self):
        """Test getting user list"""
        url = reverse('api:user-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_user_detail(self):
        """Test getting user detail"""
        url = reverse('api:user-detail', kwargs={'pk': self.user.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
    
    def test_update_user_profile(self):
        """Test updating user profile"""
        url = reverse('api:user-detail', kwargs={'pk': self.user.pk})
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Updated')


class CourseAPITest(APITestCase):
    """Test Course API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            user_type='teacher'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            user_type='student'
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher,
            status='published'
        )
        
        # Create tokens
        self.teacher_token = Token.objects.create(user=self.teacher)
        self.student_token = Token.objects.create(user=self.student)
    
    def test_get_course_list(self):
        """Test getting course list"""
        url = reverse('api:course-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_course_detail(self):
        """Test getting course detail"""
        url = reverse('api:course-detail', kwargs={'pk': self.course.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Course')
    
    def test_create_course_as_teacher(self):
        """Test creating course as teacher"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.teacher_token.key)
        
        url = reverse('api:course-list')
        data = {
            'title': 'New Course',
            'description': 'New course description',
            'short_description': 'Brief course description',
            'category': 'Programming',
            'difficulty_level': 'beginner',
            'price': '99.99',
            'is_free': False,
            'max_students': 30,
            'status': 'published'
        }
        response = self.client.post(url, data)
        if response.status_code != status.HTTP_201_CREATED:
            print(f"Course creation failed with status {response.status_code}")
            print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Course.objects.filter(title='New Course').exists())
    
    def test_create_course_as_student_forbidden(self):
        """Test that students cannot create courses"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.student_token.key)
        
        url = reverse('api:course-list')
        data = {
            'title': 'New Course',
            'description': 'New course description'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_enroll_in_course(self):
        """Test enrolling in a course via API"""
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.student_token.key)
        
        url = reverse('api:course-enroll', kwargs={'course_id': self.course.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=self.course).exists()
        )


class EnrollmentAPITest(APITestCase):
    """Test Enrollment API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            user_type='teacher'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            user_type='student'
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher,
            status='published'
        )
        self.enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        
        self.student_token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.student_token.key)
    
    def test_get_student_enrollments(self):
        """Test getting student's enrollments"""
        url = reverse('api:enrollment-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_get_enrollment_detail(self):
        """Test getting enrollment detail"""
        url = reverse('api:enrollment-detail', kwargs={'pk': self.enrollment.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['course']['title'], 'Test Course')


class FeedbackAPITest(APITestCase):
    """Test Feedback API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            user_type='teacher'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            user_type='student'
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher,
            status='published'
        )
        
        self.student_token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.student_token.key)
    
    def test_create_feedback(self):
        """Test creating course feedback via API"""
        url = reverse('api:feedback-list')
        data = {
            'course': self.course.pk,
            'rating': 5,
            'title': 'Great Course',
            'content': 'This course was excellent!'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Feedback.objects.filter(student=self.student, course=self.course).exists()
        )
    
    def test_get_feedback_list(self):
        """Test getting feedback list"""
        # Create feedback first
        Feedback.objects.create(
            course=self.course,
            student=self.student,
            rating=4,
            title='Good Course',
            content='Nice course content'
        )
        
        url = reverse('api:feedback-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)


class APISerializerTest(TestCase):
    """Test API serializers"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            user_type='teacher'
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.user
        )
    
    def test_user_serializer(self):
        """Test UserSerializer"""
        serializer = UserSerializer(self.user)
        expected_fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                          'user_type', 'bio', 'profile_picture', 'phone_number', 'location',
                          'qualification', 'experience_years', 'is_verified',
                          'date_joined', 'is_active']
        self.assertEqual(set(serializer.data.keys()), set(expected_fields))
    
    def test_course_serializer(self):
        """Test CourseSerializer"""
        serializer = CourseSerializer(self.course)
        expected_fields = ['id', 'title', 'description', 'short_description', 'teacher', 
                          'category', 'difficulty_level', 'price', 'is_free', 'max_students',
                          'created_at', 'updated_at', 'status', 'enrollment_count']
        self.assertEqual(set(serializer.data.keys()), set(expected_fields))
        self.assertEqual(serializer.data['title'], 'Test Course')
    
    def test_enrollment_serializer(self):
        """Test EnrollmentSerializer"""
        student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            user_type='student'
        )
        enrollment = Enrollment.objects.create(
            student=student,
            course=self.course
        )
        
        serializer = EnrollmentSerializer(enrollment)
        self.assertEqual(serializer.data['student']['username'], 'student')
        self.assertEqual(serializer.data['course']['title'], 'Test Course')


class APIPermissionTest(APITestCase):
    """Test API permissions"""
    
    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            user_type='teacher'
        )
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            user_type='student'
        )
        self.course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher
        )
    
    def test_unauthenticated_access(self):
        """Test unauthenticated access to protected endpoints"""
        url = reverse('api:course-list')
        
        # GET should work (read-only)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # POST should require authentication
        data = {'title': 'New Course', 'description': 'Test'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_teacher_course_permissions(self):
        """Test teacher permissions for their own courses"""
        teacher_token = Token.objects.create(user=self.teacher)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + teacher_token.key)
        
        # Teacher should be able to update their own course
        url = reverse('api:course-detail', kwargs={'pk': self.course.pk})
        data = {'title': 'Updated Course Title'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_student_course_permissions(self):
        """Test student permissions for courses"""
        student_token = Token.objects.create(user=self.student)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + student_token.key)
        
        # Student should not be able to update courses
        url = reverse('api:course-detail', kwargs={'pk': self.course.pk})
        data = {'title': 'Hacked Course Title'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
