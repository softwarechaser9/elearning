from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.utils import timezone
from .models import ChatRoom, ChatMessage, PrivateChat, PrivateMessage, ChatRoomMembership
from courses.models import Course, Enrollment

User = get_user_model()


@login_required
def chat_room_list(request):
    """List all chat rooms for the user's enrolled courses"""
    if request.user.user_type == 'student':
        # Get chat rooms for courses the student is enrolled in
        enrolled_courses = Course.objects.filter(
            enrollments__student=request.user,
            enrollments__is_active=True
        )
        chat_rooms = ChatRoom.objects.filter(
            course__in=enrolled_courses,
            is_active=True
        ).select_related('course', 'created_by')
    elif request.user.user_type == 'teacher':
        # Get chat rooms for courses the teacher teaches
        chat_rooms = ChatRoom.objects.filter(
            course__teacher=request.user,
            is_active=True
        ).select_related('course', 'created_by')
    else:
        chat_rooms = ChatRoom.objects.none()
    
    return render(request, 'chat/room_list.html', {
        'chat_rooms': chat_rooms
    })


@login_required
def chat_room_detail(request, room_id):
    """Display chat room with messages"""
    room = get_object_or_404(ChatRoom, id=room_id, is_active=True)
    
    # Check permission
    if request.user.user_type == 'student':
        if not Enrollment.objects.filter(
            student=request.user,
            course=room.course,
            is_active=True
        ).exists():
            messages.error(request, "You don't have permission to access this chat room.")
            return redirect('accounts:dashboard')
    elif request.user.user_type == 'teacher':
        if room.course.teacher != request.user:
            messages.error(request, "You don't have permission to access this chat room.")
            return redirect('accounts:dashboard')
    
    # Get messages with pagination
    chat_messages = ChatMessage.objects.filter(room=room).select_related('user').order_by('created_at')
    paginator = Paginator(chat_messages, 50)  # Show 50 messages per page
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    # Mark user as participant if not already
    membership, created = ChatRoomMembership.objects.get_or_create(
        user=request.user,
        room=room,
        defaults={'is_active': True}
    )
    
    # Get participant count
    participant_count = ChatRoomMembership.objects.filter(room=room, is_active=True).count()
    
    return render(request, 'chat/room_detail.html', {
        'room': room,
        'chat_messages': messages_page,
        'user': request.user,
        'participant_count': participant_count
    })


@login_required
@require_http_methods(["POST"])
def create_chat_room(request, course_id):
    """Create a new chat room for a course"""
    course = get_object_or_404(Course, id=course_id)
    
    # Only teachers can create chat rooms for their courses
    if request.user.user_type != 'teacher' or course.teacher != request.user:
        messages.error(request, 'Permission denied. You can only create chat rooms for your own courses.')
        return redirect('accounts:dashboard')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        
        if not name:
            messages.error(request, 'Room name is required.')
            return redirect('chat:select_course_for_room')
        
        # Check if a chat room already exists for this course
        if ChatRoom.objects.filter(course=course).exists():
            messages.error(request, f'A chat room already exists for "{course.title}".')
            return redirect('accounts:dashboard')
        
        chat_room = ChatRoom.objects.create(
            name=name,
            description=description,
            course=course,
            created_by=request.user
        )
        
        # Add the teacher as a member
        ChatRoomMembership.objects.create(
            user=request.user,
            room=chat_room
        )
        
        # Add all enrolled students as participants
        enrolled_students = User.objects.filter(
            enrollments__course=course,
            enrollments__is_active=True
        )
        
        for student in enrolled_students:
            ChatRoomMembership.objects.create(
                user=student,
                room=chat_room,
                role='member'
            )
        
        messages.success(request, f'Chat room "{name}" created successfully! {enrolled_students.count()} students added as participants.')
        return redirect('chat:room_detail', room_id=chat_room.id)
    
    # If GET request, redirect to course selection
    return redirect('chat:select_course_for_room')
    
    # Add the teacher as a participant
    ChatRoomMembership.objects.create(
        user=request.user,
        room=chat_room
    )
    
    django_messages.success(request, f'Chat room "{name}" created successfully!')
    return redirect('chat:room_detail', room_id=chat_room.id)


@login_required
def private_chat_list(request):
    """List all private chats for the user"""
    private_chats = PrivateChat.objects.filter(
        models.Q(participant1=request.user) | models.Q(participant2=request.user)
    ).select_related('participant1', 'participant2').order_by('-updated_at')
    
    # Add the other participant info for each chat
    chat_data = []
    for chat in private_chats:
        other_user = chat.participant2 if chat.participant1 == request.user else chat.participant1
        last_message = chat.messages.last()
        chat_data.append({
            'chat': chat,
            'other_user': other_user,
            'last_message': last_message
        })
    
    return render(request, 'chat/private_chat_list.html', {
        'chat_data': chat_data
    })


