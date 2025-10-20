# accounts/utils.py
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
import uuid

def send_verification_email(user, request):
    """Send email verification link to user"""
    
    # Generate verification token
    user.email_verification_token = str(uuid.uuid4())
    user.save()
    
    # Build verification URL
    verification_url = request.build_absolute_uri(
        reverse('accounts:verify_email_view', args=[user.email_verification_token])
    )
    
    # Email subject and message
    subject = f'Verify Your Email - {settings.SITE_NAME}'
    message = f"""
Hello {user.full_name},

Welcome to {settings.SITE_NAME}!

Please verify your email address by clicking the link below:
{verification_url}

This link will expire in 24 hours.

If you didn't create this account, please ignore this email.

Best regards,
{settings.SITE_NAME} Team
    """
    
    # Send email
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )