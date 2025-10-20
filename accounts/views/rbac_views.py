# accounts/views/rbac_views.py (COMPLETE FILE WITH ALL FIXES)
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.db import transaction

from accounts.decorators import permission_required, admin_required
from accounts.models import Role, Permission, CustomUser


# =============================================
# ROLE MANAGEMENT VIEWS
# =============================================

@login_required
@permission_required('manage_roles')
def role_list(request):
    """List all roles with search and filter"""
    
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    # Get roles with counts - ordering from model Meta will apply
    roles = Role.objects.annotate(
        users_count=Count('users'),
        permissions_count=Count('permissions')
    )
    
    # Search
    if query:
        roles = roles.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Filter by status
    if status_filter:
        if status_filter == 'active':
            roles = roles.filter(is_active=True)
        elif status_filter == 'inactive':
            roles = roles.filter(is_active=False)
        elif status_filter == 'system':
            roles = roles.filter(is_system_role=True)
        elif status_filter == 'custom':
            roles = roles.filter(is_system_role=False)
    
    # Pagination
    paginator = Paginator(roles, 15)
    page = request.GET.get('page', 1)
    roles_page = paginator.get_page(page)
    
    context = {
        'roles': roles_page,
        'query': query,
        'status_filter': status_filter,
        'total_roles': roles.count(),
    }
    
    return render(request, 'admin/rbac/role_list.html', context)


@login_required
@permission_required('manage_roles')
def role_detail(request, role_id):
    """View role details with users and permissions"""
    
    role = get_object_or_404(Role, id=role_id)
    
    # Get users with this role
    users = role.users.all().order_by('-created_at')[:10]
    
    # Get permissions grouped by module
    permissions = role.permissions.filter(is_active=True).order_by('module', 'name')
    
    permissions_by_module = {}
    for perm in permissions:
        module = perm.get_module_display()
        if module not in permissions_by_module:
            permissions_by_module[module] = []
        permissions_by_module[module].append(perm)
    
    context = {
        'role': role,
        'users': users,
        'permissions_by_module': permissions_by_module,
        'total_users': role.users.count(),
        'total_permissions': permissions.count(),
    }
    
    return render(request, 'admin/rbac/role_detail.html', context)


@login_required
@permission_required('manage_roles')
def role_add(request):
    """Add new role"""
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Create role
                role = Role.objects.create(
                    name=request.POST.get('name'),
                    description=request.POST.get('description', ''),
                    priority=int(request.POST.get('priority', 0)),
                    is_active=request.POST.get('is_active') == 'on',
                    is_system_role=False  # Custom roles are never system roles
                )
                
                # Assign permissions
                permission_ids = request.POST.getlist('permissions')
                if permission_ids:
                    permissions = Permission.objects.filter(id__in=permission_ids)
                    role.permissions.set(permissions)
                
                messages.success(request, f'✅ Role "{role.name}" created successfully!')
                return redirect('accounts:role_detail', role_id=role.id)
        
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    # Get all permissions grouped by module
    permissions = Permission.objects.filter(is_active=True).order_by('module', 'name')
    
    permissions_by_module = {}
    for perm in permissions:
        module = perm.get_module_display()
        if module not in permissions_by_module:
            permissions_by_module[module] = []
        permissions_by_module[module].append(perm)
    
    context = {
        'permissions_by_module': permissions_by_module,
    }
    
    return render(request, 'admin/rbac/role_add.html', context)


