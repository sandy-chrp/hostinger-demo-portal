from django import template

register = template.Library()

@register.filter(name='has_permission')
def has_permission(user, permission_code):
    """
    Check if user has a specific permission
    Usage: {% if user|has_permission:'view_customers' %}
    """
    if not user or not user.is_authenticated:
        return False
    
    # Superusers have all permissions
    if user.is_superuser:
        return True
    
    # Check if user has role and permission
    if hasattr(user, 'role') and user.role:
        return user.role.permissions.filter(
            codename=permission_code,
            is_active=True
        ).exists()
    
    return False


@register.filter(name='has_any_permission')
def has_any_permission(user, permission_codes):
    """
    Check if user has any of the permissions
    Usage: {% if user|has_any_permission:'view_customers,edit_customer' %}
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    codes = [code.strip() for code in permission_codes.split(',')]
    
    if hasattr(user, 'role') and user.role:
        return user.role.permissions.filter(
            codename__in=codes,
            is_active=True
        ).exists()
    
    return False


@register.filter(name='has_all_permissions')
def has_all_permissions(user, permission_codes):
    """Check if user has all of the permissions"""
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    codes = [code.strip() for code in permission_codes.split(',')]
    
    if hasattr(user, 'role') and user.role:
        # ✅ FIXED: Use codename
        user_perms = user.role.permissions.filter(
            is_active=True
        ).values_list('codename', flat=True)  # ✅ Database field
        
        return all(code in user_perms for code in codes)
    
    return False

@register.filter(name='has_role')
def has_role(user, role_name):
    """
    Check if user has specific role
    
    Usage:
        {% if user|has_role:'Admin' %}
            ...
        {% endif %}
    """
    if not user or not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if not user.role:
        return False
    
    return user.role.name == role_name


@register.simple_tag
def user_permissions(user):
    """
    Get all user permissions as list
    
    Usage:
        {% user_permissions user as perms %}
        {% for perm in perms %}
            {{ perm.name }}
        {% endfor %}
    """
    if not user or not user.is_authenticated:
        return []
    
    return user.get_all_permissions()


@register.simple_tag
def user_role_name(user):
    """
    Get user's role name
    
    Usage:
        <p>Your role: {% user_role_name user %}</p>
    """
    if not user or not user.is_authenticated:
        return "Guest"
    
    if user.is_superuser:
        return "Superuser"
    
    if user.role:
        return user.role.name
    
    return "No Role"


@register.inclusion_tag('accounts/partials/permission_check.html')
def show_if_permission(user, permission_codename):
    """
    Inclusion tag to show/hide content based on permission
    
    Usage:
        {% show_if_permission user 'view_customers' %}
            <a href="...">View Customers</a>
        {% endshow_if_permission %}
    """
    return {
        'has_permission': has_permission(user, permission_codename)
    }