# core/urls.py - CORRECTED WITH WEBGL SUPPORT

from django.urls import path
from . import views
from core import category_views
from . import demo_request_views
from . import admin_customer_views
from . import business_categories_views
from . import admin_notification_views
from . import admin_settings_views
from .views import get_subcategories_ajax, get_subcategories_for_category
from . import user_activity_analytics_views
from notifications.models import Notification

# Import WebGL views
from . import webgl_views
from . import lms_views

app_name = 'core'

urlpatterns = [
    # =====================================
    # CUSTOMER PORTAL URLs
    # =====================================
    
    # Landing Page & Home
    # path('', views.landing_page_view, name='home'),

    path('contact/', views.contact_view, name='contact'),
    path('contact-sales/', views.contact_sales_view, name='contact_sales'),
    
    # =====================================
    # ADMIN AUTHENTICATION
    # =====================================
    
    # Admin Authentication
    path('', views.admin_login_view, name='admin_login'),
    path('logout/', views.admin_logout_view, name='admin_logout'),
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    
    # path('dashboard/', views.dashboard_redirect, name='dashboard'),

    # =====================================
    # ADMIN CUSTOMER MANAGEMENT (CRUD)
    # =====================================
    
    path('customers/', admin_customer_views.admin_customers_list, name='admin_users'),
    path('customers/create/', admin_customer_views.admin_create_customer, name='admin_create_customer'),
    path('customers/export/', admin_customer_views.admin_customer_export_view, name='admin_customer_export'),
    path('customers/<int:customer_id>/', admin_customer_views.admin_customer_detail, name='admin_customer_detail'),
    path('customers/<int:customer_id>/edit/', admin_customer_views.admin_edit_customer, name='admin_edit_customer'),
    path('customers/<int:customer_id>/approve/', admin_customer_views.admin_approve_customer, name='admin_approve_customer'),
    path('customers/<int:customer_id>/block/', admin_customer_views.admin_block_customer, name='admin_block_customer'),
    path('customers/<int:customer_id>/unblock/', admin_customer_views.admin_unblock_customer, name='admin_unblock_customer'),
    path('customers/<int:customer_id>/delete/', admin_customer_views.admin_delete_customer, name='admin_delete_customer'),
    path('customers/bulk-actions/', admin_customer_views.admin_bulk_customer_actions, name='admin_bulk_customer_actions'),
    path('customers/bulk-import/', admin_customer_views.admin_bulk_import_customers, name='admin_bulk_import_customers'),
    path('customers/import-template/', admin_customer_views.download_import_template, name='download_import_template'),
    path('customers/export/', 
         admin_customer_views.admin_customer_export_view, 
         name='admin_customer_export'),
    
    # =====================================
    # ADMIN DEMO MANAGEMENT  
    # =====================================
    
    # Demo List & Management
    path('demos/', views.admin_demos_view, name='admin_demos'),
    path('demos/add/', views.admin_add_demo_view, name='admin_add_demo'),
    path('demos/stats/', views.admin_demo_stats_view, name='admin_demo_stats'),
    path('demos/bulk-actions/', views.admin_bulk_demo_actions_view, name='admin_bulk_demo_actions'),
    
    # Individual Demo Operations
    path('demos/<int:demo_id>/', views.admin_demo_detail_view, name='admin_demo_detail'),
    path('demos/<int:demo_id>/watch/', views.admin_demo_watch_view, name='admin_demo_watch'),
    path('demos/<int:demo_id>/delete/', views.admin_delete_demo_view, name='admin_delete_demo'),
    path('demos/<int:demo_id>/toggle-status/', views.admin_toggle_demo_status_view, name='admin_toggle_demo_status'),
    path('demos/filter/', demo_request_views.admin_get_filtered_demos, name='admin_filter_demos'),

    # =====================================
    # ✅ WEBGL DEMO VIEWING & SERVING - CORRECTED
    # =====================================
    
    # Admin WebGL Preview Routes
    path('webgl-preview/<int:demo_id>/', 
         webgl_views.webgl_preview, 
         name='admin_webgl_preview'),

     path('api/webgl/extraction-progress/<int:demo_id>/',
          webgl_views.webgl_extraction_progress,
          name='webgl_extraction_progress'),

     path('lms-preview/<int:demo_id>/', 
          lms_views.lms_preview, 
          name='admin_lms_preview'),
     
     path('api/lms/extraction-progress/<int:demo_id>/',
          lms_views.lms_extraction_progress,
          name='lms_extraction_progress'),
     
     path('lms-info/<int:demo_id>/', 
          lms_views.lms_file_info, 
          name='lms_file_info'),

     path('demo/lms/<slug:slug>/<path:filepath>', 
          lms_views.serve_lms_file, 
          name='serve_lms_file'),     
    
    # ✅ CRITICAL: Serve WebGL Extracted Files (slug + filepath)
     path('demo/webgl/<slug:slug>/<path:filepath>', 
          webgl_views.serve_webgl_file, 
          name='serve_webgl_file'),
    # WebGL Content Serving (demo_id based - for backward compatibility)
    path('webgl/serve/<int:demo_id>/', 
         webgl_views.serve_webgl_content, 
         name='serve_webgl_content'),
    
    # WebGL Asset Serving (demo_id + asset_path)
    path('api/webgl-asset/<int:demo_id>/<path:asset_path>/', 
         webgl_views.serve_webgl_asset, 
         name='serve_webgl_asset'),
    
    # WebGL Debug/Info (Admin Only)
    path('webgl-info/<int:demo_id>/', 
         webgl_views.webgl_file_info, 
         name='webgl_file_info'),

    # =====================================
    # ADMIN ENQUIRY MANAGEMENT
    # =====================================
    
    path('enquiries/', views.admin_enquiries_view, name='admin_enquiries'),
    path('enquiries/<int:enquiry_id>/', views.admin_enquiry_detail_view, name='admin_enquiry_detail'),
    path('enquiries/<int:enquiry_id>/respond/', views.admin_respond_enquiry_view, name='admin_respond_enquiry'),
    path('enquiries/<int:enquiry_id>/delete/', views.admin_delete_enquiry_view, name='admin_delete_enquiry'),
    path('enquiries/<int:enquiry_id>/assign/', views.admin_assign_enquiry_view, name='admin_assign_enquiry'),
    path('enquiries/<int:enquiry_id>/update-priority/', views.admin_update_enquiry_priority_view, name='admin_update_enquiry_priority'),
    path('enquiries/export/', views.admin_export_enquiries_view, name='admin_export_enquiries'),
        
    # =====================================
    # ADMIN DEMO REQUEST MANAGEMENT
    # =====================================
    
    path('demo-requests/', demo_request_views.admin_demo_requests_list_view, name='admin_demo_requests'),
    path('demo-requests/create/', demo_request_views.admin_create_demo_request_view, name='admin_create_demo_request'),
    path('demo-requests/calendar/', demo_request_views.admin_demo_requests_calendar_view, name='admin_demo_requests_calendar'),
    path('demo-requests/bulk-actions/', demo_request_views.admin_bulk_demo_request_actions_view, name='admin_bulk_demo_request_actions'),
    
    # Individual Demo Request Operations
    path('demo-requests/<int:request_id>/', demo_request_views.admin_demo_request_detail_view, name='admin_demo_request_detail'),
    path('demo-requests/<int:request_id>/edit/', demo_request_views.admin_edit_demo_request_view, name='admin_edit_demo_request'),
    path('demo-requests/<int:request_id>/delete/', demo_request_views.admin_delete_demo_request_view, name='admin_delete_demo_request'),
    path('demo-requests/<int:request_id>/confirm/', demo_request_views.admin_confirm_demo_request_view, name='admin_confirm_demo_request'),
    path('demo-requests/ajax-check-slots/', demo_request_views.ajax_admin_check_slot_availability, name='ajax_admin_check_slot_availability'),
    path('demo-requests/<int:request_id>/mark-complete/', 
     demo_request_views.mark_demo_request_complete, 
     name='mark_demo_request_complete'),
    path('demo-requests/<int:request_id>/update-notes/', demo_request_views.update_admin_notes, name='update_admin_notes'),
          
          
    # =====================================
    # ADMIN CATEGORY MANAGEMENT
    # =====================================
    
    # Category List & Management
    path('categories/', category_views.admin_categories_view, name='admin_categories'),
    path('categories/add/', category_views.admin_add_category_view, name='admin_add_category'),
    path('categories/export/', category_views.admin_category_export_view, name='admin_category_export'),
    path('categories/stats/', category_views.admin_category_stats_view, name='admin_category_stats'),
    path('categories/bulk-actions/', category_views.admin_bulk_category_actions_view, name='admin_bulk_category_actions'),
    path('categories/reorder/', category_views.admin_reorder_categories_view, name='admin_reorder_categories'),
    path('api/subcategories/', get_subcategories_ajax, name='get_subcategories_ajax'),
#     path('auth/ajax/get-subcategories/', get_subcategories_for_category, name='get_subcategories'),

    # Business Category Management
    path('business-categories/', business_categories_views.admin_business_categories, name='admin_business_categories'),
    path('business-categories/create/', business_categories_views.admin_business_category_create, name='admin_business_category_create'),
    path('business-categories/<int:category_id>/edit/', business_categories_views.admin_business_category_edit, name='admin_business_category_edit'),
    path('business-categories/<int:category_id>/delete/', business_categories_views.admin_business_category_delete, name='admin_business_category_delete'),
    path('business-categories/<int:category_id>/toggle-status/', business_categories_views.admin_business_category_toggle_status, name='admin_business_category_toggle_status'),
    # Business Subcategory Management
    path('business-subcategories/', business_categories_views.admin_business_subcategories, name='admin_business_subcategories'),
    path('business-subcategories/create/', business_categories_views.admin_business_subcategory_create, name='admin_business_subcategory_create'),
    path('business-subcategories/<int:subcategory_id>/edit/', business_categories_views.admin_business_subcategory_edit, name='admin_business_subcategory_edit'),
    path('business-subcategories/<int:subcategory_id>/delete/', business_categories_views.admin_business_subcategory_delete, name='admin_business_subcategory_delete'),
    path('business-subcategories/<int:subcategory_id>/toggle-status/', business_categories_views.admin_business_subcategory_toggle_status, name='admin_business_subcategory_toggle_status'),
     path('auth/ajax/get-subcategories/',  views.get_subcategories_for_category,  name='get_subcategories'),
     #   path('ajax/get-subcategories/', views.admin_get_subcategories,name='admin_get_subcategories'),
      
           
        
    
    # Individual Category Operations
    path('categories/<int:category_id>/', category_views.admin_category_detail_view, name='admin_category_detail'),
    path('categories/<int:category_id>/edit/', category_views.admin_edit_category_view, name='admin_edit_category'),
    path('categories/<int:category_id>/delete/', category_views.admin_delete_category_view, name='admin_delete_category'),
    path('categories/<int:category_id>/toggle-status/', category_views.admin_toggle_category_status_view, name='admin_toggle_category_status'),
    path('categories/<int:category_id>/duplicate/', category_views.admin_category_duplicate_view, name='admin_duplicate_category'),
    
    # =====================================
    # ADMIN SETTINGS & SYSTEM
    # =====================================
    
    # Main Settings Dashboard
    path('settings/', admin_settings_views.admin_settings_view, name='admin_settings'),
    # Site Configuration
    path('settings/site/', admin_settings_views.admin_site_settings_view, name='admin_site_settings'),
    # Demo Settings
    path('settings/demo/', admin_settings_views.admin_demo_settings_view, name='admin_demo_settings'),
    # Email Settings
    path('settings/email/', admin_settings_views.admin_email_settings_view, name='admin_email_settings'),
    # Security Settings
    path('settings/security/', admin_settings_views.admin_security_settings_view, name='admin_security_settings'),
    # Maintenance Settings
    path('settings/maintenance/', admin_settings_views.admin_maintenance_settings_view, name='admin_maintenance_settings'),
    # Backup Settings
    path('settings/backup/', admin_settings_views.admin_backup_settings_view, name='admin_backup_settings'),
    # System Health
    path('settings/health/', admin_settings_views.admin_system_health_view, name='admin_system_health'),
    # Cache Operations
    path('settings/clear-cache/', admin_settings_views.admin_clear_cache, name='admin_clear_cache'),

    # =====================================
    # ADMIN NOTIFICATION MANAGEMENT
    # =====================================

    # Main Notifications Dashboard
    path('notifications/', admin_notification_views.admin_notifications_view, name='admin_notifications'),

    # Notification Statistics and Settings
    path('notifications/stats/', admin_notification_views.admin_notification_stats, name='admin_notification_stats'),
    path('notifications/settings/', admin_notification_views.admin_notification_settings, name='admin_notification_settings'),

    # Notification Templates Management
    path('notifications/templates/', admin_notification_views.admin_notification_templates_view, name='admin_notification_templates'),
    path('notifications/templates/<int:template_id>/edit/', admin_notification_views.admin_edit_notification_template, name='admin_edit_notification_template'),

    # System Announcements
    path('notifications/announcements/', admin_notification_views.admin_system_announcements_view, name='admin_system_announcements'),
    path('notifications/announcements/create/', admin_notification_views.admin_create_announcement, name='admin_create_announcement'),
    path('notifications/announcements/<int:announcement_id>/edit/', admin_notification_views.admin_edit_announcement, name='admin_edit_announcement'),
    path('notifications/announcements/<int:announcement_id>/delete/', admin_notification_views.admin_delete_announcement, name='admin_delete_announcement'),

    # Bulk Operations
    path('notifications/send-bulk/', admin_notification_views.admin_send_bulk_notification, name='admin_send_bulk_notification'),
    path('notifications/bulk-actions/', admin_notification_views.admin_bulk_notification_actions, name='admin_bulk_notification_actions'),

    # Individual Notification Operations
    path('notifications/<int:notification_id>/mark-read/', admin_notification_views.admin_mark_notification_read, name='admin_mark_notification_read'),
    path('notifications/<int:notification_id>/delete/', admin_notification_views.admin_delete_notification, name='admin_delete_notification'),
        
    # =====================================
    # AJAX/API ENDPOINTS
    # =====================================
    
    # Customer Portal AJAX
    path('ajax/contact-sales/', views.ajax_contact_sales, name='ajax_contact_sales'),
    
    # Admin AJAX Endpoints
    path('ajax/system-health/', views.ajax_system_health, name='ajax_system_health'),
    path('ajax/validate-email/', views.validate_business_email_ajax, name='validate_business_email_ajax'),

    path('customers/send-otp/', admin_customer_views.send_email_otp, name='admin_send_otp'),
    path('customers/verify-otp/', admin_customer_views.verify_email_otp, name='admin_verify_otp'),

    path('activity-analytics/', 
         user_activity_analytics_views.user_activity_analytics_page, 
         name='user_activity_analytics'),
    
    path('ajax/activity-analytics/', 
         user_activity_analytics_views.ajax_activity_analytics, 
         name='ajax_activity_analytics'),
    
    path('ajax/quick-stats/', 
         user_activity_analytics_views.ajax_quick_stats, 
         name='ajax_quick_stats'),

    path('ajax/registration-data/', 
     user_activity_analytics_views.ajax_registration_data, 
     name='ajax_registration_data'), 

    path('save-column-preferences/', 
         admin_customer_views.save_column_preferences, 
         name='save_column_preferences'),        


    path('demo-requests/<int:request_id>/assign/', 
     demo_request_views.assign_demo_request, 
     name='assign_demo_request'),

    path('demo-requests/<int:request_id>/unassign/', 
          demo_request_views.unassign_demo_request, 
          name='unassign_demo_request'),

    # API endpoints
    path('api/demo-requests/check-availability/', 
          demo_request_views.check_employee_availability, 
          name='check_employee_availability'),

    path('api/demo-requests/available-employees/', 
          demo_request_views.get_available_employees, 
          name='get_available_employees'),
   

    path('employee/demo-requests/', 
          demo_request_views.employee_demo_requests_list, 
          name='employee_demo_requests'),

    path('employee/demo-requests/<int:request_id>/', 
          demo_request_views.employee_demo_request_detail, 
          name='employee_demo_request_detail'),
    
    path('api/demo-requests/available-slots/', 
         demo_request_views.available_time_slots_api, 
         name='api_available_slots'),
    
    path('api/demo-requests/available-employees/', 
         demo_request_views.available_employees_api, 
         name='api_available_employees'),
    
    path('demo-requests/<int:request_id>/reschedule/', 
          demo_request_views.reschedule_demo_request, 
          name='reschedule_demo_request'),

    path('demo-requests/<int:request_id>/reactivate/', 
          demo_request_views.reactivate_demo_request, 
          name='reactivate_demo_request'),
]