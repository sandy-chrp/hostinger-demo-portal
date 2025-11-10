# accounts/forms.py - Updated with Business Category Fields
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import CustomUser, BusinessCategory, BusinessSubCategory
import re


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=50, required=True)
    last_name = forms.CharField(max_length=50, required=True)
    email = forms.EmailField(required=True)
    
    # ✅ UPDATED: Dynamic mobile field (no max_length restriction)
    mobile = forms.CharField(
        max_length=15,  # Maximum for international numbers
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '9876543210',
            'inputmode': 'numeric'
        })
    )
    
    country_code = forms.ChoiceField(choices=CustomUser.COUNTRY_CHOICES)
    job_title = forms.CharField(max_length=100, required=True)
    organization = forms.CharField(max_length=200, required=True)
    business_category = forms.ModelChoiceField(
        queryset=BusinessCategory.objects.filter(is_active=True),
        required=True
    )
    business_subcategory = forms.ModelChoiceField(
        queryset=BusinessSubCategory.objects.filter(is_active=True),
        required=False
    )
    referral_source = forms.ChoiceField(choices=CustomUser.REFERRAL_CHOICES, required=False)
    referral_message = forms.CharField(widget=forms.Textarea, required=False)
    
    class Meta:
        model = CustomUser
        fields = ['first_name', 'last_name', 'email', 'mobile', 'country_code',
                  'job_title', 'organization', 'business_category', 
                  'business_subcategory', 'referral_source', 'referral_message',
                  'password1', 'password2']
    
    # ✅ NEW: Country-specific validation rules
    MOBILE_VALIDATION_RULES = {
        '+91': {
            'min_length': 10,
            'max_length': 10,
            'pattern': r'^[6-9]\d{9}$',
            'message': 'Indian mobile number must be 10 digits starting with 6-9'
        },
        '+1': {
            'min_length': 10,
            'max_length': 10,
            'pattern': r'^\d{10}$',
            'message': 'US/Canada mobile number must be 10 digits'
        },
        '+44': {
            'min_length': 10,
            'max_length': 10,
            'pattern': r'^[1-9]\d{9}$',
            'message': 'UK mobile number must be 10 digits'
        },
        '+86': {
            'min_length': 11,
            'max_length': 11,
            'pattern': r'^1[3-9]\d{9}$',
            'message': 'Chinese mobile number must be 11 digits starting with 1'
        },
        '+61': {
            'min_length': 9,
            'max_length': 9,
            'pattern': r'^4\d{8}$',
            'message': 'Australian mobile number must be 9 digits starting with 4'
        },
        '+971': {
            'min_length': 9,
            'max_length': 9,
            'pattern': r'^5\d{8}$',
            'message': 'UAE mobile number must be 9 digits starting with 5'
        },
        '+966': {
            'min_length': 9,
            'max_length': 9,
            'pattern': r'^5\d{8}$',
            'message': 'Saudi mobile number must be 9 digits starting with 5'
        },
        '+65': {
            'min_length': 8,
            'max_length': 8,
            'pattern': r'^[89]\d{7}$',
            'message': 'Singapore mobile number must be 8 digits starting with 8 or 9'
        },
        '+81': {
            'min_length': 10,
            'max_length': 10,
            'pattern': r'^[7-9]\d{8,9}$',
            'message': 'Japanese mobile number must be 9-10 digits'
        },
        # Default for other countries
        'default': {
            'min_length': 7,
            'max_length': 15,
            'pattern': r'^\d{7,15}$',
            'message': 'Mobile number must be between 7-15 digits'
        }
    }
    
    def clean_mobile(self):
        """Validate mobile number"""
        mobile = self.cleaned_data.get('mobile', '').strip()
        
        # Remove any non-digit characters
        mobile_clean = re.sub(r'\D', '', mobile)
        
        if not mobile_clean:
            raise ValidationError('Mobile number is required')
        
        # Basic digit check
        if not mobile_clean.isdigit():
            raise ValidationError('Mobile number must contain only digits')
        
        return mobile_clean
    
    def clean(self):
        """Form-level validation with country-specific rules"""
        cleaned_data = super().clean()
        mobile = cleaned_data.get('mobile')
        country_code = cleaned_data.get('country_code', '+91')
        
        if mobile and country_code:
            # Get validation rule for selected country
            rule = self.MOBILE_VALIDATION_RULES.get(
                country_code, 
                self.MOBILE_VALIDATION_RULES['default']
            )
            
            # Check length
            if len(mobile) < rule['min_length'] or len(mobile) > rule['max_length']:
                self.add_error('mobile', rule['message'])
            
            # Check pattern
            elif not re.match(rule['pattern'], mobile):
                self.add_error('mobile', rule['message'])
        
        return cleaned_data

