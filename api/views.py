from rest_framework import generics, permissions, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend

from accounts.models import UserProfile, StatusUpdate
from courses.models import Course, CourseMaterial, Enrollment, Feedback, Notification
from .serializers import (
    UserSerializer, UserProfileSerializer, StatusUpdateSerializer,
    CourseSerializer, CourseMaterialSerializer, EnrollmentSerializer,
    FeedbackSerializer, NotificationSerializer, UserRegistrationSerializer
)

User = get_user_model()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners of an object to edit it."""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'student'):
            return obj.student == request.user
        elif hasattr(obj, 'teacher'):
            return obj.teacher == request.user
        return obj == request.user


class IsTeacherOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow teachers to create/edit courses."""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.user_type == 'teacher'


# Authentication Views
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    """Register a new user"""
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Login user and return token"""
    username = request.data.get('username')
    password = request.data.get('password')
    
    if username and password:
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'user': UserSerializer(user).data,
                'token': token.key
            })
        else:
            return Response({'error': 'Invalid credentials'}, 
                          status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response({'error': 'Username and password required'}, 
                       status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout user by deleting token"""
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Successfully logged out'})
    except:
        return Response({'error': 'Error logging out'}, 
                       status=status.HTTP_400_BAD_REQUEST)


# User Views
class UserListView(generics.ListAPIView):
    """List all users"""
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name', 'date_joined']
    ordering = ['username']  # Default ordering
    filterset_fields = ['user_type', 'is_active']


class UserDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update user details"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


class UserProfileListView(generics.ListCreateAPIView):
    """List and create user profiles"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserProfileDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete user profile"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


class StatusUpdateListView(generics.ListCreateAPIView):
    """List and create status updates"""
    queryset = StatusUpdate.objects.all().order_by('-created_at')
    serializer_class = StatusUpdateSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class StatusUpdateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete status update"""
    queryset = StatusUpdate.objects.all()
    serializer_class = StatusUpdateSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


# Course Views
class CourseListView(generics.ListCreateAPIView):
    """List and create courses"""
    queryset = Course.objects.filter(status='published')
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsTeacherOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter, DjangoFilterBackend]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'price', 'title']
    filterset_fields = ['teacher', 'price']
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete course"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]


class CourseMaterialListView(generics.ListCreateAPIView):
    """List and create course materials"""
    queryset = CourseMaterial.objects.all()
    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['course', 'material_type']
    
    def get_queryset(self):
        queryset = CourseMaterial.objects.all()
        course_id = self.request.query_params.get('course', None)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset


class CourseMaterialDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete course material"""
    queryset = CourseMaterial.objects.all()
    serializer_class = CourseMaterialSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


# Enrollment Views
class EnrollmentListView(generics.ListCreateAPIView):
    """List and create enrollments"""
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'course', 'is_active']
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
    
    def get_queryset(self):
        if self.request.user.user_type == 'student':
            return Enrollment.objects.filter(student=self.request.user)
        elif self.request.user.user_type == 'teacher':
            return Enrollment.objects.filter(course__teacher=self.request.user)
        return Enrollment.objects.all()


class EnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete enrollment"""
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


# Feedback Views
class FeedbackListView(generics.ListCreateAPIView):
    """List and create feedback"""
    queryset = Feedback.objects.all().order_by('-created_at')
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['course', 'rating']
    ordering_fields = ['created_at', 'rating']
    
    def perform_create(self, serializer):
        serializer.save(student=self.request.user)
    
    def get_queryset(self):
        queryset = Feedback.objects.all()
        course_id = self.request.query_params.get('course', None)
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset


class FeedbackDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete feedback"""
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]


# Notification Views
class NotificationListView(generics.ListCreateAPIView):
    """List and create notifications"""
    queryset = Notification.objects.all().order_by('-created_at')
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_read', 'notification_type']
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete notification"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(pk=pk, recipient=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Notification marked as read'})
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, 
                       status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def enroll_in_course(request, course_id):
    """Enroll user in a course"""
    try:
        course = Course.objects.get(pk=course_id)
        enrollment, created = Enrollment.objects.get_or_create(
            student=request.user,
            course=course
        )
        if created:
            # Create notification for successful enrollment
            Notification.objects.create(
                recipient=request.user,
                title=f"Enrolled in {course.title}",
                message=f"You have successfully enrolled in the course '{course.title}'.",
                notification_type='enrollment',
                course=course
            )
            return Response({
                'message': 'Successfully enrolled in course',
                'enrollment': EnrollmentSerializer(enrollment).data
            })
        else:
            return Response({'message': 'Already enrolled in this course'})
    except Course.DoesNotExist:
        return Response({'error': 'Course not found'}, 
                       status=status.HTTP_404_NOT_FOUND)
