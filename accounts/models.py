from django.contrib.auth.models import AbstractUser
from django.db import models
from django.urls import reverse
from PIL import Image


class User(AbstractUser):
    """Custom user model with additional fields for students and teachers"""
    
    USER_TYPE_CHOICES = [
        ('student', 'Student'),
        ('teacher', 'Teacher'),
    ]
    
    # Basic profile information
    email = models.EmailField(unique=True)
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='student')
    bio = models.TextField(max_length=500, blank=True, help_text="Tell us about yourself")
    profile_picture = models.ImageField(
        upload_to='profiles/', 
        default='profiles/default.jpg',
        help_text="Upload your profile picture"
    )
    phone_number = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=100, blank=True)
    
    # Professional information (mainly for teachers)
    qualification = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(
        null=True, 
        blank=True,
        help_text="Years of teaching experience (for teachers)"
    )
    
    # Account settings
    is_verified = models.BooleanField(default=False)
    date_updated = models.DateTimeField(auto_now=True)
    
    # Make email the unique identifier
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    
    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"
    
    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'username': self.username})
    
    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip() or self.username
    
    def save(self, *args, **kwargs):
        """Override save to resize profile pictures"""
        super().save(*args, **kwargs)
        
        if self.profile_picture:
            try:
                img = Image.open(self.profile_picture.path)
                if img.height > 300 or img.width > 300:
                    output_size = (300, 300)
                    img.thumbnail(output_size)
                    img.save(self.profile_picture.path)
            except Exception:
                pass  # Handle cases where image processing fails
    
    @property
    def is_teacher(self):
        """Check if user is a teacher"""
        return self.user_type == 'teacher'
    
    @property
    def is_student(self):
        """Check if user is a student"""
        return self.user_type == 'student'
    
    def get_courses_as_teacher(self):
        """Get courses where this user is the teacher"""
        if self.is_teacher:
            return self.taught_courses.all()
        return None
    
    def get_enrolled_courses(self):
        """Get courses where this user is enrolled as student"""
        if self.is_student:
            return self.enrollments.filter(is_active=True).select_related('course')
        return None


class StatusUpdate(models.Model):
    """Model for user status updates"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='status_updates')
    content = models.TextField(max_length=280, help_text="What's on your mind?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True, help_text="Make this visible to other users")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Status Update'
        verbose_name_plural = 'Status Updates'
    
    def __str__(self):
        return f"{self.user.username}: {self.content[:50]}..."
    
    def get_absolute_url(self):
        return reverse('accounts:profile', kwargs={'username': self.user.username})


class UserProfile(models.Model):
    """Extended profile information for users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Social links
    website = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    
    # Preferences
    email_notifications = models.BooleanField(default=True)
    course_notifications = models.BooleanField(default=True)
    marketing_notifications = models.BooleanField(default=False)
    
    # Statistics
    profile_views = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(auto_now=True)
    
    # Privacy settings
    show_email = models.BooleanField(default=False)
    show_phone = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
