# core/admin_customer_views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse  # ⭐ YEH LINE ADD KAREIN
from datetime import datetime
import json
import uuid
import csv
from accounts.decorators import permission_required

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from smtplib import SMTPException

# ⭐ YEH BHI ADD KAREIN (pandas ke liye)
import pandas as pd
from accounts.models import BusinessCategory, BusinessSubCategory  # ⭐ Models import karein

from .customer_admin_forms import CustomerCreateForm, CustomerEditForm

User = get_user_model()



def is_admin(user):
    """Check if user is admin/staff"""
    return user.is_authenticated and user.is_staff

@login_required
@permission_required('view_customers')
@user_passes_test(is_admin)
def admin_customers_list(request):
    """Admin view for listing all customers with all database columns"""
    from core.models import AdminColumnPreference
    
    # ALL AVAILABLE COLUMNS FROM DATABASE
    ALL_COLUMNS = [
        {'id': 'checkbox', 'label': 'Select All', 'width': '50px', 'sortable': False, 'always_visible': False},  # ✅ Changed to False
        {'id': 'customer_id', 'label': 'ID', 'width': '80px', 'sortable': True},
        {'id': 'customer', 'label': 'Customer Name', 'width': 'auto', 'sortable': True},
        {'id': 'email', 'label': 'Email', 'width': 'auto', 'sortable': True},
        {'id': 'mobile', 'label': 'Mobile', 'width': 'auto', 'sortable': True},
        {'id': 'country_code', 'label': 'Country Code', 'width': 'auto', 'sortable': True},
        {'id': 'organization', 'label': 'Organization', 'width': 'auto', 'sortable': True},
        {'id': 'job_title', 'label': 'Job Title', 'width': 'auto', 'sortable': True},
        {'id': 'business_category', 'label': 'Business Category', 'width': 'auto', 'sortable': True},
        {'id': 'business_subcategory', 'label': 'Business Subcategory', 'width': 'auto', 'sortable': True},
        {'id': 'status', 'label': 'Status', 'width': 'auto', 'sortable': True},
        {'id': 'is_email_verified', 'label': 'Email Verified', 'width': 'auto', 'sortable': True},
        {'id': 'is_approved', 'label': 'Approved', 'width': 'auto', 'sortable': True},
        {'id': 'is_active', 'label': 'Active', 'width': 'auto', 'sortable': True},
        {'id': 'registration', 'label': 'Registration Date', 'width': 'auto', 'sortable': True},
        {'id': 'last_login', 'label': 'Last Login', 'width': 'auto', 'sortable': True},
        {'id': 'last_login_ip', 'label': 'Last Login IP', 'width': 'auto', 'sortable': True},
        {'id': 'referral_source', 'label': 'Referral Source', 'width': 'auto', 'sortable': True},
        {'id': 'referral_message', 'label': 'Referral Message', 'width': 'auto', 'sortable': False},
        {'id': 'country', 'label': 'Country', 'width': 'auto', 'sortable': True},
        {'id': 'actions', 'label': 'Actions', 'width': '150px', 'sortable': False, 'always_visible': True},  # Actions always visible
    ]
    
    # Default visible columns (commonly used)
    DEFAULT_COLUMNS = [
        'checkbox',  # ✅ Include checkbox in default
        'customer',
        'email',
        'mobile',
        'organization',
        'job_title',
        'business_category',
        'status',
        'registration',
        'last_login',
        'actions'
    ]
    
    # Get user's column preferences
    visible_columns = AdminColumnPreference.get_user_preferences(
        user=request.user,
        table_name='customers',
        default_columns=DEFAULT_COLUMNS
    )
    
    # Get filter parameters
    search = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    business_category_filter = request.GET.get('business_category', '')
    referral_source_filter = request.GET.get('referral_source', '')
    email_verified_filter = request.GET.get('email_verified', '')
    country_filter = request.GET.get('country', '')
    
    # Base queryset
    customers = User.objects.filter(is_staff=False).select_related(
        'business_category',
        'business_subcategory'
    )
    
    # Apply search filter
    if search:
        customers = customers.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(organization__icontains=search) |
            Q(job_title__icontains=search) |
            Q(mobile__icontains=search)
        )
    
    # Apply status filter
    if status_filter == 'active':
        customers = customers.filter(is_approved=True, is_active=True)
    elif status_filter == 'pending':
        customers = customers.filter(is_approved=False)
    elif status_filter == 'blocked':
        customers = customers.filter(is_active=False)
    
    # Apply business category filter
    if business_category_filter:
        customers = customers.filter(business_category_id=business_category_filter)
    
    # Apply referral source filter
    if referral_source_filter:
        customers = customers.filter(referral_source=referral_source_filter)
    
    # Apply email verified filter
    if email_verified_filter:
        customers = customers.filter(is_email_verified=(email_verified_filter == 'yes'))
    
    # Apply country filter
    if country_filter:
        customers = customers.filter(country_code=country_filter)
    
    # Apply date range filter
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            customers = customers.filter(created_at__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            customers = customers.filter(created_at__lt=to_date)
        except ValueError:
            pass
    
    # Get statistics
    total_customers = User.objects.filter(is_staff=False).count()
    active_customers = User.objects.filter(is_staff=False, is_approved=True, is_active=True).count()
    pending_approvals = User.objects.filter(is_staff=False, is_approved=False).count()
    blocked_customers = User.objects.filter(is_staff=False, is_active=False).count()
    
    # Get filter options
    from accounts.models import BusinessCategory
    business_categories = BusinessCategory.objects.filter(is_active=True).order_by('name')
    
    # Get unique country codes
    country_codes = User.objects.filter(is_staff=False).values_list('country_code', flat=True).distinct()
    
    # Referral source choices
    referral_sources = User.REFERRAL_CHOICES
    
    # Pagination
    paginator = Paginator(customers.order_by('-created_at'), 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search': search,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'business_category_filter': business_category_filter,
        'referral_source_filter': referral_source_filter,
        'email_verified_filter': email_verified_filter,
        'country_filter': country_filter,
        'total_customers': total_customers,
        'active_customers': active_customers,
        'pending_approvals': pending_approvals,
        'blocked_customers': blocked_customers,
        'visible_columns': visible_columns,
        'all_columns': ALL_COLUMNS,
        'business_categories': business_categories,
        'referral_sources': referral_sources,
        'country_codes': country_codes,
    }
    
    return render(request, 'admin/customers/list.html', context)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def save_column_preferences(request):
    """Save admin's column visibility preferences"""
    from core.models import AdminColumnPreference
    
    try:
        data = json.loads(request.body)
        table_name = data.get('table_name')
        visible_columns = data.get('visible_columns', [])
        
        if not table_name:
            return JsonResponse({
                'success': False,
                'message': 'Table name is required'
            })
        
        # Update or create preference
        preference = AdminColumnPreference.update_preferences(
            user=request.user,
            table_name=table_name,
            visible_columns=visible_columns
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Column preferences saved successfully',
            'visible_columns': preference.visible_columns
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving preferences: {str(e)}'
        })

@login_required
@permission_required('add_customer')
@user_passes_test(is_admin)
def admin_create_customer(request):
    """Admin view for creating new customer - FIXED WITH OTP EMAIL"""
    
    if request.method == 'POST':
        form = CustomerCreateForm(request.POST)
        
        if form.is_valid():
            try:
                email = form.cleaned_data['email']
                
                # ✅ CHECK 1: Verify email was validated via OTP (if OTP was required)
                # This assumes your form has email_verified field or you track it in session
                # For now, we'll proceed with creation
                
                # Create customer
                customer = form.save(commit=False)
                customer.is_email_verified = True  # Admin creates, so auto-verify
                customer.is_approved = form.cleaned_data.get('is_approved', True)
                customer.is_active = True
                customer.save()
                
                print(f"\n{'='*60}")
                print(f"✅ CUSTOMER CREATED")
                print(f"   Email: {customer.email}")
                print(f"   Name: {customer.full_name}")
                print(f"{'='*60}\n")
                
                # ✅ SEND WELCOME EMAIL (Always send for admin-created customers)
                send_welcome_email = form.cleaned_data.get('send_welcome_email', True)
                
                if send_welcome_email:
                    try:
                        result = send_customer_welcome_email_with_validation(
                            customer, 
                            request.user,
                            request  # ✅ Pass request object
                        )
                        
                        if result['success']:
                            messages.success(
                                request, 
                                f'✅ Customer created! Welcome email sent to {customer.email}'
                            )
                        else:
                            if result['error'] == 'invalid_recipient':
                                messages.warning(
                                    request,
                                    f'⚠️ Customer created but email "{customer.email}" does not exist. '
                                    f'Please verify the email address with customer.'
                                )
                            else:
                                messages.warning(
                                    request,
                                    f'⚠️ Customer created but welcome email failed to send. '
                                    f'Error: {result.get("error", "Unknown")}'
                                )
                    except Exception as e:
                        print(f"❌ Email error: {e}")
                        messages.warning(
                            request,
                            f'Customer created but email failed: {str(e)}'
                        )
                else:
                    messages.success(
                        request, 
                        f'✅ Customer "{customer.full_name}" created successfully!'
                    )
                
                return redirect('core:admin_users')
                    
            except Exception as e:
                print(f"❌ Error creating customer: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f'Error creating customer: {str(e)}')
        else:
            # Form validation errors
            print("❌ Form validation errors:")
            for field, errors in form.errors.items():
                print(f"   {field}: {errors}")
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerCreateForm()
    
    return render(request, 'admin/customers/create.html', {
        'form': form,
        'title': 'Create New Customer'
    })

def send_customer_welcome_email_with_validation(customer, created_by):
    """Send welcome email with delivery validation"""
    from django.core.mail import EmailMessage
    from smtplib import SMTPException
    
    try:
        site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
        
        subject = 'Welcome to Demo Portal'
        message = f"""
Dear {customer.first_name} {customer.last_name},

Welcome to Demo Portal!

Your account has been created by our admin team.

Account Details:
- Email: {customer.email}
- Organization: {customer.organization}
- Job Title: {customer.job_title}

Sign in here: {site_url}/auth/signin/

Use the "Forgot Password" option to set your password.

Best regards,
Demo Portal Team
CHRP India
        """
        
        email_msg = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        email_msg.send(fail_silently=False)
        
        return {'success': True, 'error': None}
    
    except SMTPException as e:
        error_msg = str(e)
        print(f"SMTP Error sending welcome email: {error_msg}")
        
        if "550" in error_msg or "recipient" in error_msg.lower():
            return {'success': False, 'error': 'invalid_recipient'}
        elif "authentication" in error_msg.lower():
            return {'success': False, 'error': 'auth_failed'}
        else:
            return {'success': False, 'error': 'smtp_error'}
    
    except Exception as e:
        print(f"General email error: {e}")
        return {'success': False, 'error': 'unknown'}


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def send_email_otp(request):
    """Send OTP to email for verification - IMPROVED"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        
        print(f"\n{'='*60}")
        print(f"📧 OTP REQUEST")
        print(f"   Email: {email}")
        print(f"{'='*60}")
        
        if not email:
            return JsonResponse({
                'success': False, 
                'message': 'Email is required'
            })
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            print(f"❌ Email already exists")
            return JsonResponse({
                'success': False, 
                'message': 'Email already registered'
            })
        
        # Generate OTP
        from accounts.models import EmailOTP
        otp_code = EmailOTP.generate_otp()
        
        # Delete old OTPs for this email
        EmailOTP.objects.filter(email=email, verified=False).delete()
        
        # Create new OTP
        otp_obj = EmailOTP.objects.create(
            email=email,
            otp=otp_code
        )
        
        print(f"🔐 Generated OTP: {otp_code}")
        print(f"⏰ Expires at: {otp_obj.expires_at}")
        
        # ✅ SEND HTML EMAIL
        subject = '🔐 Email Verification OTP - Demo Portal'
        
        context = {
            'otp_code': otp_code,
            'email': email,
            'expires_in': 10,  # minutes
            'year': timezone.now().year,
        }
        
        try:
            # Try HTML template first
            html_content = render_to_string('emails/email_otp.html', context)
            text_content = f"""
Demo Portal - Email Verification

Your OTP for email verification is: {otp_code}

This OTP will expire in 10 minutes.

If you did not request this, please ignore this email.

Best regards,
Demo Portal Team
CHRP India
            """
            
            email_msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send(fail_silently=False)
            
            print(f"✅ OTP email sent (HTML)")
            
        except Exception as template_error:
            # Fallback to plain text if template fails
            print(f"⚠️ Template error: {template_error}")
            print(f"📧 Sending plain text email instead")
            
            from django.core.mail import send_mail
            
            text_content = f"""
Dear User,

Your OTP for email verification is: {otp_code}

This OTP will expire in 10 minutes.

If you did not request this, please ignore this email.

Best regards,
Demo Portal Team
            """
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            
            print(f"✅ OTP email sent (Plain Text)")
        
        print(f"{'='*60}\n")
        
        return JsonResponse({
            'success': True,
            'message': f'OTP sent to {email}',
            'expires_in': 600  # 10 minutes in seconds
        })
        
    except Exception as e:
        print(f"❌ Error sending OTP: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        return JsonResponse({
            'success': False,
            'message': 'Failed to send OTP. Please try again.'
        })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def verify_email_otp(request):
    """Verify OTP - IMPROVED"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        otp_entered = data.get('otp', '').strip()
        
        print(f"\n{'='*60}")
        print(f"🔐 OTP VERIFICATION")
        print(f"   Email: {email}")
        print(f"   OTP Entered: {otp_entered}")
        print(f"{'='*60}")
        
        if not email or not otp_entered:
            return JsonResponse({
                'success': False, 
                'message': 'Email and OTP required'
            })
        
        from accounts.models import EmailOTP
        
        # Get latest OTP for this email
        otp_obj = EmailOTP.objects.filter(
            email=email, 
            verified=False
        ).order_by('-created_at').first()
        
        if not otp_obj:
            print(f"❌ No OTP found")
            return JsonResponse({
                'success': False, 
                'message': 'No OTP found. Please request new OTP.'
            })
        
        print(f"📝 OTP in database: {otp_obj.otp}")
        print(f"⏰ Expires at: {otp_obj.expires_at}")
        print(f"🕐 Current time: {timezone.now()}")
        
        if not otp_obj.is_valid():
            print(f"❌ OTP expired")
            return JsonResponse({
                'success': False, 
                'message': 'OTP expired. Please request new OTP.'
            })
        
        if otp_obj.otp != otp_entered:
            print(f"❌ OTP mismatch")
            return JsonResponse({
                'success': False, 
                'message': 'Invalid OTP. Please try again.'
            })
        
        # Mark as verified
        otp_obj.verified = True
        otp_obj.save()
        
        print(f"✅ OTP verified successfully")
        print(f"{'='*60}\n")
        
        return JsonResponse({
            'success': True,
            'message': 'Email verified successfully!'
        })
        
    except Exception as e:
        print(f"❌ Error verifying OTP: {e}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        return JsonResponse({
            'success': False,
            'message': 'Verification failed. Please try again.'
        })

