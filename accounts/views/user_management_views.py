# accounts/views/user_management_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password
import re

from accounts.decorators import permission_required
from accounts.models import CustomUser, Role, BusinessCategory, BusinessSubCategory
from django.http import JsonResponse
from django.conf import settings


def generate_next_employee_id():
    """Generate next employee ID in format EMP00001, EMP00002, etc."""
    # Get the last employee ID
    last_employee = CustomUser.objects.filter(
        employee_id__startswith='EMP',
        employee_id__regex=r'^EMP\d{5}$'
    ).order_by('-employee_id').first()
    
    if last_employee and last_employee.employee_id:
        # Extract number part and increment
        last_number = int(last_employee.employee_id[3:])  # Remove 'EMP' prefix
        next_number = last_number + 1
    else:
        # Start from 1 if no employees exist
        next_number = 1
    
    # Format with leading zeros (5 digits)
    return f"EMP{next_number:05d}"


def validate_employee_id_format(employee_id):
    """
    Validate Employee ID format: EMP followed by 5 digits
    Returns: (is_valid, error_message)
    """
    if not employee_id:
        return False, "Employee ID is required"
    
    # Check format: EMP + 5 digits
    pattern = r'^EMP\d{5}$'
    if not re.match(pattern, employee_id):
        return False, "Employee ID must be in format EMP00000 (EMP followed by 5 digits)"
    
    return True, None


@login_required
@permission_required('view_customers')
def user_list(request):
    """List all users (employees only - customers excluded)"""
    
    query = request.GET.get('q', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # ✅ Filter only employees
    users = CustomUser.objects.filter(user_type='employee').select_related('role', 'business_category')
    
    # Search
    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(employee_id__icontains=query) |
            Q(mobile__icontains=query)
        )
    
    # Filter by role
    if role_filter:
        users = users.filter(role_id=role_filter)
    
    # Filter by status
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(users.order_by('-created_at'), 20)
    page = request.GET.get('page', 1)
    users_page = paginator.get_page(page)
    
    # Get roles for filter
    roles = Role.objects.filter(is_active=True)
    
    context = {
        'users': users_page,
        'query': query,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': roles,
        'total_users': users.count(),
    }
    
    return render(request, 'admin/users/user_list.html', context)

@login_required
@permission_required('add_customer')
def user_add(request):
    """Add new user (employee/customer)"""
    
    if request.method == 'POST':
        try:
            # Validate passwords match
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            if password != confirm_password:
                messages.error(request, 'Passwords do not match!')
                return redirect('accounts:user_add')
            
            # Create user
            user = CustomUser.objects.create(
                username=request.POST.get('email'),  # Use email as username
                email=request.POST.get('email'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                mobile=request.POST.get('mobile'),
                country_code=request.POST.get('country_code', '+91'),
                employee_id=request.POST.get('employee_id') or None,
                system_mac_id=request.POST.get('system_mac_id') or None,
                system_ip_address=request.POST.get('system_ip_address') or None,
                user_type=request.POST.get('user_type', 'employee'),
                is_active=request.POST.get('is_active') == 'on',
                is_staff=True,  # Always true for employees
                password=make_password(password)
            )
            
            # Handle email verification options
            email_verification = request.POST.get('email_verification')
            if email_verification == 'verify_now':
                user.is_email_verified = True
            elif email_verification == 'send_verification_email':
                user.is_email_verified = False
                # Send verification email logic
                send_verification_email(user, request)
            elif email_verification == 'skip_verification':
                user.is_email_verified = False
                # No email sent, just allow login without verification
            
            # Assign role
            role_id = request.POST.get('role')
            if role_id:
                user.role_id = role_id
            
            # Assign category
            category_id = request.POST.get('business_category')
            if category_id:
                user.business_category_id = category_id
            
            subcategory_id = request.POST.get('business_subcategory')
            if subcategory_id:
                user.business_subcategory_id = subcategory_id
            
            user.save()
            
            messages.success(request, f'User "{user.full_name}" created successfully!')
            return redirect('accounts:user_detail', user_id=user.id)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('accounts:user_add')
    
    # GET request - show form
    roles = Role.objects.filter(is_active=True)
    categories = BusinessCategory.objects.filter(is_active=True)
    
    # Generate next employee ID suggestion
    last_employee = CustomUser.objects.filter(
        employee_id__isnull=False
    ).order_by('-employee_id').first()
    
    if last_employee and last_employee.employee_id:
        try:
            emp_number = int(last_employee.employee_id[3:])
            next_employee_id = f"EMP{(emp_number + 1):05d}"
        except:
            next_employee_id = "EMP00001"
    else:
        next_employee_id = "EMP00001"
    
    context = {
        'roles': roles,
        'categories': categories,
        'next_employee_id': next_employee_id,
    }
    
    return render(request, 'admin/users/user_add.html', context)

def send_verification_email(user, request):
    """Send verification email to user"""
    import secrets
    from django.utils import timezone
    from datetime import timedelta
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse
    
    # Generate token
    token = secrets.token_urlsafe(32)
    user.email_verification_token = token
    user.save()
    
    # Build verification URL
    verify_url = request.build_absolute_uri(
        reverse('accounts:verify_email', args=[token])
    )
    
    # Email content
    subject = "Verify your email address"
    message = f"""
    Hello {user.full_name},
    
    Please verify your email address by clicking the link below:
    
    {verify_url}
    
    This link will expire in 24 hours.
    
    Thank you,
    {settings.SITE_NAME if hasattr(settings, 'SITE_NAME') else 'Company'} Team
    """
    
    # Send email
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Email sending error: {str(e)}")
        return False

@login_required
@permission_required('view_customers')
def user_detail(request, user_id):
    """View user details"""
    
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    context = {
        'user_obj': user_obj,
    }
    
    return render(request, 'admin/users/user_detail.html', context)


@login_required
@permission_required('edit_customer')
def user_edit(request, user_id):
    """Edit employee details"""
    
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            
            # ✅ VALIDATION 1: Check business email (only if email changed)
            if email != user_obj.email:
                blocked_domains = [
                    'gmail.com', 'yahoo.com', 'yahoo.co.in', 'hotmail.com', 
                    'outlook.com', 'live.com', 'msn.com', 'icloud.com', 
                    'me.com', 'aol.com', 'ymail.com', 'rediffmail.com', 
                    'protonmail.com', 'mail.com', 'zoho.com'
                ]
                
                try:
                    domain = email.split('@')[1].lower()
                    if domain in blocked_domains:
                        messages.error(request, f'Personal email not allowed. Please use business email (not {domain}).')
                        context = {
                            'user_obj': user_obj,
                            'roles': Role.objects.filter(is_active=True),
                            'categories': BusinessCategory.objects.filter(is_active=True),
                            'subcategories': BusinessSubCategory.objects.filter(is_active=True),
                        }
                        return render(request, 'admin/users/user_edit.html', context)
                except (IndexError, AttributeError):
                    messages.error(request, 'Invalid email format!')
                    context = {
                        'user_obj': user_obj,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'subcategories': BusinessSubCategory.objects.filter(is_active=True),
                    }
                    return render(request, 'admin/users/user_edit.html', context)
                
                # ✅ VALIDATION 2: Check if email already exists (excluding current user)
                if CustomUser.objects.filter(email=email).exclude(id=user_obj.id).exists():
                    messages.error(request, 'Email already exists!')
                    context = {
                        'user_obj': user_obj,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'subcategories': BusinessSubCategory.objects.filter(is_active=True),
                    }
                    return render(request, 'admin/users/user_edit.html', context)
            
            # ✅ VALIDATION 3: Validate Employee ID format (only if changed)
            employee_id = request.POST.get('employee_id', '').strip().upper()
            
            if employee_id != user_obj.employee_id:
                is_valid, error_msg = validate_employee_id_format(employee_id)
                
                if not is_valid:
                    messages.error(request, error_msg)
                    context = {
                        'user_obj': user_obj,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'subcategories': BusinessSubCategory.objects.filter(is_active=True),
                    }
                    return render(request, 'admin/users/user_edit.html', context)
                
                # ✅ VALIDATION 4: Check if employee_id already exists (excluding current user)
                if CustomUser.objects.filter(employee_id=employee_id).exclude(id=user_obj.id).exists():
                    messages.error(request, f'Employee ID {employee_id} already exists!')
                    context = {
                        'user_obj': user_obj,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'subcategories': BusinessSubCategory.objects.filter(is_active=True),
                    }
                    return render(request, 'admin/users/user_edit.html', context)
            
            # ✅ Update basic fields
            user_obj.first_name = request.POST.get('first_name')
            user_obj.last_name = request.POST.get('last_name')
            user_obj.email = email
            user_obj.mobile = request.POST.get('mobile')
            user_obj.country_code = request.POST.get('country_code', '+91')
            user_obj.employee_id = employee_id or None
            user_obj.system_mac_address = request.POST.get('system_mac_address') or None
            
            # ✅ FIX: Always keep user_type as employee
            user_obj.user_type = 'employee'
            user_obj.is_staff = True
            
            # ✅ Status fields
            user_obj.is_active = request.POST.get('is_active') == 'on'
            user_obj.is_email_verified = request.POST.get('is_email_verified') == 'on'
            user_obj.is_approved = request.POST.get('is_approved') == 'on'
            
            # ✅ Organization always CHRP-HYD
            user_obj.organization = 'CHRP-HYD'
            
            # Update role
            role_id = request.POST.get('role')
            user_obj.role_id = role_id if role_id else None
            
            # Update category
            category_id = request.POST.get('business_category')
            user_obj.business_category_id = category_id if category_id else None
            
            # Update subcategory
            subcategory_id = request.POST.get('business_subcategory')
            user_obj.business_subcategory_id = subcategory_id if subcategory_id else None
            
            # ✅ VALIDATION 5: Update password if provided
            new_password = request.POST.get('new_password')
            if new_password:
                confirm_password = request.POST.get('confirm_password')
                if new_password == confirm_password:
                    user_obj.password = make_password(new_password)
                else:
                    messages.error(request, 'Passwords do not match!')
                    context = {
                        'user_obj': user_obj,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'subcategories': BusinessSubCategory.objects.filter(is_active=True),
                    }
                    return render(request, 'admin/users/user_edit.html', context)
            
            user_obj.save()
            
            messages.success(request, f'✅ Employee "{user_obj.full_name}" ({user_obj.employee_id}) updated successfully!')
            return redirect('accounts:user_detail', user_id=user_obj.id)
        
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            context = {
                'user_obj': user_obj,
                'roles': Role.objects.filter(is_active=True),
                'categories': BusinessCategory.objects.filter(is_active=True),
                'subcategories': BusinessSubCategory.objects.filter(is_active=True),
            }
            return render(request, 'admin/users/user_edit.html', context)
    
    # GET request - Show form
    roles = Role.objects.filter(is_active=True)
    categories = BusinessCategory.objects.filter(is_active=True)
    subcategories = BusinessSubCategory.objects.filter(is_active=True)
    
    context = {
        'user_obj': user_obj,
        'roles': roles,
        'categories': categories,
        'subcategories': subcategories,
    }
    
    return render(request, 'admin/users/user_edit.html', context)

@login_required
@permission_required('delete_customer')
def user_delete(request, user_id):
    """Delete user"""
    
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent self-deletion
    if user_obj.id == request.user.id:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('accounts:user_list')
    
    if request.method == 'POST':
        user_name = user_obj.full_name
        user_obj.delete()
        messages.success(request, f'User "{user_name}" deleted successfully!')
        return redirect('accounts:user_list')
    
    context = {
        'user_obj': user_obj,
    }
    
    return render(request, 'admin/users/user_delete.html', context)

@login_required
def check_employee_email(request):
    """Check if employee email already exists"""
    email = request.GET.get('email', '')
    
    # Check if this is a valid business email
    try:
        domain = email.split('@')[1].lower()
        blocked_domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 
                          'outlook.com', 'live.com', 'ymail.com', 
                          'aol.com', 'icloud.com']
        
        if domain in blocked_domains:
            return JsonResponse({
                'available': False,
                'message': f'Personal email domains ({domain}) not allowed.'
            })
    except:
        return JsonResponse({
            'available': False,
            'message': 'Invalid email format.'
        })
    
    # Check if email exists
    exists = CustomUser.objects.filter(email=email).exists()
    
    if exists:
        return JsonResponse({
            'available': False,
            'message': 'Email already registered.'
        })
    
    return JsonResponse({
        'available': True,
        'message': 'Email available.'
    })

@login_required
def check_employee_id(request):
    """Check if employee ID already exists"""
    employee_id = request.GET.get('employee_id', '').strip().upper()
    
    # Validate format
    import re
    pattern = r'^EMP\d{5}$'
    if not re.match(pattern, employee_id):
        return JsonResponse({
            'available': False,
            'message': 'Format must be EMP followed by 5 digits (e.g., EMP00001)'
        })
    
    # Check if exists
    exists = CustomUser.objects.filter(employee_id=employee_id).exists()
    
    if exists:
        return JsonResponse({
            'available': False,
            'message': f'Employee ID {employee_id} is already in use.'
        })
    
    return JsonResponse({
        'available': True,
        'message': 'Employee ID available.'
    })

@login_required
def get_next_employee_id(request):
    """AJAX endpoint to get next available employee ID"""
    next_id = generate_next_employee_id()
    return JsonResponse({
        'next_employee_id': next_id
    })