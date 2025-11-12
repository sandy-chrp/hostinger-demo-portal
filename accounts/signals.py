# accounts/signals.py - COMPLETE FIX WITH DEBUGGING
"""
Django Signals for sending welcome emails based on user type
✅ FIXED: Manual email sending with proper error handling and debugging
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import traceback

from .models import CustomUser


@receiver(post_save, sender=CustomUser)
def send_welcome_email_on_user_creation(sender, instance, created, **kwargs):
    """
    ✅ COMPLETELY DISABLED: No automatic welcome emails
    
    All emails must be sent manually from views
    """
    pass  # ✅ Do nothing - emails are manual now


def send_employee_welcome_with_password(user, temporary_password):
    """Send welcome email with password"""
    
    from datetime import datetime
    from django.conf import settings
    from django.template.loader import render_to_string
    from django.core.mail import EmailMultiAlternatives
    from django.utils.html import strip_tags
    import traceback
    
    print("\n" + "="*80)
    print("DEBUG: SENDING EMPLOYEE WELCOME EMAIL")
    print(f"To: {user.email}")
    print(f"Password: {temporary_password}")
    print("="*80 + "\n")
    
    try:
        context = {
            'user': user,
            'password': temporary_password,
            'login_url': f"{settings.SITE_URL}/auth/signin/",
            'support_email': 'support@chrp-india.com',
            'company_name': 'CHRP India',
            'site_url': settings.SITE_URL,
            'year': datetime.now().year,
        }
        
        print(f"Rendering template...")
        html_message = render_to_string('emails/employee_welcome.html', context)
        print(f"Template rendered: {len(html_message)} chars")
        
        plain_message = strip_tags(html_message)
        
        subject = 'Welcome to CHRP - Your Employee Account'
        from_email = settings.DEFAULT_FROM_EMAIL
        to_email = [user.email]
        
        print(f"From: {from_email}")
        print(f"To: {to_email}")
        print(f"Sending email...")
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=to_email,
        )
        
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        print("EMAIL SENT SUCCESSFULLY!")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        traceback.print_exc()
        print("="*80 + "\n")
        return False

def send_customer_welcome_email(user):
    """
    ✅ Manually send customer welcome email (without password)
    
    This should be called from customer registration view after successful registration.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    from datetime import datetime
    
    print("\n" + "="*80)
    print("🔍 DEBUGGING CUSTOMER WELCOME EMAIL")
    print("="*80)
    print(f"📧 Attempting to send email to: {user.email}")
    print(f"👤 Customer Name: {user.get_full_name()}")
    print(f"📅 Timestamp: {datetime.now()}")
    print("="*80 + "\n")
    
    try:
        current_year = datetime.now().year
        
        context = {
            'user': user,
            'login_url': f"{settings.SITE_URL}/auth/signin/",
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'reach@chrp-india.com'),
            'company_name': 'CHRP India',
            'site_url': settings.SITE_URL,
            'year': current_year,
        }
        
        html_message = render_to_string('emails/customer_welcome.html', context)
        plain_message = strip_tags(html_message)
        
        email = EmailMultiAlternatives(
            subject='Welcome to CHRP - Registration Successful',
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        print("✅ Customer welcome email sent successfully!")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to send customer welcome email: {str(e)}")
        print(traceback.format_exc())
        print("="*80 + "\n")
        
        return False


# ✅ DISABLED: Email verification signal
@receiver(post_save, sender=CustomUser)
def send_verification_email_if_needed(sender, instance, created, **kwargs):
    """
    ✅ DISABLED: No automatic verification emails
    
    If you need verification emails, send them manually from the view.
    """
    pass
