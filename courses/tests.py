from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.text import slugify
from .models import Course, CourseMaterial, Enrollment, Feedback, Notification, MaterialCompletion, CourseCompletion
from .forms import CourseForm, FeedbackForm, CourseMaterialForm
import tempfile
from decimal import Decimal

User = get_user_model()


class CourseModelTest(TestCase):
    """Test cases for Course model"""
    
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
    
    def test_create_course(self):
        """Test creating a course"""
        course = Course.objects.create(
            title='Test Course',
            description='This is a test course',
            teacher=self.teacher,
            price=Decimal('99.99'),
            is_free=False,  # Set is_free to False since we have a price
            max_students=30
        )
        self.assertEqual(course.title, 'Test Course')
        self.assertEqual(course.teacher, self.teacher)
        self.assertFalse(course.is_free)
        self.assertEqual(course.price, Decimal('99.99'))
    
    def test_course_slug_generation(self):
        """Test automatic slug generation"""
        course = Course.objects.create(
            title='Test Course with Spaces',
            description='Test description',
            teacher=self.teacher
        )
        self.assertEqual(course.slug, 'test-course-with-spaces')
    
    def test_course_enrollment_count(self):
        """Test enrollment count property"""
        course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher,
            status='published'
        )
        
        # Initially should be 0
        self.assertEqual(course.enrollment_count, 0)
        
        # Create enrollment
        Enrollment.objects.create(student=self.student, course=course)
        course.refresh_from_db()
        self.assertEqual(course.enrollment_count, 1)
    
    def test_course_can_enroll(self):
        """Test can_enroll method"""
        course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher,
            status='published',
            max_students=1
        )
        
        # Student should be able to enroll
        can_enroll, message = course.can_enroll(self.student)
        self.assertTrue(can_enroll)
        
        # Enroll student
        Enrollment.objects.create(student=self.student, course=course)
        
        # Course should be full now
        can_enroll, message = course.can_enroll(self.student)
        self.assertFalse(can_enroll)
        self.assertIn('full', message.lower())
    
    def test_course_str_method(self):
        """Test course string representation"""
        course = Course.objects.create(
            title='Test Course',
            description='Test description',
            teacher=self.teacher
        )
        self.assertEqual(str(course), 'Test Course')


class EnrollmentModelTest(TestCase):
    """Test cases for Enrollment model"""
    
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
    
    def test_create_enrollment(self):
        """Test creating an enrollment"""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        self.assertEqual(enrollment.student, self.student)
        self.assertEqual(enrollment.course, self.course)
        self.assertTrue(enrollment.is_active)
        self.assertEqual(enrollment.progress, 0)
    
    def test_enrollment_progress_calculation(self):
        """Test progress calculation"""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        
        # Create course materials
        material1 = CourseMaterial.objects.create(
            course=self.course,
            title='Material 1',
            description='Test material'
        )
        material2 = CourseMaterial.objects.create(
            course=self.course,
            title='Material 2',
            description='Test material'
        )
        
        # No materials completed
        progress = enrollment.calculate_progress()
        self.assertEqual(progress, 0)
        
        # Complete one material
        MaterialCompletion.objects.create(
            student=self.student,
            material=material1
        )
        progress = enrollment.calculate_progress()
        self.assertEqual(progress, 50.0)
        
        # Complete all materials
        MaterialCompletion.objects.create(
            student=self.student,
            material=material2
        )
        progress = enrollment.calculate_progress()
        self.assertEqual(progress, 100.0)
    
    def test_enrollment_str_method(self):
        """Test enrollment string representation"""
        enrollment = Enrollment.objects.create(
            student=self.student,
            course=self.course
        )
        expected_str = f"{self.student.username} enrolled in {self.course.title}"
        self.assertEqual(str(enrollment), expected_str)


class FeedbackModelTest(TestCase):
    """Test cases for Feedback model"""
    
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
    
    def test_create_feedback(self):
        """Test creating course feedback"""
        feedback = Feedback.objects.create(
            course=self.course,
            student=self.student,
            rating=5,
            title='Great Course',
            content='This course was excellent!'
        )
        self.assertEqual(feedback.course, self.course)
        self.assertEqual(feedback.student, self.student)
        self.assertEqual(feedback.rating, 5)
        self.assertTrue(feedback.is_approved)
    
    def test_feedback_star_display(self):
        """Test star display property"""
        feedback = Feedback.objects.create(
            course=self.course,
            student=self.student,
            rating=3,
            title='Average Course',
            content='It was okay.'
        )
        self.assertEqual(feedback.star_display, '★★★☆☆')


class CourseViewsTest(TestCase):
    """Test cases for Course views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
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
    
    def test_course_list_view(self):
        """Test course list view"""
        response = self.client.get(reverse('courses:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
    
    def test_course_detail_view(self):
        """Test course detail view"""
        response = self.client.get(
            reverse('courses:detail', kwargs={'slug': self.course.slug})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.course.title)
        self.assertContains(response, self.course.description)
    
    def test_course_create_requires_teacher(self):
        """Test that course creation requires teacher permissions"""
        # Test without login
        response = self.client.get(reverse('courses:create'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test with student login
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('courses:create'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Test with teacher login
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('courses:create'))
        self.assertEqual(response.status_code, 200)
    
    def test_enrollment_view(self):
        """Test course enrollment"""
        self.client.login(username='student', password='testpass123')
        response = self.client.post(
            reverse('courses:enroll', kwargs={'slug': self.course.slug})
        )
        self.assertEqual(response.status_code, 302)  # Redirect after enrollment
        self.assertTrue(
            Enrollment.objects.filter(student=self.student, course=self.course).exists()
        )
    
    def test_teacher_dashboard_requires_teacher(self):
        """Test teacher dashboard requires teacher permissions"""
        # Test without login
        response = self.client.get(reverse('courses:teacher_dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        # Test with student
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('courses:teacher_dashboard'))
        self.assertEqual(response.status_code, 403)  # Forbidden
        
        # Test with teacher
        self.client.login(username='teacher', password='testpass123')
        response = self.client.get(reverse('courses:teacher_dashboard'))
        self.assertEqual(response.status_code, 200)


class CourseFormsTest(TestCase):
    """Test cases for Course forms"""
    
    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            username='teacher',
            email='teacher@test.com',
            password='testpass123',
            user_type='teacher'
        )
    
    def test_course_form_valid(self):
        """Test valid course form"""
        form_data = {
            'title': 'Test Course',
            'description': 'This is a test course description',
            'short_description': 'Short description',
            'category': 'Programming',
            'difficulty_level': 'beginner',
            'max_students': 30,
            'is_free': True,
            'price': 0.00,
            'prerequisites': '',
            'learning_outcomes': '',
            'tags': '',
            'meta_description': '',
            'status': 'draft'
        }
        form = CourseForm(data=form_data)
        if not form.is_valid():
            print("Form errors:", form.errors)
        self.assertTrue(form.is_valid())
    
    def test_feedback_form_valid(self):
        """Test valid feedback form"""
        form_data = {
            'rating': 5,
            'title': 'Great Course',
            'content': 'This course was excellent and very helpful!'
        }
        form = FeedbackForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_feedback_form_invalid_rating(self):
        """Test feedback form with invalid rating"""
        form_data = {
            'rating': 6,  # Invalid rating (should be 1-5)
            'title': 'Test',
            'content': 'Test content'
        }
        form = FeedbackForm(data=form_data)
        self.assertFalse(form.is_valid())