class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-center',
            'placeholder': '000000',
            'autocomplete': 'off',
            'inputmode': 'numeric',
            'pattern': '[0-9]{6}'
        })
    )

# Keep all your existing forms unchanged
class SignInForm(forms.Form):
    """User login form"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'your@company.com',
            'required': True,
            'autofocus': True
        })
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your password',
            'required': True
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox'
        })
    )
    
    def clean_email(self):
        """Validate email format"""
        email = self.cleaned_data.get('email')
        if email:
            # Convert to lowercase for case-insensitive login
            email = email.lower().strip()
            domain = email.split('@')[1]
            blocked_domains = getattr(settings, 'BLOCKED_EMAIL_DOMAINS', [])
            
            if domain in blocked_domains:
                raise ValidationError('Please use your business email address.')
        
        return email

class ProfileForm(forms.ModelForm):
    """User profile edit form - UPDATED with mobile validation"""
    
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'mobile', 'country_code',
            'job_title', 'organization', 'business_category', 'business_subcategory'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Last Name'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '9876543210',
                'inputmode': 'numeric',
                'maxlength': '15'
            }),
            'country_code': forms.Select(attrs={
                'class': 'form-input'
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Your job title'
            }),
            'organization': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Company name'
            }),
            'business_category': forms.Select(attrs={
                'class': 'form-input',
                'id': 'profileCategorySelect'
            }),
            'business_subcategory': forms.Select(attrs={
                'class': 'form-input',
                'id': 'profileSubcategorySelect'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Filter active categories
        self.fields['business_category'].queryset = BusinessCategory.objects.filter(is_active=True)
        
        # If user has a category, populate subcategories
        if self.instance.pk and self.instance.business_category:
            self.fields['business_subcategory'].queryset = BusinessSubCategory.objects.filter(
                category=self.instance.business_category,
                is_active=True
            )
        else:
            self.fields['business_subcategory'].queryset = BusinessSubCategory.objects.none()
    
    def clean_mobile(self):
        """Validate mobile number"""
        mobile = self.cleaned_data.get('mobile', '').strip()
        
        # Remove non-digits
        mobile_clean = re.sub(r'\D', '', mobile)
        
        if not mobile_clean:
            raise ValidationError('Mobile number is required')
        
        if not mobile_clean.isdigit():
            raise ValidationError('Mobile number must contain only digits')
        
        return mobile_clean
    
    def clean(self):
        """Apply country-specific validation"""
        cleaned_data = super().clean()
        mobile = cleaned_data.get('mobile')
        country_code = cleaned_data.get('country_code', '+91')
        
        if mobile and country_code:
            # Use same validation rules as SignUpForm
            rule = SignUpForm.MOBILE_VALIDATION_RULES.get(
                country_code,
                SignUpForm.MOBILE_VALIDATION_RULES['default']
            )
            
            # Validate length and pattern
            if len(mobile) < rule['min_length'] or len(mobile) > rule['max_length']:
                self.add_error('mobile', rule['message'])
            elif not re.match(rule['pattern'], mobile):
                self.add_error('mobile', rule['message'])
            
            # Check duplicate mobile (excluding current user)
            if self.instance.pk:
                existing = CustomUser.objects.filter(
                    mobile=mobile,
                    country_code=country_code
                ).exclude(pk=self.instance.pk)
                
                if existing.exists():
                    self.add_error('mobile', 'This mobile number is already registered')
        
        return cleaned_data


class CustomPasswordChangeForm(PasswordChangeForm):
    """Custom password change form with styling"""
    
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Current password',
            'autofocus': True
        })
    )
    
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New password'
        })
    )
    
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password'
        })
    )

class ForgotPasswordForm(forms.Form):
    """Forgot password form"""
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your registered email',
            'required': True,
            'autofocus': True
        })
    )
    
    def clean_email(self):
        """Validate email exists"""
        email = self.cleaned_data.get('email')
        if email:
            try:
                user = CustomUser.objects.get(email=email)
                if not user.is_approved:
                    raise ValidationError(
                        'You are not a customer of the demo portal. Please sign up now.'
                    )
            except CustomUser.DoesNotExist:
                raise ValidationError(
                    'You are not a customer of the demo portal. Please sign up now.'
                )
        
        return email

class ResetPasswordForm(forms.Form):
    """Reset password form"""
    
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'New password',
            'required': True
        }),
        min_length=8,
        help_text='Password must be at least 8 characters long.'
    )
    
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm new password',
            'required': True
        })
    )
    
    def clean(self):
        """Validate password confirmation"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2:
            if password1 != password2:
                raise ValidationError('Passwords do not match.')
        
        return cleaned_data