@login_required
@permission_required('edit_customer')
@user_passes_test(is_admin)
def admin_edit_customer(request, customer_id):
    """Admin view for editing existing customer"""
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    
    if request.method == 'POST':
        form = CustomerEditForm(request.POST, instance=customer)
        if form.is_valid():
            try:
                # Save changes
                old_email = customer.email
                old_status = (customer.is_approved, customer.is_active)
                
                customer = form.save()
                
                # Check for email change
                if old_email != customer.email:
                    customer.is_email_verified = False
                    customer.email_verification_token = str(uuid.uuid4())
                    customer.save()
                    messages.info(request, 'Email changed. Customer will need to verify their new email.')
                
                # Check for status change
                new_status = (customer.is_approved, customer.is_active)
                if old_status != new_status:
                    send_status_change_notification(customer, old_status, new_status)
                
                messages.success(request, f'Customer "{customer.full_name}" updated successfully!')
                
                # Redirect based on action
                if 'save_and_continue' in request.POST:
                    return redirect('core:admin_edit_customer', customer.id)
                else:
                    return redirect('core:admin_users')
                    
            except Exception as e:
                messages.error(request, f'Error updating customer: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomerEditForm(instance=customer)
    
    # Get customer statistics
    customer_stats = get_customer_statistics(customer)
    
    return render(request, 'admin/customers/edit.html', {
        'form': form,
        'customer': customer,
        'customer_stats': customer_stats,
        'title': f'Edit Customer - {customer.full_name}'
    })

def get_customer_statistics(customer):
    """Get statistics for a customer"""
    try:
        from demos.models import DemoView, DemoRequest
        from enquiries.models import BusinessEnquiry
        
        demo_views = DemoView.objects.filter(user=customer).count()
        demo_requests = DemoRequest.objects.filter(user=customer).count()
        enquiries = BusinessEnquiry.objects.filter(user=customer).count()
        
        # Calculate engagement score (simple formula)
        engagement_score = min(100, (demo_views * 2 + demo_requests * 10 + enquiries * 15))
        
        # Get last activity
        last_activity = None
        last_demo_view = DemoView.objects.filter(user=customer).order_by('-viewed_at').first()
        if last_demo_view:
            last_activity = (last_demo_view.viewed_at, f"Viewed {last_demo_view.demo.title}")
        
        return {
            'total_demo_views': demo_views,
            'total_demo_requests': demo_requests,
            'total_enquiries': enquiries,
            'demo_views': demo_views,  # Template uses this
            'demo_requests': demo_requests,  # Template uses this
            'enquiries': enquiries,  # Template uses this
            'engagement_score': engagement_score,
            'account_age_days': (timezone.now() - customer.created_at).days if hasattr(customer, 'created_at') else 0,
            'last_activity': last_activity if last_activity else (None, 'No activity yet'),
        }
    except Exception as e:
        print(f"Error getting customer stats: {e}")
        return {
            'total_demo_views': 0,
            'total_demo_requests': 0,
            'total_enquiries': 0,
            'demo_views': 0,
            'demo_requests': 0,
            'enquiries': 0,
            'engagement_score': 0,
            'account_age_days': 0,
            'last_activity': (None, 'No activity'),
        }

@login_required
@user_passes_test(is_admin)
def admin_customer_detail(request, customer_id):
    """Admin view for customer details"""
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    customer_stats = get_customer_statistics(customer)
    
    return render(request, 'admin/customers/detail.html', {
        'customer': customer,
        'customer_stats': customer_stats,
        'title': f'Customer Details - {customer.full_name}'
    })

@login_required
@permission_required('approve_customer')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_approve_customer(request, customer_id):
    """Approve customer account"""
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    
    if not customer.is_approved:
        customer.is_approved = True
        customer.is_active = True
        customer.save()
        
        # Send approval notification
        send_approval_notification(customer)
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True, 
                'message': f'{customer.full_name} has been approved and notified.'
            })
        else:
            messages.success(request, f'{customer.full_name} has been approved and notified.')
    
    return redirect('core:admin_users')

