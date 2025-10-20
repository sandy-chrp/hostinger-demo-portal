"""
Permission definitions for role-based access control
"""

# All available permissions
PERMISSIONS = {
    # Customer Management
    'view_all_customers': {
        'name': 'View All Customers',
        'description': 'Can view all customer records',
        'module': 'Customers',
        'roles': ['superadmin', 'admin', 'manager']
    },
    'edit_customers': {
        'name': 'Edit Customers',
        'description': 'Can edit customer information',
        'module': 'Customers',
        'roles': ['superadmin', 'admin']
    },
    'approve_customers': {
        'name': 'Approve Customers',
        'description': 'Can approve/reject customer registrations',
        'module': 'Customers',
        'roles': ['superadmin', 'admin']
    },
    'delete_customers': {
        'name': 'Delete Customers',
        'description': 'Can delete customer accounts',
        'module': 'Customers',
        'roles': ['superadmin']
    },
    'block_customers': {
        'name': 'Block/Unblock Customers',
        'description': 'Can block or unblock customer accounts',
        'module': 'Customers',
        'roles': ['superadmin', 'admin']
    },
    
    # Demo Management
    'manage_demos': {
        'name': 'Manage Demos',
        'description': 'Can create, edit, delete demos',
        'module': 'Demos',
        'roles': ['superadmin', 'admin']
    },
    'view_demos': {
        'name': 'View Demos',
        'description': 'Can view demo library',
        'module': 'Demos',
        'roles': ['superadmin', 'admin', 'sales', 'manager', 'customer']
    },
    'assign_demo_access': {
        'name': 'Assign Demo Access',
        'description': 'Can assign demos to customers',
        'module': 'Demos',
        'roles': ['superadmin', 'admin', 'sales']
    },
    'view_demo_analytics': {
        'name': 'View Demo Analytics',
        'description': 'Can view demo views and engagement stats',
        'module': 'Demos',
        'roles': ['superadmin', 'admin', 'manager']
    },
    
    # Demo Requests
    'view_all_demo_requests': {
        'name': 'View All Demo Requests',
        'description': 'Can view all demo requests',
        'module': 'Demo Requests',
        'roles': ['superadmin', 'admin', 'manager']
    },
    'manage_demo_requests': {
        'name': 'Manage Demo Requests',
        'description': 'Can approve/reject demo requests',
        'module': 'Demo Requests',
        'roles': ['superadmin', 'admin', 'sales']
    },
    
    # Enquiry Management
    'view_all_enquiries': {
        'name': 'View All Enquiries',
        'description': 'Can view all customer enquiries',
        'module': 'Enquiries',
        'roles': ['superadmin', 'admin', 'manager']
    },
    'manage_enquiries': {
        'name': 'Manage Enquiries',
        'description': 'Can respond to and update enquiries',
        'module': 'Enquiries',
        'roles': ['superadmin', 'admin', 'sales', 'manager']
    },
    'view_own_enquiries': {
        'name': 'View Assigned Enquiries',
        'description': 'Can view only assigned enquiries',
        'module': 'Enquiries',
        'roles': ['sales']
    },
    'assign_enquiries': {
        'name': 'Assign Enquiries',
        'description': 'Can assign enquiries to team members',
        'module': 'Enquiries',
        'roles': ['superadmin', 'admin', 'manager']
    },
    
    # Sales Management
    'register_sales': {
        'name': 'Register Sales Users',
        'description': 'Can register new sales employees',
        'module': 'Sales',
        'roles': ['superadmin', 'admin']
    },
    'view_sales_team': {
        'name': 'View Sales Team',
        'description': 'Can view sales team members',
        'module': 'Sales',
        'roles': ['superadmin', 'admin', 'manager']
    },
    'manage_sales_users': {
        'name': 'Manage Sales Users',
        'description': 'Can edit/deactivate sales users',
        'module': 'Sales',
        'roles': ['superadmin', 'admin']
    },
    'view_team_members': {
        'name': 'View Team Members',
        'description': 'Can view own team members',
        'module': 'Sales',
        'roles': ['manager']
    },
    
    # Role Management
    'manage_roles': {
        'name': 'Manage Roles',
        'description': 'Can create and edit roles',
        'module': 'Roles',
        'roles': ['superadmin']
    },
    'assign_roles': {
        'name': 'Assign Roles',
        'description': 'Can assign roles to users',
        'module': 'Roles',
        'roles': ['superadmin', 'admin']
    },
    'view_roles': {
        'name': 'View Roles',
        'description': 'Can view role list',
        'module': 'Roles',
        'roles': ['superadmin', 'admin', 'manager']
    },
    
    # Department Management
    'manage_departments': {
        'name': 'Manage Departments',
        'description': 'Can create and edit departments',
        'module': 'Departments',
        'roles': ['superadmin', 'admin']
    },
    
    # Reports & Analytics
    'view_all_reports': {
        'name': 'View All Reports',
        'description': 'Can view all system reports',
        'module': 'Reports',
        'roles': ['superadmin', 'admin', 'manager']
    },
    'view_team_reports': {
        'name': 'View Team Reports',
        'description': 'Can view team performance',
        'module': 'Reports',
        'roles': ['manager']
    },
    'view_own_reports': {
        'name': 'View Own Reports',
        'description': 'Can view personal performance',
        'module': 'Reports',
        'roles': ['sales']
    },
    
    # System Settings
    'manage_settings': {
        'name': 'Manage System Settings',
        'description': 'Can modify system settings',
        'module': 'System',
        'roles': ['superadmin']
    },
    'view_audit_logs': {
        'name': 'View Audit Logs',
        'description': 'Can view system audit logs',
        'module': 'System',
        'roles': ['superadmin', 'admin']
    },
}

