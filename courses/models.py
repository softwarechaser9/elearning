from django.db import models
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import os

User = get_user_model()


def course_image_upload_path(instance, filename):
    """Generate upload path for course images"""
    return f'courses/{instance.slug}/{filename}'


def course_material_upload_path(instance, filename):
    """Generate upload path for course materials"""
    return f'courses/{instance.course.slug}/materials/{filename}'


class Course(models.Model):
    """Model for courses created by teachers"""
    
    DIFFICULTY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]
    
    # Basic course information
    title = models.CharField(max_length=200, help_text="Course title")
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(help_text="Detailed course description")
    short_description = models.CharField(
        max_length=300, 
        help_text="Brief description shown in course listings"
    )
    
    # Course metadata
    teacher = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='taught_courses',
        limit_choices_to={'user_type': 'teacher'}
    )
    category = models.CharField(max_length=100, blank=True)
    difficulty_level = models.CharField(
        max_length=20, 
        choices=DIFFICULTY_CHOICES, 
        default='beginner'
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='draft'
    )
    
    # Course media
    course_image = models.ImageField(
        upload_to=course_image_upload_path, 
        blank=True, 
        help_text="Course thumbnail image"
    )
    
    # Course settings
    max_students = models.PositiveIntegerField(
        default=50, 
        validators=[MinValueValidator(1), MaxValueValidator(500)],
        help_text="Maximum number of students that can enroll"
    )
    is_free = models.BooleanField(default=True, help_text="Is this course free?")
    price = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=0.00,
        help_text="Course price (if not free)"
    )
    
    # Requirements and learning outcomes
    prerequisites = models.TextField(
        blank=True, 
        help_text="What students should know before taking this course"
    )
    learning_outcomes = models.TextField(
        blank=True, 
        help_text="What students will learn from this course"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # SEO fields
    meta_description = models.CharField(max_length=160, blank=True)
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['teacher', '-created_at']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('courses:detail', kwargs={'slug': self.slug})
    
    @property
    def is_published(self):
        return self.status == 'published'
    
    @property
    def enrollment_count(self):
        return self.enrollments.filter(is_active=True).count()
    
    @property
    def is_full(self):
        return self.enrollment_count >= self.max_students
    
    @property
    def average_rating(self):
        feedbacks = self.feedbacks.all()
        if feedbacks:
            return sum(f.rating for f in feedbacks) / len(feedbacks)
        return 0
    
    def can_enroll(self, user):
        """Check if a user can enroll in this course"""
        if not user.is_authenticated or not user.is_student:
            return False, "Only students can enroll"
        
        if self.is_full:
            return False, "Course is full"
        
        if not self.is_published:
            return False, "Course is not available"
        
        # Check if student is blocked
        existing_enrollment = self.enrollments.filter(student=user).first()
        if existing_enrollment and existing_enrollment.is_blocked:
            return False, "You are blocked from this course"
        
        if self.enrollments.filter(student=user, is_active=True).exists():
            return False, "Already enrolled"
        
        return True, "Can enroll"
    
    def save(self, *args, **kwargs):
        """Override save to generate slug from title"""
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            
            # Ensure unique slug
            while Course.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = slug
        
        super().save(*args, **kwargs)


class CourseMaterial(models.Model):
    """Model for course materials uploaded by teachers"""
    
    MATERIAL_TYPES = [
        ('pdf', 'PDF Document'),
        ('video', 'Video'),
        ('image', 'Image'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('link', 'External Link'),
        ('other', 'Other'),
    ]
    
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='materials'
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # File or link
    file = models.FileField(
        upload_to=course_material_upload_path, 
        blank=True,
        help_text="Upload a file (PDF, video, audio, etc.)"
    )
    external_link = models.URLField(
        blank=True, 
        help_text="External link (YouTube, Google Drive, etc.)"
    )
    
    material_type = models.CharField(
        max_length=20, 
        choices=MATERIAL_TYPES, 
        default='document'
    )
    
    # Organization
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    is_downloadable = models.BooleanField(
        default=True, 
        help_text="Allow students to download this material"
    )
    is_public = models.BooleanField(
        default=False, 
        help_text="Make this material public (visible without enrollment)"
    )
    
    # Metadata
    file_size = models.PositiveIntegerField(null=True, blank=True, help_text="File size in bytes")
    duration = models.CharField(max_length=20, blank=True, help_text="Duration for video/audio")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Course Material'
        verbose_name_plural = 'Course Materials'
    
    def __str__(self):
        return f"{self.course.title} - {self.title}"
    
    @property
    def file_extension(self):
        if self.file:
            return os.path.splitext(self.file.name)[1].lower()
        return ''
    
    @property
    def formatted_file_size(self):
        if not self.file_size:
            return ''
        
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"


class Enrollment(models.Model):
    """Model for student enrollments in courses"""
    
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='enrollments',
        limit_choices_to={'user_type': 'student'}
    )
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    
    # Enrollment details
    date_enrolled = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_blocked = models.BooleanField(
        default=False, 
        help_text="Teacher blocked this student from the course"
    )
    progress = models.PositiveIntegerField(
        default=0, 
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Course completion percentage"
    )
    
    # Completion tracking
    date_completed = models.DateTimeField(null=True, blank=True)
    certificate_issued = models.BooleanField(default=False)
    
    # Notes
    notes = models.TextField(blank=True, help_text="Private notes for this enrollment")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-date_enrolled']
        verbose_name = 'Enrollment'
        verbose_name_plural = 'Enrollments'
        indexes = [
            models.Index(fields=['student', '-date_enrolled']),
            models.Index(fields=['course', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.student.username} enrolled in {self.course.title}"
    
    @property
    def is_completed(self):
        return self.progress >= 100
    
    def calculate_progress(self):
        """Calculate progress based on completed materials"""
        total_materials = self.course.materials.count()
        if total_materials == 0:
            return 0
        
        completed_materials = MaterialCompletion.objects.filter(
            student=self.student,
            material__course=self.course
        ).count()
        
        return round((completed_materials / total_materials) * 100, 1)
    
    def update_progress(self):
        """Update the progress field and check for completion"""
        from django.utils import timezone
        
        self.progress = self.calculate_progress()
        
        # Mark as completed if progress reaches 100%
        if self.progress >= 100 and not self.date_completed:
            self.date_completed = timezone.now()
            # Create course completion record
            CourseCompletion.objects.get_or_create(
                student=self.student,
                course=self.course,
                defaults={'completion_percentage': self.progress}
            )
        
        self.save()
        return self.progress
    
    @property
    def duration_enrolled(self):
        from django.utils import timezone
        if self.date_completed:
            return self.date_completed - self.date_enrolled
        return timezone.now() - self.date_enrolled


class Feedback(models.Model):
    """Model for course feedback from students"""
    
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        related_name='feedbacks'
    )
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='course_feedbacks',
        limit_choices_to={'user_type': 'student'}
    )
    
    # Feedback content
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Rating from 1 to 5 stars"
    )
    title = models.CharField(max_length=200, help_text="Feedback title")
    content = models.TextField(help_text="Detailed feedback")
    
    # Feedback metadata
    is_anonymous = models.BooleanField(
        default=False, 
        help_text="Hide your name from this feedback"
    )
    is_approved = models.BooleanField(
        default=True, 
        help_text="Is this feedback approved for display?"
    )
    
    # Helpful votes (other students can vote if feedback was helpful)
    helpful_votes = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('course', 'student')
        ordering = ['-created_at']
        verbose_name = 'Course Feedback'
        verbose_name_plural = 'Course Feedbacks'
        indexes = [
            models.Index(fields=['course', '-created_at']),
            models.Index(fields=['rating', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.student.username} - {self.course.title} ({self.rating}★)"
    
    @property
    def star_display(self):
        return '★' * self.rating + '☆' * (5 - self.rating)


class Notification(models.Model):
    """Model for notifications to users"""
    
    NOTIFICATION_TYPES = [
        ('enrollment', 'New Enrollment'),
        ('material', 'New Material Added'),
        ('feedback', 'New Feedback'),
        ('announcement', 'Course Announcement'),
        ('reminder', 'Reminder'),
        ('system', 'System Notification'),
    ]
    
    recipient = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='notifications'
    )
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_notifications',
        null=True, 
        blank=True
    )
    
    # Notification content
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Related objects (optional)
    course = models.ForeignKey(
        Course, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True
    )
    
    # Status
    is_read = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"


class MaterialCompletion(models.Model):
    """Track which materials a student has completed"""
    
    student = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='material_completions',
        limit_choices_to={'user_type': 'student'}
    )
    material = models.ForeignKey(
        'CourseMaterial',
        on_delete=models.CASCADE,
        related_name='completions'
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['student', 'material']
        verbose_name = 'Material Completion'
        verbose_name_plural = 'Material Completions'
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.student.username} completed {self.material.title}"


class CourseCompletion(models.Model):
    """Track course completions by students"""
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='course_completions',
        limit_choices_to={'user_type': 'student'}
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='completions'
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    completion_percentage = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        default=100.0
    )
    
    class Meta:
        unique_together = ['student', 'course']
        verbose_name = 'Course Completion'
        verbose_name_plural = 'Course Completions'
        ordering = ['-completed_at']
    
    def __str__(self):
        return f"{self.student.username} completed {self.course.title}"