@login_required
@user_passes_test(is_admin)
@permission_required('block_customer')
@require_http_methods(["POST"])
def admin_block_customer(request, customer_id):
    """Block customer account and send notification email"""
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    
    if customer.is_active:
        # Block the customer
        customer.is_active = False
        customer.save()
        
        # ✅ SEND EMAIL NOTIFICATION
        send_account_blocked_notification(customer)
        
        # ✅ KILL ALL ACTIVE SESSIONS
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        
        for session in Session.objects.filter(expire_date__gte=timezone.now()):
            session_data = session.get_decoded()
            if session_data.get('_auth_user_id') == str(customer.id):
                session.delete()
        
        if request.content_type == 'application/json':
            return JsonResponse({
                'success': True, 
                'message': f'{customer.full_name} has been blocked and notified via email.'
            })
        else:
            messages.warning(request, f'{customer.full_name} has been blocked and notified via email.')
    
    return redirect('core:admin_users')


@login_required
@permission_required('block_customer')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_unblock_customer(request, customer_id):
    """Unblock customer account and send notification (email + in-app)"""
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    
    if not customer.is_active:
        # ✅ REACTIVATE BOTH FLAGS
        customer.is_active = True
        customer.is_approved = True  
        customer.save()
        
        # ✅ SEND NOTIFICATION (EMAIL + IN-APP)
        from notifications.services import NotificationService
        NotificationService.notify_account_unblocked(customer, send_email=True)
        
        return JsonResponse({
            'success': True, 
            'message': f'{customer.full_name} has been unblocked and notified.'
        })
    
    return JsonResponse({
        'success': False, 
        'message': 'Customer is already active.'
    })