# Role hierarchy for permission checking
ROLE_HIERARCHY = {
    'superadmin': 5,  # Highest
    'admin': 4,
    'manager': 3,
    'sales': 2,
    'customer': 1,    # Lowest
}


def get_role_permissions(role_name):
    """
    Get all permissions for a specific role
    
    Args:
        role_name (str): Role name (e.g., 'sales', 'admin')
    
    Returns:
        list: List of permission keys
    """
    return [
        perm_key for perm_key, perm_data in PERMISSIONS.items()
        if role_name in perm_data['roles']
    ]


def check_permission(user, permission_key):
    """
    Check if user has specific permission
    
    Args:
        user: User object
        permission_key (str): Permission key (e.g., 'manage_demos')
    
    Returns:
        bool: True if user has permission
    """
    if not user.is_authenticated:
        return False
    
    # Superuser has all permissions
    if user.is_superuser:
        return True
    
    # Check if user has role
    if not user.role:
        return False
    
    # Check in role's custom JSON permissions
    if user.role.permissions.get(permission_key, False):
        return True
    
    # Check in predefined permissions
    return permission_key in get_role_permissions(user.role.name)


def can_manage_user(manager_user, target_user):
    """
    Check if manager can manage target user based on hierarchy
    
    Args:
        manager_user: Manager user object
        target_user: Target user object
    
    Returns:
        bool: True if manager can manage target user
    """
    # Superuser can manage anyone
    if manager_user.is_superuser:
        return True
    
    # Both must have roles
    if not manager_user.role or not target_user.role:
        return False
    
    # Get hierarchy levels
    manager_level = ROLE_HIERARCHY.get(manager_user.role.name, 0)
    target_level = ROLE_HIERARCHY.get(target_user.role.name, 0)
    
    # Manager must have higher level
    return manager_level > target_level


def get_permissions_by_module():
    """
    Group permissions by module for UI display
    
    Returns:
        dict: Permissions grouped by module
    """
    modules = {}
    for perm_key, perm_data in PERMISSIONS.items():
        module = perm_data.get('module', 'Other')
        if module not in modules:
            modules[module] = []
        modules[module].append({
            'key': perm_key,
            **perm_data
        })
    return modules


def get_user_permissions_list(user):
    """
    Get list of all permissions user has
    
    Args:
        user: User object
    
    Returns:
        list: List of permission keys user has
    """
    if not user.is_authenticated:
        return []
    
    if user.is_superuser:
        return list(PERMISSIONS.keys())
    
    if not user.role:
        return []
    
    # Get permissions from role
    permissions = get_role_permissions(user.role.name)
    
    # Add custom permissions from role's JSON field
    custom_perms = [k for k, v in user.role.permissions.items() if v]
    
    return list(set(permissions + custom_perms))


def has_any_permission(user, permission_keys):
    """
    Check if user has any of the given permissions
    
    Args:
        user: User object
        permission_keys (list): List of permission keys
    
    Returns:
        bool: True if user has at least one permission
    """
    return any(check_permission(user, perm) for perm in permission_keys)


def has_all_permissions(user, permission_keys):
    """
    Check if user has all of the given permissions
    
    Args:
        user: User object
        permission_keys (list): List of permission keys
    
    Returns:
        bool: True if user has all permissions
    """
    return all(check_permission(user, perm) for perm in permission_keys)