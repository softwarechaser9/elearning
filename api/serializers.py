from rest_framework import serializers
from django.contrib.auth import get_user_model
from accounts.models import UserProfile, StatusUpdate
from courses.models import Course, CourseMaterial, Enrollment, Feedback, Notification

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 
                 'user_type', 'bio', 'profile_picture', 'phone_number', 'location',
                 'qualification', 'experience_years', 'is_verified',
                 'date_joined', 'is_active']
        read_only_fields = ['id', 'date_joined']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['user', 'website', 'linkedin', 'twitter', 
                 'email_notifications', 'course_notifications', 'marketing_notifications',
                 'profile_views', 'show_email', 'show_phone',
                 'created_at', 'updated_at', 'last_activity']
        read_only_fields = ['created_at', 'updated_at', 'last_activity', 'profile_views']


class StatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for StatusUpdate model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = StatusUpdate
        fields = ['id', 'user', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']


class CourseSerializer(serializers.ModelSerializer):
    """Serializer for Course model"""
    teacher = UserSerializer(read_only=True)
    enrollment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'short_description', 'teacher', 
                 'category', 'difficulty_level', 'price', 'is_free', 'max_students',
                 'created_at', 'updated_at', 'status', 'enrollment_count']
        read_only_fields = ['id', 'created_at', 'updated_at', 'enrollment_count']
    
    def get_enrollment_count(self, obj):
        return obj.enrollments.count()


class CourseMaterialSerializer(serializers.ModelSerializer):
    """Serializer for CourseMaterial model"""
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    
    class Meta:
        model = CourseMaterial
        fields = ['id', 'course', 'title', 'description', 'file', 
                 'material_type', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class EnrollmentSerializer(serializers.ModelSerializer):
    """Serializer for Enrollment model"""
    student = UserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'course', 'date_enrolled', 'is_active', 
                 'progress', 'date_completed', 'certificate_issued']
        read_only_fields = ['id', 'date_enrolled']


class FeedbackSerializer(serializers.ModelSerializer):
    """Serializer for Feedback model"""
    student = UserSerializer(read_only=True)
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    
    class Meta:
        model = Feedback
        fields = ['id', 'student', 'course', 'rating', 'title', 'content', 
                 'is_anonymous', 'is_approved', 'helpful_votes', 'created_at']
        read_only_fields = ['id', 'created_at', 'helpful_votes']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""
    recipient = UserSerializer(read_only=True)
    sender = UserSerializer(read_only=True)
    
    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'sender', 'notification_type', 'title', 
                 'message', 'course', 'is_read', 'is_important', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 
                 'first_name', 'last_name', 'user_type']
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords do not match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user