@login_required
@permission_required('delete_customer') 
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_delete_customer(request, customer_id):
    """Delete customer account"""
    customer = get_object_or_404(User, id=customer_id, is_staff=False)
    
    # Get statistics before deletion
    demo_views = customer.demo_views.count()
    demo_requests = customer.demo_requests.count()
    enquiries = customer.enquiries.count()
    
    customer_name = customer.full_name
    customer.delete()
    
    return JsonResponse({
        'success': True, 
        'message': f'{customer_name} has been permanently deleted.',
        'stats': {
            'demo_views': demo_views,
            'demo_requests': demo_requests,
            'enquiries': enquiries
        }
    })

@login_required
@permission_required('edit_customer')
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_bulk_customer_actions(request):
    """Handle bulk actions on customers"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        customer_ids = data.get('customer_ids', [])
        
        if not customer_ids:
            return JsonResponse({'success': False, 'message': 'No customers selected.'})
        
        customers = User.objects.filter(id__in=customer_ids, is_staff=False)
        count = customers.count()
        
        if count == 0:
            return JsonResponse({'success': False, 'message': 'No valid customers found.'})
        
        if action == 'approve':
            customers.update(is_approved=True, is_active=True)
            message = f'{count} customers approved successfully.'
            
        elif action == 'block':
            customers.update(is_active=False)
            message = f'{count} customers blocked successfully.'
            
        elif action == 'unblock':
            customers.update(is_active=True)
            message = f'{count} customers unblocked successfully.'
            
        elif action == 'delete':
            customers.delete()
            message = f'{count} customers deleted permanently.'
            
        else:
            return JsonResponse({'success': False, 'message': 'Invalid action.'})
        
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


@login_required
@permission_required('view_customers')
@user_passes_test(is_admin)
def admin_customer_export_view(request):
    """Export customer data to CSV with visible columns only"""
    from core.models import AdminColumnPreference
    
    # Get user's visible columns
    visible_columns = AdminColumnPreference.get_user_preferences(
        user=request.user,
        table_name='customers',
        default_columns=[
            'customer', 'contact', 'organization', 'job_title',
            'business_category', 'status', 'registration', 
            'last_login', 'referral_source', 'country'
        ]
    )
    
    # Remove non-exportable columns
    non_exportable = ['checkbox', 'actions']
    exportable_columns = [col for col in visible_columns if col not in non_exportable]
    
    # Column mapping to CSV headers and data extraction
    COLUMN_CONFIG = {
        'customer': {
            'header': 'Name',
            'getter': lambda u: u.full_name
        },
        'contact': {
            'header': 'Email',
            'getter': lambda u: u.email,
            'extra_headers': ['Phone'],
            'extra_getters': [lambda u: u.full_mobile]
        },
        'organization': {
            'header': 'Organization',
            'getter': lambda u: u.organization or 'Not specified'
        },
        'job_title': {
            'header': 'Job Title',
            'getter': lambda u: u.job_title or 'Not specified'
        },
        'business_category': {
            'header': 'Business Category',
            'getter': lambda u: u.business_category.name if u.business_category else 'Not specified',
            'extra_headers': ['Business Subcategory'],
            'extra_getters': [lambda u: u.business_subcategory.name if u.business_subcategory else 'Not specified']
        },
        'status': {
            'header': 'Status',
            'getter': lambda u: (
                'Active' if u.is_approved and u.is_active else
                'Blocked' if u.is_approved and not u.is_active else 'Pending'
            ),
            'extra_headers': ['Email Verified'],
            'extra_getters': [lambda u: 'Yes' if u.is_email_verified else 'No']
        },
        'registration': {
            'header': 'Registration Date',
            'getter': lambda u: u.created_at.strftime('%Y-%m-%d %H:%M:%S')
        },
        'last_login': {
            'header': 'Last Login',
            'getter': lambda u: u.last_login.strftime('%Y-%m-%d %H:%M:%S') if u.last_login else 'Never'
        },
        'referral_source': {
            'header': 'Referral Source',
            'getter': lambda u: u.get_referral_source_display() or 'Not specified'
        },
        'country': {
            'header': 'Country',
            'getter': lambda u: get_country_name(u.country_code)
        }
    }
    
    # Get filter parameters
    status_filter = request.GET.get('status')
    search = request.GET.get('search')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Filter customers
    customers = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).select_related('business_category', 'business_subcategory').order_by('-created_at')
    
    # Apply filters (same as list view)
    if status_filter == 'pending':
        customers = customers.filter(is_approved=False)
    elif status_filter == 'approved':
        customers = customers.filter(is_approved=True)
    elif status_filter == 'blocked':
        customers = customers.filter(is_active=False)
    elif status_filter == 'active':
        customers = customers.filter(is_active=True, is_approved=True)
    
    if search:
        customers = customers.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(organization__icontains=search)
        )
    
    if date_from:
        try:
            from_date = datetime.strptime(date_from, '%Y-%m-%d')
            customers = customers.filter(created_at__gte=from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            customers = customers.filter(created_at__lt=to_date)
        except ValueError:
            pass
    
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="customers_export_{timestamp}.csv"'
    
    writer = csv.writer(response)
    
    # Build headers based on visible columns
    headers = []
    for col_id in exportable_columns:
        if col_id in COLUMN_CONFIG:
            config = COLUMN_CONFIG[col_id]
            headers.append(config['header'])
            if 'extra_headers' in config:
                headers.extend(config['extra_headers'])
    
    writer.writerow(headers)
    
    # Write customer data
    for customer in customers:
        row = []
        for col_id in exportable_columns:
            if col_id in COLUMN_CONFIG:
                config = COLUMN_CONFIG[col_id]
                row.append(config['getter'](customer))
                if 'extra_getters' in config:
                    for getter in config['extra_getters']:
                        row.append(getter(customer))
        writer.writerow(row)
    
    return response


def get_country_name(country_code):
    """Extract country name from country code"""
    country_map = {
        '+91': 'India',
        '+1': 'United States',
        '+44': 'United Kingdom',
        '+86': 'China',
        '+81': 'Japan',
        '+49': 'Germany',
        '+33': 'France',
        '+39': 'Italy',
        '+34': 'Spain',
        '+7': 'Russia',
        # Add more as needed
    }
    return country_map.get(country_code, 'Not specified')

def send_approval_notification(customer, request=None):
    """
    Send account approval email using HTML template
    
    Args:
        customer: User instance
        request: HttpRequest instance (optional)
    """
    try:
        # Build login URL
        if request:
            login_url = request.build_absolute_uri(reverse('accounts:signin'))
        else:
            site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            login_url = f"{site_url}/auth/signin/"
        
        subject = "🎉 Your Demo Portal Account is Approved!"
        
        # Context for template
        context = {
            'user': customer,
            'login_url': login_url,
            'year': timezone.now().year,
        }
        
        # Render HTML template
        try:
            html_content = render_to_string('emails/account_approved.html', context)
        except Exception as e:
            print(f"Template error: {e}")
            html_content = None
        
        # Plain text fallback
        text_content = f"""
