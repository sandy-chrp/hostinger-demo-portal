# accounts/views/user_management_views.py (NEW FILE)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.hashers import make_password
from django.http import JsonResponse

from accounts.decorators import permission_required
from accounts.models import CustomUser, Role, BusinessCategory, BusinessSubCategory


@login_required
@permission_required('view_customers')
def user_list(request):
    """List all users (employees + customers)"""
    
    query = request.GET.get('q', '')
    user_type = request.GET.get('type', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    users = CustomUser.objects.all().select_related('role', 'business_category')
    
    # Search
    if query:
        users = users.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(employee_id__icontains=query) |
            Q(mobile__icontains=query)
        )
    
    # Filter by user type
    if user_type:
        users = users.filter(user_type=user_type)
    
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
                employee_id=request.POST.get('employee_id') or None,
                system_mac_id=request.POST.get('system_mac_id') or None,
                system_ip_address=request.POST.get('system_ip_address') or None,
                user_type=request.POST.get('user_type', 'customer'),
                is_active=request.POST.get('is_active') == 'on',
                is_staff=request.POST.get('user_type') == 'employee',
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
            
            user.save()
            
            messages.success(request, f'User "{user.full_name}" created successfully!')
            return redirect('accounts:user_detail', user_id=user.id)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('accounts:user_add')
    
    # GET request - show form
    roles = Role.objects.filter(is_active=True)
    categories = BusinessCategory.objects.filter(is_active=True)
    
    context = {
        'roles': roles,
        'categories': categories,
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
            user.first_name = request.POST.get('first_name')
            user.last_name = request.POST.get('last_name')
            user.email = request.POST.get('email')
            user.mobile = request.POST.get('mobile')
            user.employee_id = request.POST.get('employee_id') or None
            user.system_mac_id = request.POST.get('system_mac_id') or None
            user.system_ip_address = request.POST.get('system_ip_address') or None
            user.user_type = request.POST.get('user_type')
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
            new_password = request.POST.get('new_password')
            if new_password:
                confirm_password = request.POST.get('confirm_password')
                if new_password == confirm_password:
                    user.password = make_password(new_password)
                else:
                    messages.error(request, 'Passwords do not match!')
                    return redirect('accounts:user_edit', user_id=user_id)
            
            user.save()
            
            messages.success(request, f'User "{user.full_name}" updated successfully!')
            return redirect('accounts:user_detail', user_id=user.id)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
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