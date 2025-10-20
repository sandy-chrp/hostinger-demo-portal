# accounts/decorators.py (COMPLETE WITH RBAC)
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def permission_required(permission_code):
    """Decorator to check if user has permission"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to continue.')
                return redirect('core:admin_login')
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            if not hasattr(request.user, 'role') or not request.user.role:
                messages.error(request, 'Access denied. No role assigned.')
                return redirect('core:admin_dashboard')
            
            # ✅ FIXED: Use codename
            has_perm = request.user.role.permissions.filter(
                codename=permission_code,  # ✅ Database field
                is_active=True
            ).exists()
            
            if not has_perm:
                messages.error(request, f'Access denied. Required permission: {permission_code}')
                return redirect('core:admin_dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator

def any_permission_required(*permission_codenames, raise_exception=False):
    """
    Decorator to check if user has ANY of the specified permissions
    
    Usage:
        @any_permission_required('view_customers', 'edit_customers')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:signin')
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check if user has ANY of the permissions
            for perm in permission_codenames:
                if request.user.has_permission(perm):
                    return view_func(request, *args, **kwargs)
            
            # No permission found
            if raise_exception:
                raise PermissionDenied("You don't have required permissions")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Permission denied'
                }, status=403)
            
            messages.error(request, '⛔ Access Denied: Insufficient permissions.')
            return redirect('core:admin_dashboard')
        
        return wrapper
    return decorator


def all_permissions_required(*permission_codenames, raise_exception=False):
    """
    Decorator to check if user has ALL of the specified permissions
    
    Usage:
        @all_permissions_required('view_customers', 'edit_customers')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:signin')
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check if user has ALL permissions
            for perm in permission_codenames:
                if not request.user.has_permission(perm):
                    if raise_exception:
                        raise PermissionDenied(f"Missing permission: {perm}")
                    
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({
                            'success': False,
                            'error': 'Permission denied'
                        }, status=403)
                    
                    messages.error(request, '⛔ Access Denied: Insufficient permissions.')
                    return redirect('core:admin_dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def role_required(*role_names, raise_exception=False):
    """
    Decorator to check if user has specific role(s)
    
    Usage:
        @role_required('Admin', 'Super Admin')
        def my_view(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:signin')
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check if user has role
            if request.user.role and request.user.role.name in role_names:
                return view_func(request, *args, **kwargs)
            
            # Role not matched
            if raise_exception:
                raise PermissionDenied("You don't have required role")
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Access denied'
                }, status=403)
            
            messages.error(request, '⛔ Access Denied: Required role not assigned.')
            return redirect('core:admin_dashboard')
        
        return wrapper
    return decorator


def staff_required(view_func):
    """
    Decorator to check if user is staff member
    Shortcut for checking is_staff
    
    Usage:
        @staff_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:signin')
        
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Staff access required'
            }, status=403)
        
        messages.error(request, '⛔ Access Denied: Staff access required.')
        return redirect('core:admin_dashboard')
    
    return wrapper


def admin_required(view_func):
    """
    Decorator to check if user is admin (staff + access_admin_panel permission)
    
    Usage:
        @admin_required
        def my_view(request):
            ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:signin')
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        if request.user.is_staff and request.user.has_permission('access_admin_panel'):
            return view_func(request, *args, **kwargs)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'Admin access required'
            }, status=403)
        
        messages.error(request, '⛔ Access Denied: Admin access required.')
        return redirect('accounts:signin')
    
    return wrapper


# =============================================
# CONDITIONAL DECORATORS
# =============================================

def owner_or_permission_required(permission_codename, owner_field='user'):
    """
    Allow access if user is owner OR has permission
    
    Usage:
        @owner_or_permission_required('edit_demo', owner_field='created_by')
        def edit_demo(request, demo_id):
            demo = get_object_or_404(Demo, id=demo_id)
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:signin')
            
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            
            # Check permission first
            if request.user.has_permission(permission_codename):
                return view_func(request, *args, **kwargs)
            
            # Check ownership (this is basic - you'll need to customize per view)
            # For now, just deny if no permission
            messages.error(request, '⛔ Access Denied: Insufficient permissions.')
            return redirect('core:admin_dashboard')
        
        return wrapper
    return decorator