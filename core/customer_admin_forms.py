# core/customer_admin_forms.py
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
import re

User = get_user_model()

# Add these imports at top
from accounts.models import BusinessCategory, BusinessSubCategory

COUNTRY_MOBILE_FORMATS = {
    '+1': {'min': 10, 'max': 10, 'name': 'USA/Canada'},
    '+44': {'min': 10, 'max': 10, 'name': 'UK'},
    '+91': {'min': 10, 'max': 10, 'name': 'India'},
    '+86': {'min': 11, 'max': 11, 'name': 'China'},
    '+61': {'min': 9, 'max': 9, 'name': 'Australia'},
    '+971': {'min': 9, 'max': 9, 'name': 'UAE'},
    '+65': {'min': 8, 'max': 8, 'name': 'Singapore'},
    '+81': {'min': 10, 'max': 10, 'name': 'Japan'},
    '+49': {'min': 10, 'max': 11, 'name': 'Germany'},
    '+33': {'min': 9, 'max': 9, 'name': 'France'},
    '+92': {'min': 10, 'max': 10, 'name': 'Pakistan'},
    '+880': {'min': 10, 'max': 10, 'name': 'Bangladesh'},
    '+94': {'min': 9, 'max': 9, 'name': 'Sri Lanka'},
}

def validate_mobile_for_country(mobile, country_code):
    """Validate mobile number based on country code"""
    # Remove any spaces, dashes, or special characters
    clean_mobile = re.sub(r'[^\d]', '', mobile)
    
    # Get country format requirements
    country_format = COUNTRY_MOBILE_FORMATS.get(
        country_code, 
        {'min': 7, 'max': 15, 'name': 'International'}
    )
    
    min_length = country_format['min']
    max_length = country_format['max']
    country_name = country_format['name']
    
    # Check if only digits
    if not clean_mobile:
        raise ValidationError('Mobile number is required.')
    
    if not clean_mobile.isdigit():
        raise ValidationError('Mobile number must contain only digits.')
    
    # Check length
    if len(clean_mobile) < min_length or len(clean_mobile) > max_length:
        if min_length == max_length:
            raise ValidationError(
                f'Mobile number for {country_name} ({country_code}) must be exactly {min_length} digits.'
            )
        else:
            raise ValidationError(
                f'Mobile number for {country_name} ({country_code}) must be between {min_length}-{max_length} digits.'
            )
    
    return clean_mobile
    
