"""
Views package for accounts app
"""

# Import all customer views
from .customer_views import (
    signup_view,
    verify_otp_view,
    resend_otp_view,
    signin_view,
    signout_view,
    pending_approval_view,
    account_blocked_view,
    profile,
    forgot_password_view,
    reset_password_view,
    verify_email_view,
    resend_verification_view,
    edit_profile_view,
    change_password_view,
    check_email_exists,
    contact_sales_view,
    get_country_from_ip,
    get_subcategories,
)

# Import RBAC views
from . import rbac_views

# Import User Management views
from . import user_management_views


__all__ = [
    # Customer views
    'signup_view',
    'verify_otp_view',
    'resend_otp_view',
    'signin_view',
    'signout_view',
    'pending_approval_view',
    'account_blocked_view',
    'profile',
    'forgot_password_view',
    'reset_password_view',
    'verify_email_view',
    'resend_verification_view',
    'edit_profile_view',
    'change_password_view',
    'check_email_exists',
    'contact_sales_view',
    'get_country_from_ip',
    'get_subcategories',
    
    # RBAC views module
    'rbac_views',
    
    # User Management views module
    'user_management_views',
]
