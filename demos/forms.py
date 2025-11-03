
# demos/forms.py - Complete with all imports and forms

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
from .models import DemoRequest, DemoFeedback, Demo, TimeSlot
from accounts.models import BusinessCategory, BusinessSubCategory
from accounts.models import CustomUser, BusinessCategory, BusinessSubCategory  # Add this line

# Get the user model (CustomUser)
User = get_user_model()


class DemoRequestForm(forms.ModelForm):
    """Form for requesting demo sessions"""
    
    class Meta:
        model = DemoRequest
        fields = [
            'requested_date', 
            'requested_time_slot', 
            'notes',
            'postal_code',
            'city',
            'country_region',
            'timezone'
        ]
        widgets = {
            'requested_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'required': True
            }),
            'requested_time_slot': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Any specific topics or questions you\'d like covered?'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter postal/ZIP code'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter city'
            }),
            'country_region': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country/Region code'
            }),
            'timezone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., GMT+5:30'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active time slots
        self.fields['requested_time_slot'].queryset = TimeSlot.objects.filter(is_active=True)
    
    def clean_requested_date(self):
        from django.utils import timezone
        from datetime import timedelta
        
        requested_date = self.cleaned_data['requested_date']
        
        # Check if date is not in the past
        if requested_date < timezone.now().date():
            raise ValidationError("Cannot request demos for past dates.")
        
        # Check if date is not Sunday
        if requested_date.weekday() == 6:
            raise ValidationError("Demo sessions are not available on Sundays.")
        
        # Check if date is within allowed advance booking period (30 days)
        max_advance_date = timezone.now().date() + timedelta(days=30)
        if requested_date > max_advance_date:
            raise ValidationError("Demo sessions can only be booked up to 30 days in advance.")
        
        return requested_date


class DemoFeedbackForm(forms.ModelForm):
    """Form for submitting demo feedback"""
    
    class Meta:
        model = DemoFeedback
        fields = ['rating', 'feedback_text']
        widgets = {
            'rating': forms.RadioSelect(
                choices=[(i, i) for i in range(1, 6)],
                attrs={'class': 'form-check-input'}
            ),
            'feedback_text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your thoughts about this demo...',
                'required': True
            })
        }
    
    def clean_feedback_text(self):
        feedback_text = self.cleaned_data.get('feedback_text')
        if feedback_text and len(feedback_text.strip()) < 10:
            raise ValidationError("Feedback must be at least 10 characters long.")
        return feedback_text.strip()