@login_required
@permission_required('manage_roles')
def role_edit(request, role_id):
    """Edit existing role"""
    
    role = get_object_or_404(Role, id=role_id)
    
    # Prevent editing system roles' critical fields
    if role.is_system_role:
        can_edit_name = False
        can_delete = False
    else:
        can_edit_name = True
        can_delete = True
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Update role
                if can_edit_name:
                    role.name = request.POST.get('name')
                
                role.description = request.POST.get('description', '')
                role.priority = int(request.POST.get('priority', 0))
                role.is_active = request.POST.get('is_active') == 'on'
                role.save()
                
                # Update permissions
                permission_ids = request.POST.getlist('permissions')
                permissions = Permission.objects.filter(id__in=permission_ids)
                role.permissions.set(permissions)
                
                messages.success(request, f'✅ Role "{role.name}" updated successfully!')
                return redirect('accounts:role_detail', role_id=role.id)
        
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    # Get all permissions grouped by module
    all_permissions = Permission.objects.filter(is_active=True).order_by('module', 'name')
    role_permission_ids = list(role.permissions.values_list('id', flat=True))
    
    permissions_by_module = {}
    for perm in all_permissions:
        module = perm.get_module_display()
        if module not in permissions_by_module:
            permissions_by_module[module] = []
        permissions_by_module[module].append(perm)
    
    context = {
        'role': role,
        'permissions_by_module': permissions_by_module,
        'role_permission_ids': role_permission_ids,
        'can_edit_name': can_edit_name,
        'can_delete': can_delete,
    }
    
    return render(request, 'admin/rbac/role_edit.html', context)


@login_required
@permission_required('manage_roles')
def role_delete(request, role_id):
    """Delete role"""
    
    role = get_object_or_404(Role, id=role_id)
    
    # Prevent deletion of system roles
    if role.is_system_role:
        messages.error(request, '⛔ Cannot delete system role!')
        return redirect('accounts:role_list')
    
    # Check if role has users
    users_count = role.users.count()
    
    if request.method == 'POST':
        if users_count > 0:
            # Reassign users to another role or remove role
            action = request.POST.get('action')
            
            if action == 'reassign':
                new_role_id = request.POST.get('new_role_id')
                if new_role_id:
                    new_role = get_object_or_404(Role, id=new_role_id)
                    role.users.all().update(role=new_role)
                    messages.success(request, f'✅ Users reassigned to "{new_role.name}"')
            else:
                # Remove role from users
                role.users.all().update(role=None)
                messages.info(request, '✅ Role removed from all users')
        
        role_name = role.name
        role.delete()
        messages.success(request, f'✅ Role "{role_name}" deleted successfully!')
        return redirect('accounts:role_list')
    
    # Get other roles for reassignment
    other_roles = Role.objects.filter(is_active=True).exclude(id=role_id)
    
    context = {
        'role': role,
        'users_count': users_count,
        'other_roles': other_roles,
    }
    
    return render(request, 'admin/rbac/role_delete.html', context)


# =============================================
# PERMISSION MANAGEMENT VIEWS
# =============================================

@login_required
@permission_required('manage_permissions')
def permission_list(request):
    """List all permissions"""
    
    query = request.GET.get('q', '')
    module_filter = request.GET.get('module', '')
    
    permissions = Permission.objects.all().order_by('module', 'name')
    
    # Search
    if query:
        permissions = permissions.filter(
            Q(name__icontains=query) |
            Q(codename__icontains=query) |
            Q(description__icontains=query)
        )
    
    # Filter by module
    if module_filter:
        permissions = permissions.filter(module=module_filter)
    
    # Group by module
    permissions_by_module = {}
    for perm in permissions:
        module = perm.get_module_display()
        if module not in permissions_by_module:
            permissions_by_module[module] = []
        permissions_by_module[module].append(perm)
    
    # Get module choices for filter
    modules = Permission.MODULE_CHOICES
    
    context = {
        'permissions_by_module': permissions_by_module,
        'modules': modules,
        'query': query,
        'module_filter': module_filter,
        'total_permissions': permissions.count(),
    }
    
    return render(request, 'admin/rbac/permission_list.html', context)


