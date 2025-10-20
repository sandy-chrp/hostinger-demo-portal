# accounts/views/user_management_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password

from accounts.decorators import permission_required
from accounts.models import CustomUser, Role, BusinessCategory, BusinessSubCategory
from django.http import JsonResponse
from django.conf import settings


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
    """Add new employee"""
    
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            
            # ✅ VALIDATION 1: Check business email
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
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'form_data': request.POST,
                    }
                    return render(request, 'admin/users/user_add.html', context)
            except (IndexError, AttributeError):
                messages.error(request, 'Invalid email format!')
                context = {
                    'roles': Role.objects.filter(is_active=True),
                    'categories': BusinessCategory.objects.filter(is_active=True),
                    'form_data': request.POST,
                }
                return render(request, 'admin/users/user_add.html', context)
            
            # ✅ VALIDATION 2: Check if email already exists
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists!')
                context = {
                    'roles': Role.objects.filter(is_active=True),
                    'categories': BusinessCategory.objects.filter(is_active=True),
                    'form_data': request.POST,
                }
                return render(request, 'admin/users/user_add.html', context)
            
            # ✅ VALIDATION 3: Check if employee_id already exists
            employee_id = request.POST.get('employee_id')
            if CustomUser.objects.filter(employee_id=employee_id).exists():
                messages.error(request, 'Employee ID already exists!')
                context = {
                    'roles': Role.objects.filter(is_active=True),
                    'categories': BusinessCategory.objects.filter(is_active=True),
                    'form_data': request.POST,
                }
                return render(request, 'admin/users/user_add.html', context)
            
            # ✅ VALIDATION 4: Validate passwords match
            password = request.POST.get('password')
            confirm_password = request.POST.get('confirm_password')
            
            if password != confirm_password:
                messages.error(request, 'Passwords do not match!')
                context = {
                    'roles': Role.objects.filter(is_active=True),
                    'categories': BusinessCategory.objects.filter(is_active=True),
                    'form_data': request.POST,
                }
                return render(request, 'admin/users/user_add.html', context)
            
            # ✅ Get email verification option
            email_verification = request.POST.get('email_verification', 'verify_now')
            
            # Set email verification status
            if email_verification == 'verify_now':
                is_email_verified = True
            elif email_verification == 'skip':
                is_email_verified = False
            else:  # send_email
                is_email_verified = False
            
            # ✅ Create user
            user = CustomUser.objects.create(
                username=email,
                email=email,
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                mobile=request.POST.get('mobile'),
                country_code=request.POST.get('country_code', '+91'),
                employee_id=employee_id,
                organization='CHRP-HYD',
                user_type='employee',
                is_staff=True,
                is_active=request.POST.get('is_active') == 'on',
                is_email_verified=is_email_verified,  # ✅ Set based on option
                is_approved=request.POST.get('is_approved') == 'on',  # ✅ Pre-approval
                system_mac_address=request.POST.get('system_mac_address') or None,
                last_login_ip=request.POST.get('system_ip_address') or None,
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
            
            # Assign subcategory
            subcategory_id = request.POST.get('business_subcategory')
            if subcategory_id:
                user.business_subcategory_id = subcategory_id
            
            user.save()
            
            # ✅ Handle email verification
            if email_verification == 'send_email':
                # Send verification email
                from accounts.utils import send_verification_email
                try:
                    send_verification_email(user, request)
                    messages.success(request, f'✅ Employee "{user.full_name}" created! Verification email sent to {user.email}')
                except Exception as e:
                    messages.warning(request, f'Employee created but email sending failed: {str(e)}')
            elif email_verification == 'verify_now':
                messages.success(request, f'✅ Employee "{user.full_name}" created successfully! (Email pre-verified)')
            else:  # skip
                messages.success(request, f'✅ Employee "{user.full_name}" created! (Email verification skipped)')
            
            return redirect('accounts:user_detail', user_id=user.id)
        
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            context = {
                'roles': Role.objects.filter(is_active=True),
                'categories': BusinessCategory.objects.filter(is_active=True),
                'form_data': request.POST,
            }
            return render(request, 'admin/users/user_add.html', context)
    
    # GET request
    roles = Role.objects.filter(is_active=True)
    categories = BusinessCategory.objects.filter(is_active=True)
    
    context = {
        'roles': roles,
        'categories': categories,
        'form_data': None,
    }
    
    return render(request, 'admin/users/user_add.html', context)

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
    """Edit user"""
    
    user_obj = get_object_or_404(CustomUser, id=user_id)
    
    if request.method == 'POST':
        try:
            user_obj.first_name = request.POST.get('first_name')
            user_obj.last_name = request.POST.get('last_name')
            user_obj.email = request.POST.get('email')
            user_obj.mobile = request.POST.get('mobile')
            user_obj.country_code = request.POST.get('country_code', '+91')
            user_obj.employee_id = request.POST.get('employee_id') or None
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
            
            # ✅ Update password if provided
            new_password = request.POST.get('new_password')
            if new_password:
                confirm_password = request.POST.get('confirm_password')
                if new_password == confirm_password:
                    user_obj.password = make_password(new_password)
                else:
                    messages.error(request, 'Passwords do not match!')
                    # Preserve form data
                    context = {
                        'user_obj': user_obj,
                        'roles': Role.objects.filter(is_active=True),
                        'categories': BusinessCategory.objects.filter(is_active=True),
                        'subcategories': BusinessSubCategory.objects.filter(is_active=True),
                    }
                    return render(request, 'admin/users/user_edit.html', context)
            
            user_obj.save()
            
            messages.success(request, f'✅ Employee "{user_obj.full_name}" updated successfully!')
            return redirect('accounts:user_detail', user_id=user_obj.id)
        
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            # Preserve form data on error
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
    """AJAX endpoint to check if email exists and is business email"""
    email = request.GET.get('email', '')
    
    if not email:
        return JsonResponse({'available': True})
    
    # ✅ Check if personal email domain
    blocked_domains = getattr(settings, 'BLOCKED_EMAIL_DOMAINS', [
        'yahoo.com', 'hotmail.com', 'outlook.com', 
        'ymail.com', 'aol.com', 'icloud.com', 'live.com',
        'gmail.com', 'rediffmail.com', 'protonmail.com'
    ])
    
    try:
        domain = email.split('@')[1].lower()
        if domain in blocked_domains:
            return JsonResponse({
                'available': False,
                'message': f'Personal email not allowed. Please use business email.'
            })
    except IndexError:
        return JsonResponse({
            'available': False,
            'message': 'Invalid email format'
        })
    
    # ✅ Check if email already exists
    exists = CustomUser.objects.filter(email=email).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Email already exists!' if exists else 'Email available'
    })

@login_required
def check_employee_id(request):
    """AJAX endpoint to check if employee ID exists"""
    employee_id = request.GET.get('employee_id', '')
    
    if not employee_id:
        return JsonResponse({'available': True})
    
    exists = CustomUser.objects.filter(employee_id=employee_id).exists()
    
    return JsonResponse({
        'available': not exists,
        'message': 'Employee ID already exists!' if exists else 'Employee ID available'
    })