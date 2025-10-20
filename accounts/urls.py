# accounts/urls.py

from django.urls import path
from accounts.views import (
    # Customer views
    signup_view, verify_otp_view, resend_otp_view, signin_view, signout_view,
    pending_approval_view, account_blocked_view, profile, forgot_password_view,
    reset_password_view, verify_email_view, resend_verification_view,
    edit_profile_view, change_password_view, check_email_exists,
    contact_sales_view, get_country_from_ip, get_subcategories,
)

# Import modules for RBAC and User Management
from accounts.views import rbac_views, user_management_views

app_name = 'accounts'

urlpatterns = [
    # ==========================================
    # CUSTOMER AUTHENTICATION & PROFILE
    # ==========================================
    path('signup/', signup_view, name='signup'),
    path('verify-otp/', verify_otp_view, name='verify_otp'),
    path('resend-otp/', resend_otp_view, name='resend_otp'),
    path('signin/', signin_view, name='signin'),
    path('signout/', signout_view, name='signout'),
    path('pending-approval/', pending_approval_view, name='pending_approval'),
    path('account-blocked/', account_blocked_view, name='account_blocked'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('reset-password/<str:token>/', reset_password_view, name='reset_password'),
    path('verify-email/<str:token>/', verify_email_view, name='verify_email'),
    path('resend-verification/', resend_verification_view, name='resend_verification'),
    
    # Profile Management
    path('profile/', profile, name='profile'),
    path('profile/edit/', edit_profile_view, name='edit_profile'),
    path('profile/change-password/', change_password_view, name='change_password'),
    
    # AJAX Endpoints
    path('check-email/', check_email_exists, name='check_email_exists'),
    path('get-country/', get_country_from_ip, name='get_country_from_ip'),
    path('get-subcategories/', get_subcategories, name='get_subcategories'),
    path('contact-sales/', contact_sales_view, name='contact_sales'),
    
    # ==========================================
    # RBAC (ROLES & PERMISSIONS)
    # ==========================================
    path('admin/roles/', rbac_views.role_list, name='role_list'),
    path('admin/roles/add/', rbac_views.role_add, name='role_add'),
    path('admin/roles/<int:role_id>/edit/', rbac_views.role_edit, name='role_edit'),
    path('admin/roles/<int:role_id>/detail/', rbac_views.role_detail, name='role_detail'),
    path('admin/roles/<int:role_id>/delete/', rbac_views.role_delete, name='role_delete'),
    
    path('admin/permissions/', rbac_views.permission_list, name='permission_list'),
    path('admin/permissions/add/', rbac_views.permission_add, name='permission_add'),
    path('admin/permissions/<int:permission_id>/edit/', rbac_views.permission_edit, name='permission_edit'),
    path('admin/permissions/<int:permission_id>/delete/', rbac_views.permission_delete, name='permission_delete'),
    
    # ==========================================
    # USER MANAGEMENT
    # ==========================================
    path('admin/users/', user_management_views.user_list, name='user_list'),
    path('admin/users/add/', user_management_views.user_add, name='user_add'),
    path('admin/users/<int:user_id>/', user_management_views.user_detail, name='user_detail'),
    path('admin/users/<int:user_id>/edit/', user_management_views.user_edit, name='user_edit'),
    path('admin/users/<int:user_id>/delete/', user_management_views.user_delete, name='user_delete'),
    path('ajax/check-employee-email/', user_management_views.check_employee_email, name='check_employee_email'),
    path('ajax/check-employee-id/', user_management_views.check_employee_id, name='check_employee_id'),
]