@login_required
@permission_required('manage_permissions')
def permission_add(request):
    """Add new permission dynamically"""
    
    if request.method == 'POST':
        try:
            name = request.POST.get('name', '').strip()
            codename = request.POST.get('code_name', '').strip()  # ✅ Form uses code_name
            description = request.POST.get('description', '').strip()
            module = request.POST.get('module', '').strip()
            
            # Handle custom module
            if module == '__custom__':
                custom_module_name = request.POST.get('custom_module_name', '').strip()
                if not custom_module_name:
                    messages.error(request, 'Please provide a custom module name.')
                    context = {
                        'form_data': request.POST,
                        'custom_modules': get_custom_modules()
                    }
                    return render(request, 'admin/rbac/permission_add.html', context)
                module = custom_module_name
            
            # Validate codename format
            if not codename.replace('_', '').isalpha() or codename != codename.lower():
                messages.error(request, 'Code name must be lowercase letters and underscores only.')
                context = {
                    'form_data': request.POST,
                    'custom_modules': get_custom_modules()
                }
                return render(request, 'admin/rbac/permission_add.html', context)
            
            # ✅ Check if codename already exists (FIXED)
            if Permission.objects.filter(codename=codename).exists():
                messages.error(request, f'Permission with code "{codename}" already exists!')
                context = {
                    'form_data': request.POST,
                    'custom_modules': get_custom_modules()
                }
                return render(request, 'admin/rbac/permission_add.html', context)
            
            # ✅ Create permission (FIXED - use codename)
            permission = Permission.objects.create(
                name=name,
                codename=codename,  # ✅ Database field
                description=description,
                module=module,
                is_active=request.POST.get('is_active') == 'on'
            )
            
            messages.success(request, f'✅ Permission "{permission.name}" created successfully!')
            return redirect('accounts:permission_list')
        
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            context = {
                'form_data': request.POST,
                'custom_modules': get_custom_modules()
            }
            return render(request, 'admin/rbac/permission_add.html', context)
    
    # GET request
    context = {
        'form_data': None,
        'custom_modules': get_custom_modules()
    }
    
    return render(request, 'admin/rbac/permission_add.html', context)


def get_custom_modules():
    """Helper function to get custom modules"""
    core_modules = [
        'Customer Management', 'Demo Management', 'Demo Requests',
        'Business Categories', 'Enquiries', 'Notifications',
        'Analytics & Reports', 'Settings', 'System Administration'
    ]
    
    return Permission.objects.exclude(
        module__in=core_modules
    ).values_list('module', flat=True).distinct().order_by('module')

@login_required
@permission_required('manage_permissions')
def permission_edit(request, permission_id):
    """Edit permission"""
    
    permission = get_object_or_404(Permission, id=permission_id)
    
    if request.method == 'POST':
        try:
            permission.name = request.POST.get('name')
            permission.codename = request.POST.get('codename')
            permission.description = request.POST.get('description', '')
            permission.module = request.POST.get('module')
            permission.is_active = request.POST.get('is_active') == 'on'
            permission.save()
            
            messages.success(request, f'✅ Permission "{permission.name}" updated successfully!')
            return redirect('accounts:permission_list')
        
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
    
    modules = Permission.MODULE_CHOICES
    
    context = {
        'permission': permission,
        'modules': modules,
    }
    
    return render(request, 'admin/rbac/permission_edit.html', context)


@login_required
@permission_required('manage_permissions')
def permission_delete(request, permission_id):
    """Delete permission"""
    
    permission = get_object_or_404(Permission, id=permission_id)
    
    # Check if permission is used in any roles
    roles_count = permission.roles.count()
    
    if request.method == 'POST':
        permission_name = permission.name
        permission.delete()
        messages.success(request, f'✅ Permission "{permission_name}" deleted successfully!')
        return redirect('accounts:permission_list')
    
    context = {
        'permission': permission,
        'roles_count': roles_count,
    }
    
    return render(request, 'admin/rbac/permission_delete.html', context)


# =============================================
# USER ROLE ASSIGNMENT
# =============================================

@login_required
@permission_required('manage_roles')
def assign_role(request, user_id):
    """Assign role to user (AJAX)"""
    
    if request.method == 'POST':
        try:
            user = get_object_or_404(CustomUser, id=user_id)
            role_id = request.POST.get('role_id')
            
            if role_id:
                role = get_object_or_404(Role, id=role_id)
                user.role = role
            else:
                user.role = None
            
            user.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Role assigned successfully!',
                'role_name': user.role.name if user.role else 'No Role'
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)