CHRP India - Demo Portal
🎉 Account Approved!

Dear {customer.full_name},

Great news! Your Demo Portal account has been APPROVED.

Account Details:
• Name: {customer.full_name}
• Email: {customer.email}
• Organization: {customer.organization}
• Status: ✅ Active

Access Your Dashboard: {login_url}

Need Help?
📧 reach@chrp-india.com
📞 +91-8008987948

© {timezone.now().year} CHRP India. All rights reserved.
"""
        
        print("\n" + "="*60)
        print("📧 APPROVAL EMAIL")
        print(f"To: {customer.email}")
        print(f"Name: {customer.full_name}")
        print("="*60 + "\n")
        
        # Send email
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        
        if html_content:
            email_msg.attach_alternative(html_content, "text/html")
        
        email_msg.send(fail_silently=False)
        
        print(f"✅ Approval email sent\n")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False


def send_customer_welcome_email_with_validation(customer, created_by, request=None):
    """
    Send welcome email to admin-created customer using HTML template
    
    Args:
        customer: User instance
        created_by: Admin user who created the account
        request: HttpRequest instance (optional)
    """
    try:
        # Build login URL
        if request:
            login_url = request.build_absolute_uri(reverse('accounts:signin'))
        else:
            site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            login_url = f"{site_url}/auth/signin/"
        
        subject = "Welcome to Demo Portal - CHRP India"
        
        # Context for template
        context = {
            'user': customer,
            'login_url': login_url,
            'year': timezone.now().year,
        }
        
        # Render HTML template
        try:
            html_content = render_to_string('emails/admin_created_welcome.html', context)
        except Exception as e:
            print(f"Template error: {e}")
            html_content = None
        
        # Plain text fallback
        text_content = f"""
CHRP India - Demo Portal
Welcome!

Dear {customer.full_name},

Your account has been created by our admin team.

Account Details:
• Name: {customer.full_name}
• Email: {customer.email}
• Organization: {customer.organization}
• Job Title: {customer.job_title}

Getting Started:
1. Visit the login page: {login_url}
2. Click "Forgot Password" to set your password
3. Check your email for password reset link
4. Set your password and sign in

Need Help?
📧 reach@chrp-india.com
📞 +91-8008987948

© {timezone.now().year} CHRP India. All rights reserved.
"""
        
        print("\n" + "="*60)
        print("📧 WELCOME EMAIL")
        print(f"To: {customer.email}")
        print(f"Name: {customer.full_name}")
        print("="*60 + "\n")
        
        # Send email
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        
        if html_content:
            email_msg.attach_alternative(html_content, "text/html")
        
        email_msg.send(fail_silently=False)
        
        print(f"✅ Welcome email sent\n")
        return {'success': True, 'error': None}
        
    except SMTPException as e:
        error_msg = str(e)
        print(f"❌ SMTP Error: {error_msg}\n")
        
        if "550" in error_msg or "recipient" in error_msg.lower():
            return {'success': False, 'error': 'invalid_recipient'}
        elif "authentication" in error_msg.lower():
            return {'success': False, 'error': 'auth_failed'}
        else:
            return {'success': False, 'error': 'smtp_error'}
    
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return {'success': False, 'error': 'unknown'}

def send_status_change_notification(customer, old_status, new_status, request=None):
    """
    Send notification when customer status changes
    
    Args:
        customer: User instance
        old_status: Tuple (old_is_approved, old_is_active)
        new_status: Tuple (new_is_approved, new_is_active)
        request: HttpRequest instance (optional)
    """
    old_approved, old_active = old_status
    new_approved, new_active = new_status
    
    # If approved status changed to True
    if old_approved != new_approved and new_approved:
        send_approval_notification(customer, request)
    
    # If blocked (active changed from True to False)
    elif old_active and not new_active:
        send_account_blocked_notification(customer)
    
    # If unblocked (active changed from False to True)
    elif not old_active and new_active and new_approved:
        send_account_unblocked_notification(customer, request)


def send_account_blocked_notification(customer):
    """
    Send account blocked notification using HTML template
    
    Args:
        customer: User instance
    """
    try:
        subject = "Account Status Update - Demo Portal"
        
        # Context for template
        context = {
            'user': customer,
            'year': timezone.now().year,
        }
        
        # Render HTML template
        try:
            html_content = render_to_string('emails/account_blocked.html', context)
        except Exception as e:
            print(f"Template error: {e}")
            html_content = None
        
        # Plain text fallback
        text_content = f"""
CHRP India - Demo Portal
Account Status Update

Dear {customer.full_name},

Your Demo Portal account has been temporarily suspended.

What this means:
• You cannot access your account
• Your login credentials are disabled
• Pending demo requests are paused

If you believe this is a mistake, please contact our support team.

Contact Support:
📧 reach@chrp-india.com
📞 +91-8008987948
🕐 9:00 AM - 7:00 PM (Mon-Sat)

© {timezone.now().year} CHRP India. All rights reserved.
"""
        
        print("\n" + "="*60)
        print("📧 ACCOUNT BLOCKED EMAIL")
        print(f"To: {customer.email}")
        print("="*60 + "\n")
        
        # Send email
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        
        if html_content:
            email_msg.attach_alternative(html_content, "text/html")
        
        email_msg.send(fail_silently=False)
        
        print(f"✅ Account blocked email sent\n")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def send_account_unblocked_notification(customer, request=None):
    """
    Send account reactivated email using HTML template
    
    Args:
        customer: User instance
        request: HttpRequest instance (optional)
    """
    try:
        # Build login URL
        if request:
            login_url = request.build_absolute_uri(reverse('accounts:signin'))
        else:
            site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            login_url = f"{site_url}/auth/signin/"
        
        subject = "✅ Account Reactivated - Demo Portal"
        
        # Context for template
        context = {
            'user': customer,
            'login_url': login_url,
            'year': timezone.now().year,
        }
        
        # Render HTML template
        try:
            html_content = render_to_string('emails/account_unblocked.html', context)
        except Exception as e:
            print(f"Template error: {e}")
            html_content = None
        
        # Plain text fallback
        text_content = f"""
CHRP India - Demo Portal
✅ Account Reactivated

Dear {customer.full_name},

Good news! Your Demo Portal account has been reactivated.

You can now sign in and access all features again.

Sign in here: {login_url}

Account Details:
• Name: {customer.full_name}
• Email: {customer.email}
• Status: ✅ Active

You can now:
✓ Access your dashboard and all features
✓ Browse and watch product demonstrations
✓ Request live demo sessions
✓ Submit business enquiries

Need Help?
📧 reach@chrp-india.com
📞 +91-8008987948
🕐 9:00 AM - 7:00 PM (Mon-Sat)

We're glad to have you back!

© {timezone.now().year} CHRP India. All rights reserved.
"""
        
        print("\n" + "="*60)
        print("📧 ACCOUNT UNBLOCKED EMAIL")
        print(f"To: {customer.email}")
        print(f"Name: {customer.full_name}")
        print("="*60 + "\n")
        
        # Send email
        email_msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[customer.email],
        )
        
        if html_content:
            email_msg.attach_alternative(html_content, "text/html")
        
        email_msg.send(fail_silently=False)
        
        print(f"✅ Account unblocked email sent\n")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return False

def get_customer_statistics(customer):
    """Get statistics for a customer"""
    try:
        from demos.models import DemoView, DemoRequest
        from enquiries.models import BusinessEnquiry
        
        return {
            'total_demo_views': DemoView.objects.filter(user=customer).count(),
            'total_demo_requests': DemoRequest.objects.filter(user=customer).count(),
            'total_enquiries': BusinessEnquiry.objects.filter(user=customer).count(),
            'account_age_days': (timezone.now() - customer.created_at).days if hasattr(customer, 'created_at') else 0,
        }
    except Exception as e:
        print(f"Error getting customer stats: {e}")
        return {
            'total_demo_views': 0,
            'total_demo_requests': 0,
            'total_enquiries': 0,
            'account_age_days': 0,
        }


@login_required
@permission_required('add_customer')
@user_passes_test(is_admin)
def admin_bulk_import_customers(request):
    """Bulk import customers from CSV/Excel"""
    if request.method == 'POST':
        if 'file' not in request.FILES:
            messages.error(request, 'Please select a file to upload.')
            return redirect('core:admin_bulk_import_customers')
        
        uploaded_file = request.FILES['file']
        file_extension = uploaded_file.name.split('.')[-1].lower()
        
        if file_extension not in ['csv', 'xlsx', 'xls']:
            messages.error(request, 'Invalid file format. Please upload CSV or Excel file.')
            return redirect('core:admin_bulk_import_customers')
        
        try:
            # Read file based on extension
            if file_extension == 'csv':
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            # Validate columns
            required_columns = ['first_name', 'last_name', 'email', 'mobile']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                messages.error(
                    request, 
                    f'Missing required columns: {", ".join(missing_columns)}'
                )
                return redirect('core:admin_bulk_import_customers')
            
            # Process data
            success_count = 0
            error_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # Clean data
                    email = str(row['email']).strip().lower()
                    mobile = str(row['mobile']).strip()
                    
                    # Remove country code if present in mobile
                    mobile = mobile.replace('+91', '').replace('+', '').strip()
                    if len(mobile) > 10:
                        mobile = mobile[-10:]
                    
                    # Validate mobile number
                    if not mobile.isdigit() or len(mobile) != 10:
                        errors.append(f"Row {index + 2}: Invalid mobile number '{mobile}'")
                        error_count += 1
                        continue
                    
                    # Check if user already exists
                    if User.objects.filter(email=email).exists():
                        errors.append(f"Row {index + 2}: Email '{email}' already exists")
                        error_count += 1
                        continue
                    
                    # Create username from email
                    username = email.split('@')[0] + str(uuid.uuid4())[:8]
                    
                    # Get optional fields
                    country_code = str(row.get('country_code', '+91')).strip()
                    job_title = str(row.get('job_title', '')).strip()
                    organization = str(row.get('organization', '')).strip()
                    
                    # Get business category if provided
                    business_category = None
                    business_subcategory = None
                    
                    if 'business_category' in df.columns and pd.notna(row.get('business_category')):
                        category_name = str(row['business_category']).strip()
                        business_category = BusinessCategory.objects.filter(
                            name__iexact=category_name,
                            is_active=True
                        ).first()
                    
                    if 'business_subcategory' in df.columns and pd.notna(row.get('business_subcategory')):
                        subcategory_name = str(row['business_subcategory']).strip()
                        if business_category:
                            business_subcategory = BusinessSubCategory.objects.filter(
                                name__iexact=subcategory_name,
                                category=business_category,
                                is_active=True
                            ).first()
                    
                    # Create user
                    user = User.objects.create(
                        username=username,
                        email=email,
                        first_name=str(row['first_name']).strip(),
                        last_name=str(row['last_name']).strip(),
                        mobile=mobile,
                        country_code=country_code,
                        job_title=job_title,
                        organization=organization,
                        business_category=business_category,
                        business_subcategory=business_subcategory,
                        is_email_verified=True,
                        is_approved=True,
                        is_active=True,
                        is_staff=False,
                        is_superuser=False
                    )
                    
                    # Set random password
                    random_password = User.objects.make_random_password()
                    user.set_password(random_password)
                    user.save()
                    
                    success_count += 1
                    
                    # Send welcome email if enabled
                    send_welcome_email = request.POST.get('send_welcome_emails') == 'on'
                    if send_welcome_email:
                        send_customer_welcome_email_with_validation(user, request.user)
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")
                    error_count += 1
                    continue
            
            # Show results
            if success_count > 0:
                messages.success(
                    request, 
                    f'Successfully imported {success_count} customers!'
                )
            
            if error_count > 0:
                error_message = f'{error_count} customers failed to import.'
                if len(errors) <= 10:
                    error_message += ' Errors: ' + '; '.join(errors)
                else:
                    error_message += f' First 10 errors: ' + '; '.join(errors[:10])
                messages.warning(request, error_message)
            
            if success_count == 0 and error_count == 0:
                messages.info(request, 'No customers were imported.')
            
            return redirect('core:admin_users')
            
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            return redirect('core:admin_bulk_import_customers')
    
    # GET request - show upload form
    context = {
        'title': 'Bulk Import Customers',
        'breadcrumbs': [
            {'title': 'Customers', 'url': reverse('core:admin_users')},
            {'title': 'Bulk Import'},
        ]
    }
    
    return render(request, 'admin/customers/bulk_import.html', context)


@login_required
@user_passes_test(is_admin)
def download_import_template(request):
    """Download sample CSV template for bulk import"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_import_template.csv"'
    
    writer = csv.writer(response)
    
    # Write header with required and optional fields
    writer.writerow([
        'first_name',
        'last_name', 
        'email',
        'mobile',
        'country_code',
        'job_title',
        'organization',
        'business_category',
        'business_subcategory'
    ])
    
    # Write sample data
    writer.writerow([
        'John',
        'Doe',
        'john.doe@example.com',
        '9876543210',
        '+91',
        'Manager',
        'ABC Company',
        'IT Services',
        'Software Development'
    ])
    
    writer.writerow([
        'Jane',
        'Smith',
        'jane.smith@company.com',
        '9876543211',
        '+91',
        'Director',
        'XYZ Corporation',
        'Manufacturing',
        'Electronics'
    ])
    
    return response