@login_required
def private_chat_detail(request, user_id):
    """Display private chat with another user"""
    other_user = get_object_or_404(User, id=user_id)
    
    if other_user == request.user:
        messages.error(request, "You cannot chat with yourself.")
        return redirect('chat:private_list')
    
    # Get or create private chat
    user1, user2 = sorted([request.user, other_user], key=lambda u: u.id)
    private_chat, created = PrivateChat.objects.get_or_create(
        participant1=user1,
        participant2=user2
    )
    
    # Handle POST request (sending a message)
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if content:
            PrivateMessage.objects.create(
                chat=private_chat,
                sender=request.user,
                content=content
            )
            # Update chat timestamp
            private_chat.updated_at = timezone.now()
            private_chat.save()
            
            return JsonResponse({'success': True})
        return JsonResponse({'error': 'Message content is required'}, status=400)
    
    # Get messages with pagination
    messages_list = PrivateMessage.objects.filter(chat=private_chat).select_related('sender').order_by('created_at')
    paginator = Paginator(messages_list, 50)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    # Mark messages as read
    PrivateMessage.objects.filter(
        chat=private_chat,
        sender=other_user,
        is_read=False
    ).update(is_read=True)
    
    return render(request, 'chat/private_chat_detail.html', {
        'private_chat': private_chat,
        'other_user': other_user,
        'messages': messages_page,
        'user': request.user
    })


@login_required
def user_search(request):
    """Search for users to start private chat"""
    query = request.GET.get('q', '')
    users = []
    
    if query:
        users = User.objects.filter(
            models.Q(username__icontains=query) | 
            models.Q(first_name__icontains=query) | 
            models.Q(last_name__icontains=query) |
            models.Q(email__icontains=query)
        ).exclude(id=request.user.id)[:10]
    
    return render(request, 'chat/user_search.html', {
        'users': users,
        'query': query
    })


@login_required
def get_room_messages(request, room_id):
    """API endpoint to get room messages"""
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # Check permission
    if request.user.user_type == 'student':
        if not Enrollment.objects.filter(
            student=request.user,
            course=room.course,
            is_active=True
        ).exists():
            return JsonResponse({'error': 'Permission denied'}, status=403)
    elif request.user.user_type == 'teacher':
        if room.course.teacher != request.user:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    
    page = int(request.GET.get('page', 1))
    messages = ChatMessage.objects.filter(room=room).select_related('user').order_by('-created_at')
    paginator = Paginator(messages, 20)
    messages_page = paginator.get_page(page)
    
    messages_data = []
    for message in messages_page:
        messages_data.append({
            'id': message.id,
            'content': message.content,
            'user': {
                'id': message.user.id,
                'username': message.user.username,
                'first_name': message.user.first_name,
                'last_name': message.user.last_name,
            },
            'created_at': message.created_at.isoformat(),
            'message_type': message.message_type,
        })
    
    return JsonResponse({
        'messages': messages_data,
        'has_next': messages_page.has_next(),
        'has_previous': messages_page.has_previous(),
        'total_pages': paginator.num_pages,
        'current_page': page
    })


@login_required
@require_http_methods(["POST"])
def start_private_chat(request, user_id):
    """Start or open existing private chat with another user"""
    other_user = get_object_or_404(User, id=user_id)
    
    if other_user == request.user:
        messages.error(request, "You cannot chat with yourself.")
        return redirect('chat:user_search')
    
    # Get or create private chat
    user1, user2 = sorted([request.user, other_user], key=lambda u: u.id)
    private_chat, created = PrivateChat.objects.get_or_create(
        participant1=user1,
        participant2=user2
    )
    
    if created:
        messages.success(request, f'Started new chat with {other_user.get_full_name() or other_user.username}!')
    else:
        messages.info(request, f'Opening existing chat with {other_user.get_full_name() or other_user.username}.')
    
    return redirect('chat:private_detail', user_id=other_user.id)


@login_required
def select_course_for_chat_room(request):
    """Allow teachers to select which course to create a chat room for"""
    if request.user.user_type != 'teacher':
        messages.error(request, 'Only teachers can create chat rooms.')
        return redirect('accounts:dashboard')
    
    # Get teacher's courses that don't already have chat rooms
    teacher_courses = Course.objects.filter(
        teacher=request.user,
        status='published'
    ).exclude(
        chat_rooms__isnull=False
    ).distinct()
    
    return render(request, 'chat/select_course_for_room.html', {
        'courses': teacher_courses
    })
