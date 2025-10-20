"""
Main views module - imports from submodules
"""

# Import all customer views
from .views.customer_views import *

# Import all sales views
from .views import sales_views

# For backwards compatibility
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
]