class DemoFilterForm(forms.Form):
    """Form for filtering demos"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search demos...'
        })
    )
    
    demo_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Types')] + Demo.DEMO_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        required=False,
        queryset=BusinessCategory.objects.filter(is_active=True),
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('newest', 'Newest First'),
            ('oldest', 'Oldest First'),
            ('popular', 'Most Popular'),
            ('featured', 'Featured First')
        ],
        initial='newest',
        widget=forms.Select(attrs={'class': 'form-select'})
    )




class AdminDemoForm(forms.ModelForm):
    """Admin form for creating/editing demos - Supports Video, WebGL, LMS"""
    
    # File Type Selection
    file_type = forms.ChoiceField(
        choices=[
            ('video', '🎥 Video Demo (MP4, AVI, MOV)'),
            ('webgl', '🧊 WebGL Interactive (HTML, ZIP, 3D)'),
            ('lms', '🎓 LMS/SCORM Package (ZIP)'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_file_type'
        }),
        label='File Type',
        required=True,
        initial='video'
    )
    
    # Business Categories - ManyToMany field
    target_business_categories = forms.ModelMultipleChoiceField(
        queryset=BusinessCategory.objects.filter(is_active=True).order_by('sort_order', 'name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input category-checkbox'
        }),
        help_text='Select business categories this demo is relevant for. Leave empty for all categories.'
    )
    
    # Business Subcategories - ManyToMany field
    target_business_subcategories = forms.ModelMultipleChoiceField(
        queryset=BusinessSubCategory.objects.filter(is_active=True).order_by('sort_order', 'name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input subcategory-checkbox'
        }),
        help_text='Select specific subcategories this demo is relevant for.'
    )
    
    # Customer Selection - ManyToMany field
    target_customers = forms.ModelMultipleChoiceField(
        queryset=CustomUser.objects.filter(
            user_type='customer',
            is_active=True
        ).order_by('first_name', 'last_name'),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input customer-checkbox'
        }),
        help_text="Select specific customers who can access this demo. Leave empty for all customers."
    )
    
    # Helper field for "All Customers" option
    all_customers = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'allCustomersCheckbox'
        }),
        label="Available to All Customers"
    )
    
    # Helper field for "All Business Categories" option
    all_business_categories = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'allBusinessCategoriesCheckbox'
        }),
        label="Available to All Business Categories"
    )
    
    class Meta:
        model = Demo
        fields = [
            'title',
            'description',
            'file_type',
            'video_file',
            'webgl_file',
            'lms_file',
            'thumbnail',
            'demo_type',
            'target_business_categories',
            'target_business_subcategories',
            'target_customers',
            'is_featured',
            'is_active',
            'sort_order'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter demo title',
                'required': True,
                'id': 'id_title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe what this demo showcases...',
                'required': True,
                'id': 'id_description'
            }),
            'demo_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'video_file': forms.FileInput(attrs={
                'class': 'd-none',
                'accept': 'video/*',
                'id': 'id_video_file'
            }),
            'webgl_file': forms.FileInput(attrs={
                'class': 'd-none',
                'accept': '.html,.zip,.gltf,.glb',
                'id': 'id_webgl_file'
            }),
            'lms_file': forms.FileInput(attrs={
                'class': 'd-none',
                'accept': '.zip,.scorm',
                'id': 'id_lms_file'
            }),
            'thumbnail': forms.FileInput(attrs={
                'class': 'd-none',
                'accept': 'image/*',
                'id': 'id_thumbnail'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_featured'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'id_is_active'
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'value': 0
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial values for helper fields based on existing data
        if self.instance.pk:
            # Existing demo - check if categories/customers are selected
            if not self.instance.target_business_categories.exists():
                self.fields['all_business_categories'].initial = True
            else:
                self.fields['all_business_categories'].initial = False
                
            if not self.instance.target_customers.exists():
                self.fields['all_customers'].initial = True
            else:
                self.fields['all_customers'].initial = False
        
        # Improve field labels
        self.fields['file_type'].label = "File Type"
        self.fields['is_featured'].label = "Featured Demo"
        self.fields['is_active'].label = "Active"
        self.fields['thumbnail'].label = "Thumbnail (Optional)"
        self.fields['thumbnail'].help_text = "Default icon will be shown if not provided"
    
    def clean_title(self):
        """Validate title"""
        title = self.cleaned_data.get('title')
        if not title or not title.strip():
            raise ValidationError("Title cannot be empty.")
        return title.strip()
    
    def clean_video_file(self):
        """Validate video file"""
        video = self.cleaned_data.get('video_file')
        file_type = self.cleaned_data.get('file_type')
        
        # Only validate if file_type is video
        if file_type == 'video' and video:
            # Check file size (max 200MB)
            if video.size > 200 * 1024 * 1024:
                raise ValidationError("Video file size cannot exceed 200MB.")
            
            # Check file extension
            ext = video.name.split('.')[-1].lower()
            if ext not in ['mp4', 'avi', 'mov', 'wmv']:
                raise ValidationError("Invalid video format. Allowed: MP4, AVI, MOV, WMV")
        
        return video
    
    def clean_webgl_file(self):
        """Validate WebGL file"""
        webgl = self.cleaned_data.get('webgl_file')
        file_type = self.cleaned_data.get('file_type')
        
        # Only validate if file_type is webgl
        if file_type == 'webgl' and webgl:
            # Check file size (max 3GB)
            if webgl.size > 3 * 1024 * 1024 * 1024:
                raise ValidationError("WebGL file size cannot exceed 3GB.")
            
            # Check file extension
            ext = webgl.name.split('.')[-1].lower()
            if ext not in ['html', 'zip', 'gltf', 'glb']:
                raise ValidationError("Invalid WebGL format. Allowed: HTML, ZIP, GLTF, GLB")
        
        return webgl
    
    def clean_lms_file(self):
        """Validate LMS file"""
        lms = self.cleaned_data.get('lms_file')
        file_type = self.cleaned_data.get('file_type')
        
        # Only validate if file_type is lms
        if file_type == 'lms' and lms:
            # Check file size (max 4GB)
            if lms.size > 4 * 1024 * 1024 * 1024:
                raise ValidationError("LMS file size cannot exceed 4GB.")
            
            # Check file extension
            ext = lms.name.split('.')[-1].lower()
            if ext not in ['zip', 'scorm']:
                raise ValidationError("Invalid LMS format. Allowed: ZIP, SCORM")
        
        return lms
    
    def clean_thumbnail(self):
        """Validate thumbnail image"""
        thumbnail = self.cleaned_data.get('thumbnail')
        if thumbnail:
            # Check file size (max 10MB)
            if thumbnail.size > 10 * 1024 * 1024:
                raise ValidationError("Thumbnail size cannot exceed 10MB.")
            
            # Check file extension
            ext = thumbnail.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                raise ValidationError("Invalid image format. Allowed: JPG, PNG, WebP")
        
        return thumbnail
    
    def clean_target_business_subcategories(self):
        """Validate that selected subcategories belong to selected categories"""
        categories = self.cleaned_data.get('target_business_categories', [])
        subcategories = self.cleaned_data.get('target_business_subcategories', [])
        
        if subcategories and not categories:
            # If subcategories selected but no categories, it's okay
            return subcategories
            
        if subcategories and categories:
            # Validate that subcategories belong to selected categories
            valid_subcategories = BusinessSubCategory.objects.filter(
                category__in=categories
            )
            
            invalid_subcategories = []
            for subcat in subcategories:
                if subcat not in valid_subcategories:
                    invalid_subcategories.append(str(subcat))
            
            if invalid_subcategories:
                raise ValidationError(
                    f"The following subcategories don't belong to selected categories: {', '.join(invalid_subcategories)}"
                )
        
        return subcategories
    
    def clean(self):
        """Overall form validation"""
        cleaned_data = super().clean()
        
        file_type = cleaned_data.get('file_type')
        video_file = cleaned_data.get('video_file')
        webgl_file = cleaned_data.get('webgl_file')
        lms_file = cleaned_data.get('lms_file')
        
        # Validate that appropriate file is uploaded based on file_type
        if file_type == 'video' and not video_file and not self.instance.pk:
            raise ValidationError({'video_file': 'Video file is required when file type is Video'})
        
        if file_type == 'webgl' and not webgl_file and not self.instance.pk:
            raise ValidationError({'webgl_file': 'WebGL file is required when file type is WebGL'})
        
        if file_type == 'lms' and not lms_file and not self.instance.pk:
            raise ValidationError({'lms_file': 'LMS file is required when file type is LMS'})
        
        # Handle "all customers" logic
        all_customers = cleaned_data.get('all_customers')
        target_customers = cleaned_data.get('target_customers')
        
        if all_customers:
            cleaned_data['target_customers'] = []
        
        # Handle "all business categories" logic
        all_categories = cleaned_data.get('all_business_categories')
        
        if all_categories:
            cleaned_data['target_business_categories'] = []
            cleaned_data['target_business_subcategories'] = []
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the demo with ManyToMany relationships"""
        demo = super().save(commit=False)
        
        # Ensure slug is handled by the model
        if not demo.slug:
            demo.slug = None  # Model's save() will generate it
        
        if commit:
            demo.save()
            
            # Save ManyToMany relationships
            # Business Categories
            if self.cleaned_data.get('all_business_categories'):
                demo.target_business_categories.clear()
                demo.target_business_subcategories.clear()
            else:
                categories = self.cleaned_data.get('target_business_categories', [])
                demo.target_business_categories.set(categories)
                
                subcategories = self.cleaned_data.get('target_business_subcategories', [])
                demo.target_business_subcategories.set(subcategories)
            
            # Customers
            if self.cleaned_data.get('all_customers'):
                demo.target_customers.clear()
            else:
                customers = self.cleaned_data.get('target_customers', [])
                demo.target_customers.set(customers)
            
            # Save the form's many-to-many data
            self.save_m2m()
        
        return demo