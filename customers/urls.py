# customers/urls.py

from django.urls import path, re_path
from . import views
from . import liked_demos_views
from . import security_views

app_name = 'customers'

urlpatterns = [
    # Dashboard
    path('', views.customer_dashboard, name='dashboard'),
    
    # ===== CRITICAL: EXACT ORDER MATTERS =====
    # Most specific patterns FIRST, generic patterns LAST
    
    # Demo Section
    path('demos/', views.browse_demos, name='browse_demos'),
    
    # ✅ 1. WebGL/LMS file serving (MOST SPECIFIC - must be first)
    re_path(
        r'^demos/(?P<slug>[\w-]+)/webgl-content/(?P<filepath>.+)$',
        views.serve_webgl_file,
        name='serve_webgl_file'
    ),
    
    # ✅ 2. WebGL 3D Viewer (specific route)
    path('demos/<slug:slug>/view-3d/', views.webgl_viewer, name='webgl_viewer'),
    
    # ✅ 3. Demo feedback (specific route)
    path('demos/<slug:slug>/feedback/', views.demo_feedback_view, name='demo_feedback'),
    
    # ✅ 4. Demo detail (LEAST SPECIFIC - must be last among demo routes)
    path('demos/<slug:slug>/', views.demo_detail, name='demo_detail'),
    
    # Demo requests
    path('request-demo/', views.request_demo, name='request_demo'),
    path('my-requests/', views.demo_requests, name='demo_requests'),
    
    # Business Enquiries
    path('enquiries/', views.enquiries, name='enquiries'),
    path('send-enquiry/', views.send_enquiry, name='send_enquiry'),
    path('contact-sales/', views.contact_sales, name='contact_sales'),
    
    # Liked Demos
    path('liked-demos/', liked_demos_views.liked_demos, name='liked_demos'),
    path('demos/<int:demo_id>/like/', views.toggle_like, name='toggle_like'),

    # Notifications
    path('notifications/', views.notifications, name='notifications'),
    
    # AJAX Endpoints
    path('ajax/subcategories/<int:category_id>/', views.ajax_subcategories, name='ajax_subcategories'),
    path('ajax/demos/', views.ajax_demos_by_category, name='ajax_demos_by_category'),
    path('ajax/demo/<int:demo_id>/', views.ajax_demo_detail, name='ajax_demo_detail'),
    path('ajax/demo-request/<int:request_id>/cancel/', views.cancel_demo_request, name='cancel_demo_request'),
    path('ajax/check-slot-availability/', views.ajax_check_slot_availability, name='check_slot_availability'),
    path('ajax/booking-calendar/', views.ajax_get_booking_calendar, name='booking_calendar'),
    path('ajax/demo/<int:demo_id>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('ajax/notification/<int:notification_id>/mark-read/', views.mark_notification_read, name='mark_notification_read'),
    path('ajax/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),

    # Security
    path('ajax/log-security-violation/', views.log_security_violation, name='log_security_violation'),
    path('ajax/log-security-violation/', security_views.log_security_violation, name='log_security_violation'),
    path('security/logout/', security_views.security_logout, name='security_logout'),
]