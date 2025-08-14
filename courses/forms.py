from django import forms
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from .models import Course, CourseMaterial, Feedback, Enrollment


class CourseForm(forms.ModelForm):
    """Form for creating and updating courses"""
    
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'short_description', 'category',
            'difficulty_level', 'course_image', 'max_students',
            'is_free', 'price', 'prerequisites', 'learning_outcomes',
            'tags', 'meta_description', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter course title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Provide a detailed description of your course...'
            }),
            'short_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description for course listings...'
            }),
            'category': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Programming, Design, Business'
            }),
            'difficulty_level': forms.Select(attrs={
                'class': 'form-control'
            }),
            'course_image': forms.FileInput(attrs={
                'class': 'form-control-file',
                'accept': 'image/*'
            }),
            'max_students': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 500
            }),
            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01'
            }),
            'prerequisites': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What should students know before taking this course?'
            }),
            'learning_outcomes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'What will students learn from this course?'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Comma-separated tags (e.g., python, web development, beginner)'
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'maxlength': 160,
                'placeholder': 'SEO meta description for search engines (max 160 characters)'
            }),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help texts
        self.fields['short_description'].help_text = 'This will be shown in course listings (max 300 characters)'
        self.fields['course_image'].help_text = 'Upload a course thumbnail (recommended size: 800x600px)'
        self.fields['max_students'].help_text = 'Maximum number of students that can enroll'
        self.fields['price'].help_text = 'Leave as 0 for free courses'
        self.fields['tags'].help_text = 'Separate multiple tags with commas'
        
        # Make price field conditional on is_free
        if 'is_free' in self.data:
            if self.data.get('is_free'):
                self.fields['price'].widget = forms.HiddenInput()
    
    def clean_title(self):
        """Validate and clean the title"""
        title = self.cleaned_data.get('title')
        if not title:
            return title
        
        # Check for duplicate titles (excluding current instance if updating)
        queryset = Course.objects.filter(title=title)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise ValidationError('A course with this title already exists.')
        
        return title
    
    def clean_price(self):
        """Validate price based on is_free field"""
        price = self.cleaned_data.get('price', 0)
        is_free = self.cleaned_data.get('is_free', True)
        
        if is_free and price > 0:
            raise ValidationError('Free courses cannot have a price.')
        
        if not is_free and price <= 0:
            raise ValidationError('Paid courses must have a price greater than 0.')
        
        return price
    
    def save(self, commit=True):
        """Generate slug and save the course"""
        course = super().save(commit=False)
        
        if not course.slug:
            course.slug = slugify(course.title)
            
            # Ensure slug is unique
            original_slug = course.slug
            counter = 1
            while Course.objects.filter(slug=course.slug).exists():
                course.slug = f"{original_slug}-{counter}"
                counter += 1
        
        if commit:
            course.save()
        
        return course


class CourseMaterialForm(forms.ModelForm):
    """Form for adding/updating course materials"""
    
    class Meta:
        model = CourseMaterial
        fields = [
            'title', 'description', 'material_type', 'file', 'external_link',
            'duration', 'order', 'is_downloadable', 'is_public'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Material title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Brief description of this material...'
            }),
            'material_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control-file'
            }),
            'external_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://...'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 15:30 or 1h 30min'
            }),
            'order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help texts
        self.fields['file'].help_text = 'Upload a file (PDF, video, audio, etc.)'
        self.fields['external_link'].help_text = 'Or provide a link to external content'
        self.fields['duration'].help_text = 'For video/audio materials'
        self.fields['order'].help_text = 'Display order (0 = first)'
        self.fields['is_downloadable'].help_text = 'Allow students to download this file'
        self.fields['is_public'].help_text = 'Make visible without enrollment (preview)'
        
        # Add custom styling for checkboxes
        self.fields['is_downloadable'].widget.attrs.update({'class': 'form-check-input'})
        self.fields['is_public'].widget.attrs.update({'class': 'form-check-input'})
    
    def clean(self):
        """Validate that either file or external_link is provided"""
        cleaned_data = super().clean()
        file = cleaned_data.get('file')
        external_link = cleaned_data.get('external_link')
        
        if not file and not external_link:
            raise ValidationError('Either upload a file or provide an external link.')
        
        if file and external_link:
            raise ValidationError('Provide either a file or an external link, not both.')
        
        return cleaned_data


class FeedbackForm(forms.ModelForm):
    """Form for course feedback"""
    
    class Meta:
        model = Feedback
        fields = ['rating', 'title', 'content', 'is_anonymous']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f'{i} Star{"s" if i != 1 else ""}') for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Summarize your feedback...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Share your detailed thoughts about this course...'
            }),
            'is_anonymous': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help texts
        self.fields['rating'].help_text = 'Rate your overall experience'
        self.fields['title'].help_text = 'Brief summary of your feedback'
        self.fields['content'].help_text = 'Detailed feedback to help other students and the teacher'
        self.fields['is_anonymous'].help_text = 'Hide your name from this feedback'


class CourseSearchForm(forms.Form):
    """Form for searching and filtering courses"""
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search courses, teachers, topics...'
        })
    )
    
    category = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    difficulty = forms.ChoiceField(
        choices=[('', 'All Levels')] + Course.DIFFICULTY_CHOICES,
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    free_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Free courses only'
    )
    
    sort_by = forms.ChoiceField(
        choices=[
            ('-created_at', 'Newest First'),
            ('title', 'Title A-Z'),
            ('-enrollment_count', 'Most Popular'),
            ('-avg_rating', 'Highest Rated'),
        ],
        required=False,
        initial='-created_at',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )


class EnrollmentForm(forms.ModelForm):
    """Form for enrollment management (admin use)"""
    
    class Meta:
        model = Enrollment
        fields = ['student', 'course', 'is_active', 'progress', 'notes']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'progress': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter students and courses
        self.fields['student'].queryset = self.fields['student'].queryset.filter(user_type='student')
        self.fields['course'].queryset = self.fields['course'].queryset.filter(status='published')
