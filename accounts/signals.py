# accounts/signals.py
"""
Django Signals for sending welcome emails based on user type
OUTLOOK COMPATIBLE VERSION
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags

from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def send_welcome_email_on_user_creation(sender, instance, created, **kwargs):
    """
    Send appropriate welcome email based on user type (employee vs customer)
    
    This signal is triggered after a CustomUser is saved.
    Only sends email when:
    - User is newly created (not updated)
    - User's email is verified (is_email_verified=True)
    - User is approved (is_approved=True)
    """
    
    # Only proceed for newly created users
    if not created:
        return
    
    # Skip if email not verified or not approved
    if not instance.is_email_verified or not instance.is_approved:
        return
    
    # Determine which template to use based on user type
    if instance.user_type == 'employee':
        template_name = 'emails/employee_welcome_email.html'
        subject = f'Welcome to CHRP - Your Employee Account is Ready'
    else:  # customer
        template_name = 'emails/customer_welcome.html'
        subject = 'Welcome to CHRP - Registration Successful'
    
    # Get current year for footer
    from datetime import datetime
    current_year = datetime.now().year
    
    # Prepare template context
    context = {
        'user': instance,
        'login_url': f"{settings.SITE_URL}/auth/signin/",
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'reach@chrp-india.com'),
        'company_name': 'CHRP India',
        'site_url': settings.SITE_URL,
        'year': current_year,
        # 'password': None,  # Only include if you want to send temporary password
    }
    
    try:
        # Render HTML email
        html_message = render_to_string(template_name, context)
        
        # Create plain text version (fallback for email clients that don't support HTML)
        plain_message = strip_tags(html_message)
        
        # Use EmailMultiAlternatives for better Outlook compatibility
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.email],
        )
        
        # Attach HTML version
        email.attach_alternative(html_message, "text/html")
        
        # Send email
        email.send(fail_silently=False)
        
        print(f"✅ Welcome email sent to {instance.email} ({instance.user_type})")
        
    except Exception as e:
        # Log error but don't break the user creation process
        print(f"❌ Failed to send welcome email to {instance.email}: {str(e)}")


def send_employee_welcome_with_password(user, temporary_password):
    """
    Manually send employee welcome email with temporary password
    
    Call this function when you want to send password in the email.
    Usage in views:
        user.save()
        send_employee_welcome_with_password(user, password)
    """
    
    from datetime import datetime
    current_year = datetime.now().year
    
    context = {
        'user': user,
        'password': temporary_password,  # Include password in context
        'login_url': f"{settings.SITE_URL}/auth/signin/",
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'reach@chrp-india.com'),
        'company_name': 'CHRP India',
        'site_url': settings.SITE_URL,
        'year': current_year,
    }
    
    try:
        html_message = render_to_string('emails/employee_welcome_email.html', context)
        plain_message = strip_tags(html_message)
        
        email = EmailMultiAlternatives(
            subject='Welcome to CHRP - Your Employee Account is Ready',
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        print(f"✅ Employee welcome email with password sent to {user.email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send employee welcome email: {str(e)}")
        return False


# Optional: Signal to send email verification
@receiver(post_save, sender=CustomUser)
def send_verification_email_if_needed(sender, instance, created, **kwargs):
    """
    Send email verification link if user needs to verify email
    
    This is separate from welcome email and is sent when:
    - User is newly created
    - Email is NOT verified yet
    - Verification token exists
    """
    
    if not created:
        return
    
    # Skip if already verified
    if instance.is_email_verified:
        return
    
    # Skip if no verification token
    if not instance.email_verification_token:
        return
    
    from datetime import datetime
    current_year = datetime.now().year
    
    subject = 'Verify Your CHRP Account Email'
    template_name = 'emails/email_verification.html'
    
    context = {
        'user': instance,
        'verification_link': f"{settings.SITE_URL}/auth/verify-email/{instance.email_verification_token}/",
        'support_email': getattr(settings, 'SUPPORT_EMAIL', 'reach@chrp-india.com'),
        'year': current_year,
    }
    
    try:
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[instance.email],
        )
        
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        print(f"✅ Verification email sent to {instance.email}")
        
    except Exception as e:
        print(f"❌ Failed to send verification email to {instance.email}: {str(e)}")