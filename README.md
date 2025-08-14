# eLearning Django Application

A comprehensive eLearning web application built with Django, featuring user authentication, course management, real-time chat, and REST API.

## Features

### Core Features
- **User Management**: Students and Teachers with different permissions
- **Course Management**: Teachers can create courses, upload materials
- **Enrollment System**: Students can enroll in courses
- **Feedback System**: Students can leave course feedback
- **Real-time Chat**: WebSocket-based chat between users
- **File Management**: Upload and manage course materials
- **REST API**: Full REST interface for user data
- **Notifications**: Real-time notifications for enrollments and new materials

### User Types
- **Students**: Can enroll in courses, leave feedback, post status updates, chat
- **Teachers**: Can create courses, manage students, upload materials, search users

## Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd elearning_app
```

2. **Create virtual environment**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment setup**
Create a `.env` file in the root directory:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379
```

5. **Database setup**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

6. **Load sample data**
```bash
python manage.py loaddata sample_data.json
```

7. **Run Redis server** (for real-time features)
```bash
redis-server
```

8. **Run the application**
```bash
python manage.py runserver
```

## Default Login Credentials

### Admin
- Username: `admin`
- Password: `admin123`

### Sample Teacher
- Username: `teacher1`
- Password: `teacher123`

### Sample Student
- Username: `student1`
- Password: `student123`

## Testing

Run the test suite:
```bash
python manage.py test
```

Run specific app tests:
```bash
python manage.py test accounts
python manage.py test courses
python manage.py test chat
python manage.py test api
```

## Project Structure

```
elearning_app/
├── elearning/              # Main Django project
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/               # User management app
├── courses/                # Course management app
├── chat/                   # Real-time chat app
├── api/                    # REST API app
├── static/                 # Static files
├── media/                  # User uploaded files
├── templates/              # HTML templates
└── requirements.txt
```

## Database Design

### Models
- **User**: Extended Django user with profile information
- **Course**: Course information and materials
- **Enrollment**: Student-course relationships
- **Feedback**: Course feedback from students
- **StatusUpdate**: User status updates
- **ChatMessage**: Real-time chat messages
- **Notification**: System notifications

## API Endpoints

### Authentication
- `POST /api/auth/login/` - User login
- `POST /api/auth/logout/` - User logout
- `POST /api/auth/register/` - User registration

### Users
- `GET /api/users/` - List users
- `GET /api/users/{id}/` - User details
- `PUT /api/users/{id}/` - Update user

### Courses
- `GET /api/courses/` - List courses
- `POST /api/courses/` - Create course (teachers only)
- `GET /api/courses/{id}/` - Course details
- `POST /api/courses/{id}/enroll/` - Enroll in course

### Feedback
- `GET /api/feedback/` - List feedback
- `POST /api/feedback/` - Create feedback

## WebSocket Endpoints

- `/ws/chat/{room_name}/` - Real-time chat rooms
- `/ws/notifications/` - Real-time notifications

## Development Environment

- **OS**: Windows/macOS/Linux
- **Python**: 3.8+
- **Django**: 4.2.7
- **Database**: SQLite (development), PostgreSQL (production)
- **Cache/Message Broker**: Redis

## Deployment

The application is designed to be deployed on cloud platforms like AWS, DigitalOcean, or Heroku.

### Environment Variables for Production
```env
SECRET_KEY=production-secret-key
DEBUG=False
DATABASE_URL=postgresql://user:pass@host:port/dbname
REDIS_URL=redis://host:port
ALLOWED_HOSTS=your-domain.com
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

## License

This project is for educational purposes.
