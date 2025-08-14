<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

# eLearning Django Application - Copilot Instructions

## Project Overview
This is a comprehensive eLearning web application built with Django. The application supports two types of users (students and teachers) with different permissions and includes real-time features.

## Key Technologies
- Django 4.2.7 with Django REST Framework
- Django Channels for WebSocket support
- Redis for caching and message brokering
- Bootstrap 4 for frontend styling
- SQLite (development) / PostgreSQL (production)

## Code Style Guidelines
- Follow Django best practices and PEP 8
- Use class-based views where appropriate
- Implement proper error handling and validation
- Write comprehensive tests for all functionality
- Use Django's built-in authentication system
- Implement proper permissions and security measures

## Application Structure
- `accounts/` - User management and authentication
- `courses/` - Course creation and management
- `chat/` - Real-time chat functionality using WebSockets
- `api/` - REST API endpoints using DRF
- Follow Django's MVT (Model-View-Template) pattern

## Security Considerations
- Implement proper user permissions (students vs teachers)
- Validate all user inputs
- Use Django's CSRF protection
- Secure file upload handling
- Implement rate limiting for API endpoints

## Testing Guidelines
- Write unit tests for all models, views, and API endpoints
- Test WebSocket functionality
- Test file upload features
- Test user permissions and authentication
- Use Django's TestCase and APITestCase classes

## Database Design
- Use Django's ORM effectively
- Implement proper foreign key relationships
- Add appropriate indexes for performance
- Use migrations for all database changes
- Follow database normalization principles

## WebSocket Implementation
- Use Django Channels for real-time features
- Implement proper channel layer configuration
- Handle WebSocket connections securely
- Test WebSocket functionality thoroughly