class CustomerCreateForm(forms.ModelForm):
    """Form for admin to create new customers"""
    
    # Password fields
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'id': 'id_password'
        }),
        help_text='Password must be at least 8 characters long.'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'id': 'id_confirm_password'
        }),
        help_text='Enter the same password as above.'
    )
    
    # Business Category/Subcategory
    business_category = forms.ModelChoiceField(
        queryset=BusinessCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_business_category'
        }),
        help_text='Select customer business category (optional).'
    )
    
    business_subcategory = forms.ModelChoiceField(
        queryset=BusinessSubCategory.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_business_subcategory'
        }),
        help_text='Select subcategory after choosing category.'
    )
    
    skip_email_validation = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Skip business email domain validation (use with caution).'
    )
    
    verify_email_otp = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Send OTP to verify email address.'
    )
    
    send_welcome_email = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Send welcome email to customer.'
    )
    
    is_approved = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Approve account immediately.'
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'mobile', 'country_code',
            'job_title', 'organization', 'business_category', 'business_subcategory',
            'referral_source', 'referral_message'
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'id': 'id_first_name',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'required': True,
                'id': 'id_last_name',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'required': True,
                'id': 'id_email',
                'placeholder': 'business@company.com'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '[0-9]{7,15}',
                'maxlength': '15',
                'required': True,
                'id': 'id_mobile',
                'placeholder': '9876543210'
            }),
            # ✅ Country Code with proper styling
            'country_code': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
                'id': 'id_country_code'
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Manager, Director'
            }),
            'organization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company or Organization name'
            }),
            'referral_source': forms.Select(attrs={
                'class': 'form-select'
            }),
            'referral_message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: How did you hear about us?'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mark required fields
        required_fields = ['first_name', 'last_name', 'email', 'mobile', 'country_code']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
        # ✅ Set default country code to +91 (India)
        if 'country_code' in self.fields:
            if not self.instance.pk:  # Only for new records
                self.fields['country_code'].initial = '+91'
        
        # Populate subcategories if category is selected
        if 'business_category' in self.data:
            try:
                category_id = int(self.data.get('business_category'))
                self.fields['business_subcategory'].queryset = BusinessSubCategory.objects.filter(
                    category_id=category_id,
                    is_active=True
                ).order_by('sort_order', 'name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.business_category:
            self.fields['business_subcategory'].queryset = BusinessSubCategory.objects.filter(
                category=self.instance.business_category,
                is_active=True
            ).order_by('sort_order', 'name')
    
    def clean_email(self):
        """Validate business email with skip option"""
        email = self.cleaned_data.get('email', '').lower().strip()
        
        # ✅ Get skip_validation from raw form data
        skip_validation = self.data.get('skip_email_validation') == 'on'
        
        print(f"\n{'='*60}")
        print(f"📧 EMAIL VALIDATION")
        print(f"   Email: {email}")
        print(f"   Skip Validation: {skip_validation}")
        print(f"{'='*60}\n")
        
        if not email:
            raise ValidationError('Email is required.')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError('A customer with this email already exists.')
        
        # Skip domain validation if admin chose to
        if skip_validation:
            print(f"✅ Email domain validation SKIPPED by admin for: {email}")
            return email
        
        # Validate business email domain
        from django.conf import settings
        blocked_domains = getattr(settings, 'BLOCKED_EMAIL_DOMAINS', [
            'gmail.com', 'googlemail.com',
            'yahoo.com', 'yahoo.co.in', 'yahoo.co.uk', 'ymail.com', 'rocketmail.com',
            'hotmail.com', 'hotmail.co.uk', 'outlook.com', 'live.com', 'msn.com',
            'aol.com', 'aim.com',
            'icloud.com', 'me.com', 'mac.com',
            'rediffmail.com', 'rediff.com',
            'protonmail.com', 'mail.com', 'gmx.com', 'zoho.com'
        ])
        
        domain = email.split('@')[1].lower()
        if domain in blocked_domains:
            raise ValidationError(
                f'❌ Personal email domain ({domain}) not allowed. '
                f'Please use your business email or enable "Admin Override" to bypass.'
            )
        
        print(f"✅ Business email validated: {email}")
        return email
    
    def clean_mobile(self):
        """Validate mobile number based on country code"""
        mobile = self.cleaned_data.get('mobile', '').strip()
        country_code = self.data.get('country_code', '+91')
        
        if not mobile:
            raise ValidationError('Mobile number is required.')
        
        # Validate using country-specific rules
        try:
            clean_mobile = validate_mobile_for_country(mobile, country_code)
            return clean_mobile
        except ValidationError as e:
            raise e
    
    def clean_country_code(self):
        """Validate country code"""
        country_code = self.cleaned_data.get('country_code', '').strip()
        
        if not country_code:
            # ✅ Set default if empty
            return '+91'
        
        return country_code
    
    def clean_password(self):
        """Validate password"""
        password = self.cleaned_data.get('password')
        
        if not password:
            raise ValidationError('Password is required.')
        
        try:
            validate_password(password)
        except ValidationError as e:
            raise ValidationError(e.messages)
        
        return password
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        
        # Validate password match
        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError({
                    'confirm_password': 'Passwords do not match.'
                })
        
        # Generate username from email
        email = cleaned_data.get('email')
        if email:
            username = email.split('@')[0]
            counter = 1
            original_username = username
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            cleaned_data['username'] = username
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customer with all fields"""
        user = super().save(commit=False)
        
        user.username = self.cleaned_data['username']
        user.set_password(self.cleaned_data['password'])
        user.is_email_verified = True
        user.is_staff = False
        user.is_superuser = False
        
        if commit:
            user.save()
        
        return user

class CustomerEditForm(forms.ModelForm):
    """Form for admin to edit existing customers"""
    
    change_password = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='Check this box to change the customer\'s password.'
    )
    
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'id': 'id_new_password'
        }),
        help_text='Leave blank to keep current password.'
    )
    
    confirm_new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'id': 'id_confirm_new_password'
        }),
        help_text='Enter the same password as above, for verification.'
    )
    
    skip_email_validation = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'skipVerification'
        }),
        help_text='Skip email verification if email is changed (admin override).'
    )
    
    # Business Category/Subcategory
    business_category = forms.ModelChoiceField(
        queryset=BusinessCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'editCategorySelect'
        }),
        help_text='Select customer business category (optional).'
    )
    
    business_subcategory = forms.ModelChoiceField(
        queryset=BusinessSubCategory.objects.none(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'editSubcategorySelect'
        }),
        help_text='Select subcategory after choosing category (optional).'
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'mobile', 'country_code',
            'job_title', 'organization', 'business_category', 'business_subcategory',
            'referral_source', 'referral_message',
            'is_approved', 'is_active', 'is_email_verified'
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_first_name',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'id': 'id_last_name',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'id': 'id_email',
                'placeholder': 'business@company.com'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'pattern': '[0-9]{7,15}',
                'maxlength': '15',
                'id': 'id_mobile',
                'placeholder': '9876543210'
            }),
            'country_code': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_country_code'
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Manager, Director'
            }),
            'organization': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Company or Organization name'
            }),
            'referral_source': forms.Select(attrs={
                'class': 'form-select'
            }),
            'referral_message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional: How did you hear about us?'
            }),
            'is_approved': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_email_verified': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mark required fields
        required_fields = ['first_name', 'last_name', 'email', 'mobile', 'country_code']
        for field_name in required_fields:
            if field_name in self.fields:
                self.fields[field_name].required = True
        
        # Set default country code if not set
        if 'country_code' in self.fields:
            if not self.instance.pk or not self.instance.country_code:
                self.fields['country_code'].initial = '+91'
        
        # Populate subcategories if category is selected
        if 'business_category' in self.data:
            try:
                category_id = int(self.data.get('business_category'))
                self.fields['business_subcategory'].queryset = BusinessSubCategory.objects.filter(
                    category_id=category_id,
                    is_active=True
                ).order_by('sort_order', 'name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.business_category:
            self.fields['business_subcategory'].queryset = BusinessSubCategory.objects.filter(
                category=self.instance.business_category,
                is_active=True
            ).order_by('sort_order', 'name')
    
    def clean_email(self):
        """Validate email on edit"""
        email = self.cleaned_data.get('email', '').lower().strip()
        skip_validation = self.data.get('skip_email_validation') == 'on'
        
        print(f"\n{'='*60}")
        print(f"📧 EDIT - EMAIL VALIDATION")
        print(f"   New Email: {email}")
        print(f"   Old Email: {self.instance.email}")
        print(f"   Skip Validation: {skip_validation}")
        print(f"{'='*60}\n")
        
        if not email:
            raise ValidationError('Email is required.')
        
        # Check if email exists for other users
        existing_user = User.objects.filter(email=email).exclude(pk=self.instance.pk).first()
        if existing_user:
            raise ValidationError('A customer with this email already exists.')
        
        # If email hasn't changed, allow it
        if email == self.instance.email.lower():
            print(f"✅ Email unchanged - allowing without validation")
            return email
        
        # If skip validation is enabled, allow email change
        if skip_validation:
            print(f"✅ Email domain validation SKIPPED by admin")
            return email
        
        # Validate business email domain for new email
        from django.conf import settings
        blocked_domains = getattr(settings, 'BLOCKED_EMAIL_DOMAINS', [
            'gmail.com', 'googlemail.com',
            'yahoo.com', 'yahoo.co.in', 'yahoo.co.uk', 'ymail.com', 'rocketmail.com',
            'hotmail.com', 'hotmail.co.uk', 'outlook.com', 'live.com', 'msn.com',
            'aol.com', 'aim.com',
            'icloud.com', 'me.com', 'mac.com',
            'rediffmail.com', 'rediff.com',
            'protonmail.com', 'mail.com', 'gmx.com', 'zoho.com'
        ])
        
        domain = email.split('@')[1].lower()
        if domain in blocked_domains:
            raise ValidationError(
                f'Business email required. Personal email domain ({domain}) not allowed. '
                f'Enable "Skip Email Verification" to override.'
            )
        
        print(f"✅ Business email validated: {email}")
        return email
    
    def clean_mobile(self):
        """Validate mobile number based on country code"""
        mobile = self.cleaned_data.get('mobile', '').strip()
        country_code = self.data.get('country_code') or self.instance.country_code or '+91'
        
        if not mobile:
            raise ValidationError('Mobile number is required.')
        
        # Validate using country-specific rules
        try:
            clean_mobile = validate_mobile_for_country(mobile, country_code)
            return clean_mobile
        except ValidationError as e:
            raise e
    
    def clean_country_code(self):
        """Validate country code"""
        country_code = self.cleaned_data.get('country_code', '').strip()
        
        if not country_code:
            return '+91'  # Default to India
        
        return country_code
    
    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        change_password = cleaned_data.get('change_password')
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')
        
        # Validate password change
        if new_password or confirm_new_password:
            if not new_password:
                raise ValidationError({
                    'new_password': 'New password is required when changing password.'
                })
            
            try:
                validate_password(new_password)
            except ValidationError as e:
                raise ValidationError({
                    'new_password': e.messages
                })
            
            if new_password != confirm_new_password:
                raise ValidationError({
                    'confirm_new_password': 'Passwords do not match.'
                })
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save customer with optional password change"""
        user = super().save(commit=False)
        
        # Update password if provided
        if self.cleaned_data.get('new_password'):
            user.set_password(self.cleaned_data['new_password'])
            print(f"✅ Password updated for: {user.email}")
        
        if commit:
            user.save()
        
        return user

class CustomerSearchForm(forms.Form):
    """Form for searching customers"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'autocomplete': 'off'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Customers'),
            ('active', 'Active'),
            ('pending', 'Pending Approval'),
            ('blocked', 'Blocked'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )