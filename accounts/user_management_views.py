# accounts/views/user_management_views.py (FIXED VERSION - NO WRONG EMAILS)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re

from accounts.decorators import permission_required
from accounts.models import CustomUser, Role, BusinessCategory, BusinessSubCategory
from accounts.signals import send_employee_welcome_with_password

@login_required
@permission_required('view_customers')
def user_list(request):
    """List all employees (NOT customers)"""
    
    query = request.GET.get('q', '')
    user_type = request.GET.get('type', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    # ✅ FIX: Default to showing ONLY employees
    users = CustomUser.objects.filter(
        user_type='employee',  # Only employees
        is_staff=True          # Only staff members
    ).select_related('role', 'business_category')
    
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
        'user_type': user_type,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'roles': roles,
        'total_users': users.count(),
    }
    
    return render(request, 'admin/users/user_list.html', context)


def get_next_employee_id():
    """Generate next employee ID in format EMP00001"""
    last_employee = CustomUser.objects.filter(
        employee_id__isnull=False
    ).order_by('-employee_id').first()
    
    if last_employee and last_employee.employee_id:
        # Extract number from EMP00001
        try:
            last_number = int(last_employee.employee_id[3:])
            next_number = last_number + 1
            return f"EMP{next_number:05d}"
        except (ValueError, IndexError):
            return "EMP00001"
    
    return "EMP00001"

