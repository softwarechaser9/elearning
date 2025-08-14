import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, ChatMessage, PrivateChat, PrivateMessage, ChatRoomMembership

User = get_user_model()


class ChatRoomConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for chat rooms"""
    
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope.get('user')
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Check if user has permission to join this room
        has_permission = await self.check_room_permission()
        if not has_permission:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send user joined message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': self.user.username,
                'user_id': self.user.id
            }
        )
    
    async def disconnect(self, close_code):
        # Send user left message
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user': self.user.username,
                    'user_id': self.user.id
                }
            )
            
            # Leave room group
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'message')
            
            if message_type == 'message':
                message = text_data_json['message']
                
                # Save message to database
                chat_message = await self.save_message(message)
                
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'user': self.user.username,
                        'user_id': self.user.id,
                        'message_id': chat_message.id,
                        'created_at': chat_message.created_at.isoformat()
                    }
                )
            elif message_type == 'typing':
                # Send typing indicator
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'user': self.user.username,
                        'user_id': self.user.id,
                        'is_typing': text_data_json.get('is_typing', False)
                    }
                )
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': f'Error processing message: {str(e)}'
            }))
    
    async def chat_message(self, event):
        """Receive message from room group"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'user': event['user'],
            'user_id': event['user_id'],
            'message_id': event['message_id'],
            'created_at': event['created_at']
        }))
    
    async def user_joined(self, event):
        """Send user joined notification"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_joined',
                'message': f"{event['user']} joined the chat",
                'user': event['user'],
                'user_id': event['user_id']
            }))
    
    async def user_left(self, event):
        """Send user left notification"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'user_left',
                'message': f"{event['user']} left the chat",
                'user': event['user'],
                'user_id': event['user_id']
            }))
    
    async def typing_indicator(self, event):
        """Send typing indicator"""
        if event['user_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'user': event['user'],
                'user_id': event['user_id'],
                'is_typing': event['is_typing']
            }))
    
    @database_sync_to_async
    def check_room_permission(self):
        """Check if user has permission to access this chat room"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            # Check if user is enrolled in the course or is the teacher
            if self.user.user_type == 'teacher' and room.course.teacher == self.user:
                return True
            elif self.user.user_type == 'student':
                return room.course.enrollments.filter(student=self.user, is_active=True).exists()
            return False
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, message):
        """Save message to database"""
        room = ChatRoom.objects.get(id=self.room_id)
        chat_message = ChatMessage.objects.create(
            room=room,
            user=self.user,
            content=message
        )
        return chat_message


class PrivateChatConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for private chats"""
    
    async def connect(self):
        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        self.user = self.scope.get('user')
        
        if self.user.is_anonymous:
            await self.close()
            return
        
        # Create room name (sorted user IDs to ensure consistent naming)
        user_ids = sorted([self.user.id, int(self.other_user_id)])
        self.room_group_name = f'private_{user_ids[0]}_{user_ids[1]}'
        
        # Get or create private chat
        await self.get_or_create_private_chat()
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive message from WebSocket"""
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type', 'message')
            
            if message_type == 'message':
                message = text_data_json['message']
                
                # Save message to database
                private_message = await self.save_private_message(message)
                
                # Send message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'private_message',
                        'message': message,
                        'sender': self.user.username,
                        'sender_id': self.user.id,
                        'message_id': private_message.id,
                        'created_at': private_message.created_at.isoformat()
                    }
                )
            elif message_type == 'typing':
                # Send typing indicator
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'typing_indicator',
                        'sender': self.user.username,
                        'sender_id': self.user.id,
                        'is_typing': text_data_json.get('is_typing', False)
                    }
                )
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': f'Error processing message: {str(e)}'
            }))
    
    async def private_message(self, event):
        """Receive message from room group"""
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
            'sender': event['sender'],
            'sender_id': event['sender_id'],
            'message_id': event['message_id'],
            'created_at': event['created_at']
        }))
    
    async def typing_indicator(self, event):
        """Send typing indicator"""
        if event['sender_id'] != self.user.id:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'sender': event['sender'],
                'sender_id': event['sender_id'],
                'is_typing': event['is_typing']
            }))
    
    @database_sync_to_async
    def get_or_create_private_chat(self):
        """Get or create private chat"""
        other_user = User.objects.get(id=self.other_user_id)
        user1, user2 = sorted([self.user, other_user], key=lambda u: u.id)
        
        private_chat, created = PrivateChat.objects.get_or_create(
            participant1=user1,
            participant2=user2
        )
        self.private_chat = private_chat
        return private_chat
    
    @database_sync_to_async
    def save_private_message(self, message):
        """Save private message to database"""
        private_message = PrivateMessage.objects.create(
            chat=self.private_chat,
            sender=self.user,
            content=message
        )
        return private_message
