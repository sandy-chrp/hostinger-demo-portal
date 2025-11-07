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
    """
    ✅ Send employee welcome email with temporary password
    
    This should ONLY be called from user_add view when admin chooses to send email.
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    
    from datetime import datetime
    
    print("\n" + "="*80)
    print("🔍 DEBUGGING EMPLOYEE WELCOME EMAIL")
    print("="*80)
    print(f"📧 Attempting to send email to: {user.email}")
    print(f"👤 Employee Name: {user.get_full_name()}")
    print(f"🆔 Employee ID: {user.employee_id}")
    print(f"🔑 Password provided: {'Yes' if temporary_password else 'No'}")
    print(f"📅 Timestamp: {datetime.now()}")
    print("="*80 + "\n")
    
    try:
        current_year = datetime.now().year
        
        # Prepare context
        context = {
            'user': user,
            'password': temporary_password,  # Include password in context
            'login_url': f"{settings.SITE_URL}/auth/signin/",
            'support_email': getattr(settings, 'SUPPORT_EMAIL', 'reach@chrp-india.com'),
            'company_name': 'CHRP India',
            'site_url': settings.SITE_URL,
            'year': current_year,
        }
        
        print("📋 Context prepared:")
        print(f"   - User: {user.email}")
        print(f"   - Password: {'*' * len(temporary_password) if temporary_password else 'None'}")
        print(f"   - Login URL: {context['login_url']}")
        print(f"   - Support Email: {context['support_email']}")
        
        # Try to render the email template
        print("\n🎨 Attempting to render template: 'emails/employee_welcome.html'")
        
        try:
            html_message = render_to_string('emails/employee_welcome.html', context)
            print("✅ Template rendered successfully!")
            print(f"   - HTML length: {len(html_message)} characters")
        except Exception as template_error:
            print(f"❌ Template rendering failed: {template_error}")
            print("\n🔍 Trying alternative template names...")
            
            # Try alternative template names
            alternative_templates = [
                'emails/employee_welcome_email.html',
                'emails/welcome_employee.html',
                'accounts/emails/employee_welcome.html',
            ]
            
            template_found = False
            for alt_template in alternative_templates:
                try:
                    print(f"   Trying: {alt_template}")
                    html_message = render_to_string(alt_template, context)
                    print(f"   ✅ Success with: {alt_template}")
                    template_found = True
                    break
                except:
                    print(f"   ❌ Not found: {alt_template}")
                    continue
            
            if not template_found:
                print("\n❌ No template found! Creating fallback HTML email...")
                # Create a simple fallback email
                html_message = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Welcome to CHRP</title>
                </head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h1 style="color: #087fc2;">Welcome to CHRP, {user.first_name}!</h1>
                        
                        <p>Your employee account has been successfully created.</p>
                        
                        <div style="background-color: #f8f9fa; padding: 20px; border-left: 4px solid #087fc2; margin: 20px 0;">
                            <h3>Your Login Credentials:</h3>
                            <p><strong>Employee ID:</strong> {user.employee_id}</p>
                            <p><strong>Email:</strong> {user.email}</p>
                            <p><strong>Temporary Password:</strong> <code style="background: #fff; padding: 2px 8px; border-radius: 4px;">{temporary_password}</code></p>
                        </div>
                        
                        <p>Please login and change your password immediately:</p>
                        <p><a href="{context['login_url']}" style="background-color: #087fc2; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Login Now</a></p>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                        
                        <p style="color: #666; font-size: 12px;">
                            If you need assistance, contact us at {context['support_email']}
                        </p>
                    </div>
                </body>
                </html>
                """
                print("✅ Fallback HTML email created")
        
        # Create plain text version
        plain_message = strip_tags(html_message)
        print(f"\n📄 Plain text version created ({len(plain_message)} characters)")
        
        # Prepare email
        print("\n📧 Preparing email message...")
        subject = 'Welcome to CHRP - Your Employee Account is Ready'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@chrp-india.com')
        to_email = [user.email]
        
        print(f"   - Subject: {subject}")
        print(f"   - From: {from_email}")
        print(f"   - To: {to_email}")
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=from_email,
            to=to_email,
        )
        
        # Attach HTML version
        email.attach_alternative(html_message, "text/html")
        print("✅ Email message prepared with HTML alternative")
        
        # Send email
        print("\n📤 Sending email...")
        email.send(fail_silently=False)
        print("✅ EMAIL SENT SUCCESSFULLY!")
        
        print("\n" + "="*80)
        print(f"✅ SUCCESS: Employee welcome email sent to {user.email}")
        print("="*80 + "\n")
        
        return True
        
    except Exception as e:
        print("\n" + "="*80)
        print("❌ ERROR SENDING EMPLOYEE WELCOME EMAIL")
        print("="*80)
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print("\nFull Traceback:")
        print(traceback.format_exc())
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