@login_required
@permission_required('add_customer')
def user_add(request):
    """Add new user (employee only) - ✅ FIXED: Email sending with password"""
    
    if request.method == 'POST':
        try:
            # Validate passwords match
            password = request.POST.get('password', '').strip()
            confirm_password = request.POST.get('confirm_password', '').strip()
            
            if password != confirm_password:
                messages.error(request, 'Passwords do not match!')
                context = {
                    'form_data': request.POST,
                    'roles': Role.objects.filter(is_active=True),
                    'categories': BusinessCategory.objects.filter(is_active=True),
                    'next_employee_id': get_next_employee_id(),
                }
                return render(request, 'admin/users/user_add.html', context)
            
            # Validate email
            email = request.POST.get('email', '').strip()
            try:
                validate_email(email)
            except ValidationError:
                messages.error(request, 'Invalid email address!')
                context = {
                    'form_data': request.POST,
                    'roles': Role.objects.filter(is_active=True),
                    'categories': BusinessCategory.objects.filter(is_active=True),
                    'next_employee_id': get_next_employee_id(),
                }
                return render(request, 'admin/users/user_add.html', context)
            
            # Check if email already exists
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'This email is already registered!')
                context = {
                    'form_data': request.POST,
                    'roles': Role.objects.filter(is_active=True),
                    'categories': BusinessCategory.objects.filter(is_active=True),
                    'next_employee_id': get_next_employee_id(),
                }
                return render(request, 'admin/users/user_add.html', context)
            
            # Validate employee ID format if provided
            employee_id = request.POST.get('employee_id', '').strip().upper()
            if employee_id:
                pattern = r'^EMP\d{5}$'
                if not re.match(pattern, employee_id):
                    messages.error(request, 'Employee ID must be in format EMP00001 (EMP followed by 5 digits)')
                    context = {
                        'form_data': request.POST,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'next_employee_id': get_next_employee_id(),
                    }
                    return render(request, 'admin/users/user_add.html', context)
                
                # Check if employee ID already exists
                if CustomUser.objects.filter(employee_id=employee_id).exists():
                    messages.error(request, f'Employee ID {employee_id} is already in use!')
                    context = {
                        'form_data': request.POST,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'next_employee_id': get_next_employee_id(),
                    }
                    return render(request, 'admin/users/user_add.html', context)
            
            # Get country code and mobile
            country_code = request.POST.get('country_code', '+91')
            mobile = request.POST.get('mobile', '').strip()
            
            # Create user
            user = CustomUser.objects.create(
                username=email,
                email=email,
                first_name=request.POST.get('first_name', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                country_code=country_code,
                mobile=mobile,
                employee_id=employee_id if employee_id else None,
                system_mac_address=request.POST.get('system_mac_id', '').strip() or None,
                last_login_ip=request.POST.get('system_ip_address', '').strip() or None,
                user_type='employee',
                is_active=request.POST.get('is_active') == 'on',
                is_staff=True,
                is_approved=True,
                is_email_verified=True,
                password=make_password(password)
            )
            
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
            
            # Save user
            user.save()
            
            # ✅ EMAIL SENDING WITH DEBUGGING
            email_verification = request.POST.get('email_verification', 'verify_now')
            
            # Print to console
            print("\n" + "="*80)
            print(f"DEBUG: FORM SUBMIT - USER ADD")
            print(f"Email Choice: {email_verification}")
            print(f"User Email: {user.email}")
            print(f"Password: {password}")
            print("="*80 + "\n")
            
            if email_verification == 'send_verification_email':
                print(">>> Sending email now...")
                
                try:
                    from accounts.signals import send_employee_welcome_with_password
                    email_sent = send_employee_welcome_with_password(user, password)
                    
                    if email_sent:
                        messages.success(
                            request, 
                            f'Employee created! Email sent to {user.email}'
                        )
                    else:
                        messages.warning(
                            request, 
                            f'Employee created but email failed!'
                        )
                        
                except Exception as e:
                    print(f"ERROR: {e}")
                    import traceback
                    traceback.print_exc()
                    messages.warning(request, f'Email error: {str(e)}')
            else:
                messages.success(request, f'Employee created: {user.full_name}')
            
            return redirect('accounts:user_detail', user_id=user.id)
        
        except Exception as e:
            print(f"ERROR creating user: {e}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error: {str(e)}')
            context = {
                'form_data': request.POST,
                'roles': Role.objects.filter(is_active=True),
                'categories': BusinessCategory.objects.filter(is_active=True),
                'next_employee_id': get_next_employee_id(),
            }
            return render(request, 'admin/users/user_add.html', context)
    
    # GET request
    roles = Role.objects.filter(is_active=True)
    categories = BusinessCategory.objects.filter(is_active=True)
    
    context = {
        'roles': roles,
        'categories': categories,
        'next_employee_id': get_next_employee_id(),
    }
    
    return render(request, 'admin/users/user_add.html', context)

@login_required
@permission_required('view_customers')
def user_detail(request, user_id):
    """View user details"""
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    context = {
        'user_obj': user,
    }
    
    return render(request, 'admin/users/user_detail.html', context)


@login_required
@permission_required('edit_customer')
def user_edit(request, user_id):
    """Edit user"""
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        try:
            user.first_name = request.POST.get('first_name', '').strip()
            user.last_name = request.POST.get('last_name', '').strip()
            user.email = request.POST.get('email', '').strip()
            user.country_code = request.POST.get('country_code', '+91')
            user.mobile = request.POST.get('mobile', '').strip()
            user.employee_id = request.POST.get('employee_id', '').strip().upper() or None
            user.system_mac_address = request.POST.get('system_mac_id', '').strip() or None
            user.last_login_ip = request.POST.get('system_ip_address', '').strip() or None
            user.user_type = request.POST.get('user_type', 'employee')
            user.is_active = request.POST.get('is_active') == 'on'
            user.is_staff = request.POST.get('user_type') == 'employee'
            
            # Update role
            role_id = request.POST.get('role')
            user.role_id = role_id if role_id else None
            
            # Update category
            category_id = request.POST.get('business_category')
            user.business_category_id = category_id if category_id else None
            
            subcategory_id = request.POST.get('business_subcategory')
            user.business_subcategory_id = subcategory_id if subcategory_id else None
            
            # Update password if provided
            new_password = request.POST.get('new_password', '').strip()
            if new_password:
                confirm_password = request.POST.get('confirm_password', '').strip()
                if new_password == confirm_password:
                    user.password = make_password(new_password)
                else:
                    messages.error(request, 'Passwords do not match!')
                    return redirect('accounts:user_edit', user_id=user_id)
            
            user.save()
            
            messages.success(request, f'User "{user.full_name}" updated successfully!')
            return redirect('accounts:user_detail', user_id=user.id)
        
        except Exception as e:
            messages.error(request, f'Error updating user: {str(e)}')
    
    roles = Role.objects.filter(is_active=True)
    categories = BusinessCategory.objects.filter(is_active=True)
    subcategories = BusinessSubCategory.objects.filter(is_active=True)
    
    context = {
        'user_obj': user,
        'roles': roles,
        'categories': categories,
        'subcategories': subcategories,
    }
    
    return render(request, 'admin/users/user_edit.html', context)


@login_required
@permission_required('delete_customer')
def user_delete(request, user_id):
    """Delete user"""
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    # Prevent self-deletion
    if user.id == request.user.id:
        messages.error(request, 'You cannot delete your own account!')
        return redirect('accounts:user_list')
    
    if request.method == 'POST':
        user_name = user.full_name
        user.delete()
        messages.success(request, f'User "{user_name}" deleted successfully!')
        return redirect('accounts:user_list')
    
    context = {
        'user_obj': user,
    }
    
    return render(request, 'admin/users/user_delete.html', context)


# ==========================================
# AJAX ENDPOINTS
# ==========================================

def check_employee_email(request):
    """AJAX endpoint to check if employee email is available"""
    email = request.GET.get('email', '').strip().lower()
    
    if not email:
        return JsonResponse({
            'available': False,
            'message': 'Email is required'
        })
    
    # Validate email format
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({
            'available': False,
            'message': 'Invalid email format'
        })
    
    # Check blocked domains
    blocked_domains = [
        'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
        'live.com', 'ymail.com', 'aol.com', 'icloud.com',
        'rediffmail.com', 'protonmail.com'
    ]
    
    try:
        domain = email.split('@')[1].lower()
        if domain in blocked_domains:
            return JsonResponse({
                'available': False,
                'message': 'Personal email domains not allowed. Use business email.'
            })
    except IndexError:
        return JsonResponse({
            'available': False,
            'message': 'Invalid email format'
        })
    
    # Check if email already exists
    if CustomUser.objects.filter(email=email).exists():
        return JsonResponse({
            'available': False,
            'message': 'This email is already registered'
        })
    
    return JsonResponse({
        'available': True,
        'message': 'Email is available'
    })


def check_employee_id(request):
    """AJAX endpoint to check if employee ID is available"""
    employee_id = request.GET.get('employee_id', '').strip().upper()
    
    if not employee_id:
        return JsonResponse({
            'available': False,
            'message': 'Employee ID is required'
        })
    
    # Validate format
    pattern = r'^EMP\d{5}$'
    if not re.match(pattern, employee_id):
        return JsonResponse({
            'available': False,
            'message': 'Format must be EMP followed by 5 digits (e.g., EMP00001)'
        })
    
    # Check if exists
    if CustomUser.objects.filter(employee_id=employee_id).exists():
        return JsonResponse({
            'available': False,
            'message': f'Employee ID {employee_id} is already in use'
        })
    
    return JsonResponse({
        'available': True,
        'message': 'Employee ID is available'
    })