from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Q,Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
import json
import csv
from django.db import models  # Add this import
# Get the custom user model
User = get_user_model()  # This will give us User
from enquiries.models import BusinessEnquiry, EnquiryResponse, EnquiryCategory
from demos.models import Demo, DemoRequest, DemoView, DemoLike, DemoCategory
from enquiries.models import BusinessEnquiry
from notifications.models import Notification, SystemAnnouncement
from .models import SiteSettings, ContactMessage
from django.db.models.functions import ExtractHour
from accounts.decorators import permission_required
from accounts.models import BusinessCategory, BusinessSubCategory  
from accounts.models import CustomUser 
# FIXED - Correct import from accounts app
from django.views.decorators.http import require_GET, require_POST
from django.core.paginator import Paginator
from demos.forms import AdminDemoForm

# File size limits (in bytes)
FILE_SIZE_LIMITS = {
    'video': 200 * 1024 * 1024,      # 200 MB
    'webgl': 3 * 1024 * 1024 * 1024,  # 3 GB
    'thumbnail': 10 * 1024 * 1024,    # 10 MB
}

def validate_file_size(file, file_type):
    """
    Validate file size based on type
    Returns: (is_valid: bool, error_message: str or None)
    """
    if not file:
        return True, None
    
    max_size = FILE_SIZE_LIMITS.get(file_type, 100 * 1024 * 1024)  # Default 100MB
    file_size = file.size
    
    if file_size > max_size:
        # Format max size
        max_size_mb = max_size / (1024 * 1024)
        if max_size_mb >= 1024:
            max_size_display = f"{max_size_mb / 1024:.1f} GB"
        else:
            max_size_display = f"{max_size_mb:.0f} MB"
        
        # Format actual size
        actual_size_mb = file_size / (1024 * 1024)
        if actual_size_mb >= 1024:
            actual_size_display = f"{actual_size_mb / 1024:.2f} GB"
        else:
            actual_size_display = f"{actual_size_mb:.2f} MB"
        
        error_msg = f"File size ({actual_size_display}) exceeds maximum allowed size ({max_size_display})"
        return False, error_msg
    
    return True, None

# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def custom_404(request, exception=None):
    """Custom 404 error handler"""
    return render(request, '404.html', status=404)

def custom_500(request):
    """Custom 500 error handler"""
    return render(request, '500.html', status=500)

# =====================================
# CUSTOMER PORTAL VIEWS

@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    """Main admin dashboard with statistics and demographics - OPTIMIZED"""
    
    # Get activity period from request
    activity_period = request.GET.get('period', 'daily')
    
    # Date ranges for statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # ===== BASIC STATS (Fast Queries) =====
    # Use select_related and prefetch_related to reduce queries
    
    # User Statistics - FILTER OUT ADMIN/STAFF USERS
    user_base_query = User.objects.filter(is_staff=False, is_superuser=False)
    
    total_users = user_base_query.count()
    new_users_today = user_base_query.filter(created_at__date=today).count()
    new_users_week = user_base_query.filter(created_at__date__gte=week_ago).count()
    pending_approvals = user_base_query.filter(is_approved=False, is_active=True).count()
    active_users = user_base_query.filter(is_active=True, is_approved=True).count()
    
    # Demo Statistics (Optimized)
    total_demos = Demo.objects.count()
    active_demos = Demo.objects.filter(is_active=True).count()
    total_demo_views = DemoView.objects.count()
    demo_views_today = DemoView.objects.filter(viewed_at__date=today).count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    # Enquiry Statistics (Optimized)
    total_enquiries = BusinessEnquiry.objects.count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    new_enquiries_today = BusinessEnquiry.objects.filter(created_at__date=today).count()
    
    # ===== RECENT ACTIVITY (Limited to 5, Optimized) =====
    recent_users = user_base_query.only('id', 'first_name', 'last_name', 'email', 'organization', 'created_at').order_by('-created_at')[:5]
    recent_enquiries = BusinessEnquiry.objects.only('id', 'first_name', 'last_name', 'enquiry_id', 'organization', 'created_at').order_by('-created_at')[:5]
    recent_demo_requests = DemoRequest.objects.select_related('user', 'demo').only(
        'id', 'requested_date', 'status', 'created_at',
        'user__first_name', 'user__last_name', 'user__organization',
        'demo__title'
    ).order_by('-created_at')[:5]
    
    # ===== POPULAR DEMOS (Optimized) =====
    popular_demos = Demo.objects.annotate(
        views_count_calc=Count('demo_views')
    ).only('id', 'title', 'is_featured', 'is_active', 'likes_count', 'created_at').order_by('-views_count_calc')[:5]
    
    # ===== USER REGISTRATION DATA (Simplified for performance) =====
    monthly_users = []
    if activity_period == 'monthly':
        # Last 6 months only
        for i in range(6):
            date = today.replace(day=1) - timedelta(days=i*30)
            count = user_base_query.filter(
                created_at__year=date.year,
                created_at__month=date.month
            ).count()
            monthly_users.append({'month': date.strftime('%b %Y'), 'count': count})
        monthly_users.reverse()
    else:
        # Last 7 days (daily)
        for i in range(7):
            date = today - timedelta(days=i)
            count = user_base_query.filter(created_at__date=date).count()
            monthly_users.append({'month': date.strftime('%m/%d'), 'count': count})
        monthly_users.reverse()
    
    # ===== WEEKLY ACTIVITY (Last 7 days only) =====
    weekly_activity = []
    for i in range(7):
        date = today - timedelta(days=i)
        weekly_activity.append({
            'date': date.strftime('%m/%d'),
            'demo_views': DemoView.objects.filter(viewed_at__date=date).count(),
            'enquiries': BusinessEnquiry.objects.filter(created_at__date=date).count(),
            'signups': user_base_query.filter(created_at__date=date).count(),
        })
    weekly_activity.reverse()
    
    # ===== DEMOGRAPHICS (Top 10 only) =====
    country_distribution = user_base_query.exclude(
        Q(country_code__isnull=True) | Q(country_code='')
    ).values('country_code').annotate(count=Count('id')).order_by('-count')[:10]
    
    # Country mapping (simplified)
    PHONE_CODE_TO_COUNTRY = {
        '+91': 'India', '+1': 'USA/Canada', '+44': 'UK', '+61': 'Australia',
        '+86': 'China', '+81': 'Japan', '+82': 'South Korea', '+49': 'Germany',
        '+33': 'France', '+39': 'Italy', '+34': 'Spain', '+92': 'Pakistan',
        '+971': 'UAE', '+966': 'Saudi Arabia', '+65': 'Singapore',
    }
    
    country_data = [
        {
            'country': PHONE_CODE_TO_COUNTRY.get(item['country_code'], item['country_code']),
            'count': item['count']
        }
        for item in country_distribution
    ]
    
    # ===== SOURCE DATA (Optimized) =====
    source_distribution = user_base_query.values('referral_source').annotate(
        count=Count('id')
    ).order_by('-count')
    
    source_labels = {
        'referral': 'Referral from colleague', 'facebook': 'Facebook',
        'youtube': 'YouTube', 'linkedin': 'LinkedIn',
        'google': 'Google Search', 'other': 'Other',
        '': 'Not Specified', None: 'Not Specified'
    }
    
    source_data = []
    for item in source_distribution:
        source_value = item['referral_source'] or ''
        source_name = source_labels.get(source_value, 'Not Specified')
        existing = next((x for x in source_data if x['source'] == source_name), None)
        if existing:
            existing['count'] += item['count']
        else:
            source_data.append({'source': source_name, 'count': item['count']})
    
    # ===== ACTIVITY ANALYTICS (Lazy Load - Only basic stats) =====
    # Heavy queries moved to AJAX endpoint for better performance
    activity_stats = {
        'active_users': 0,
        'active_users_change': 0,
        'total_views': total_demo_views,
        'views_change': 0,
        'demo_requests': demo_requests_pending,
        'requests_change': 0,
        'enquiries': open_enquiries,
        'enquiries_change': 0,
    }
    
    context = {
        # Basic Stats
        'total_users': total_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'pending_approvals': pending_approvals,
        'active_users': active_users,
        'total_demos': total_demos,
        'active_demos': active_demos,
        'total_demo_views': total_demo_views,
        'demo_views_today': demo_views_today,
        'demo_requests_pending': demo_requests_pending,
        'total_enquiries': total_enquiries,
        'open_enquiries': open_enquiries,
        'new_enquiries_today': new_enquiries_today,
        
        # Recent Activity
        'recent_users': recent_users,
        'recent_enquiries': recent_enquiries,
        'recent_demo_requests': recent_demo_requests,
        'recent_contact_messages': [],
        'popular_demos': popular_demos,
        
        # Chart Data
        'monthly_users': monthly_users,
        'weekly_activity': weekly_activity,
        'country_data': country_data,
        'source_data': source_data,
        
        # Activity Analytics (Minimal for initial load)
        'activity_stats': activity_stats,
        'user_activity_data': [],  # Load via AJAX
        'peak_hours': [],  # Load via AJAX
        'most_active_users': [],  # Load via AJAX
        'activity_period': activity_period,
        'system_health': {'database': 'healthy', 'email': 'healthy'},
    }
    
    return render(request, 'admin/dashboard.html', context)
    
    # User Statistics - FILTER OUT ADMIN/STAFF USERS
    total_users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).count()
    
    new_users_today = User.objects.filter(
        created_at__date=today,
        is_staff=False,
        is_superuser=False
    ).count()
    
    new_users_week = User.objects.filter(
        created_at__date__gte=week_ago,
        is_staff=False,
        is_superuser=False
    ).count()
    
    pending_approvals = User.objects.filter(
        is_approved=False, 
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()
    
    active_users = User.objects.filter(
        is_active=True, 
        is_approved=True,
        is_staff=False,
        is_superuser=False
    ).count()
    
    # Demo Statistics
    total_demos = Demo.objects.count()
    active_demos = Demo.objects.filter(is_active=True).count()
    total_demo_views = DemoView.objects.count()
    demo_views_today = DemoView.objects.filter(viewed_at__date=today).count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    demo_requests_today = DemoRequest.objects.filter(created_at__date=today).count()
    
    # Enquiry Statistics
    total_enquiries = BusinessEnquiry.objects.count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    new_enquiries_today = BusinessEnquiry.objects.filter(created_at__date=today).count()
    overdue_enquiries = BusinessEnquiry.objects.filter(
        status='open',
        created_at__lt=timezone.now() - timedelta(hours=24)
    ).count()
    
    # System Health
    system_health = {
        'database': 'healthy',
        'email': 'healthy',
        'storage': 'healthy',
        'cache': 'healthy',
    }
    
    # Recent Activity - FILTER OUT ADMIN USERS
    recent_users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).order_by('-created_at')[:5]
    
    recent_enquiries = BusinessEnquiry.objects.order_by('-created_at')[:5]
    recent_demo_requests = DemoRequest.objects.select_related('user', 'demo').order_by('-created_at')[:5]
    
    # Popular Demos (most viewed)
    popular_demos = Demo.objects.annotate(
        views_count_calc=Count('demo_views')
    ).order_by('-views_count_calc')[:5]
    
    # ============ DYNAMIC USER REGISTRATION DATA (WITH FILTERS) ============
    end_date = timezone.now()
    
    if activity_period == 'daily':
        start_date = end_date - timedelta(days=7)  # Last 7 days
        date_format = '%m/%d'
    elif activity_period == 'weekly':
        start_date = end_date - timedelta(weeks=12)  # Last 12 weeks
        date_format = 'Week %W'
    elif activity_period == 'monthly':
        start_date = end_date - timedelta(days=365)  # Last 12 months
        date_format = '%b %Y'
    elif activity_period == 'custom':
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        if start_date_str and end_date_str:
            from datetime import datetime
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
        else:
            start_date = end_date - timedelta(days=30)
        date_format = '%m/%d'
    else:
        start_date = end_date - timedelta(days=7)
        date_format = '%m/%d'
    
    # Monthly User Growth Chart Data
    monthly_users = []
    
    if activity_period == 'monthly':
        # Monthly breakdown for last 12 months
        for i in range(12):
            date = today.replace(day=1) - timedelta(days=i*30)
            count = User.objects.filter(
                created_at__year=date.year,
                created_at__month=date.month,
                is_staff=False,
                is_superuser=False
            ).count()
            monthly_users.append({
                'month': date.strftime('%b %Y'),
                'count': count
            })
        monthly_users.reverse()
    elif activity_period == 'weekly':
        # Weekly breakdown for last 12 weeks
        current_date = start_date.date()
        while current_date <= end_date.date():
            week_end = current_date + timedelta(days=6)
            count = User.objects.filter(
                created_at__date__range=[current_date, week_end],
                is_staff=False,
                is_superuser=False
            ).count()
            monthly_users.append({
                'month': f"Week {current_date.strftime('%W')}",
                'count': count
            })
            current_date = week_end + timedelta(days=1)
    else:
        # Daily breakdown
        current_date = start_date.date()
        while current_date <= end_date.date():
            count = User.objects.filter(
                created_at__date=current_date,
                is_staff=False,
                is_superuser=False
            ).count()
            monthly_users.append({
                'month': current_date.strftime(date_format),
                'count': count
            })
            current_date += timedelta(days=1)
    
    # Weekly Activity Data (always last 7 days)
    weekly_activity = []
    for i in range(7):  # Last 7 days
        date = today - timedelta(days=i)
        demo_views = DemoView.objects.filter(viewed_at__date=date).count()
        enquiries = BusinessEnquiry.objects.filter(created_at__date=date).count()
        signups = User.objects.filter(
            created_at__date=date,
            is_staff=False,
            is_superuser=False
        ).count()
        
        weekly_activity.append({
            'date': date.strftime('%m/%d'),
            'demo_views': demo_views,
            'enquiries': enquiries,
            'signups': signups,
        })
    weekly_activity.reverse()
    
    # ============ USER DEMOGRAPHICS BY COUNTRY ============
    country_distribution = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).exclude(
        Q(country_code__isnull=True) | Q(country_code='')
    ).values('country_code').annotate(
        count=Count('id')
    ).order_by('-count')[:10]  # Top 10 countries
    
    # Phone code to country name mapping
    PHONE_CODE_TO_COUNTRY = {
        '+91': 'India', '+1': 'USA/Canada', '+44': 'United Kingdom', '+61': 'Australia',
        '+86': 'China', '+81': 'Japan', '+82': 'South Korea', '+49': 'Germany',
        '+33': 'France', '+39': 'Italy', '+34': 'Spain', '+7': 'Russia/Kazakhstan',
        '+52': 'Mexico', '+55': 'Brazil', '+62': 'Indonesia', '+63': 'Philippines',
        '+60': 'Malaysia', '+65': 'Singapore', '+66': 'Thailand', '+84': 'Vietnam',
        '+92': 'Pakistan', '+880': 'Bangladesh', '+94': 'Sri Lanka', '+977': 'Nepal',
        '+971': 'UAE', '+966': 'Saudi Arabia', '+27': 'South Africa', '+234': 'Nigeria',
        '+254': 'Kenya', '+20': 'Egypt', '+30': 'Greece', '+31': 'Netherlands',
        '+41': 'Switzerland', '+46': 'Sweden', '+47': 'Norway', '+48': 'Poland',
        '+351': 'Portugal', '+353': 'Ireland', '+358': 'Finland', '+380': 'Ukraine',
        '+420': 'Czech Republic', '+43': 'Austria', '+45': 'Denmark', '+90': 'Turkey',
    }
    
    # Format country data for chart
    country_data = []
    for item in country_distribution:
        phone_code = item['country_code']
        country_name = PHONE_CODE_TO_COUNTRY.get(phone_code, phone_code)
        country_data.append({
            'country': country_name,
            'count': item['count']
        })
    
    # Add "Not Specified" if there are users without country_code
    users_without_country = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).filter(
        Q(country_code__isnull=True) | Q(country_code='')
    ).count()
    
    if users_without_country > 0:
        country_data.append({
            'country': 'Not Specified',
            'count': users_without_country
        })
    
    # ============ USER SOURCE TRACKING ============
    source_distribution = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).values('referral_source').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Format source data for chart
    source_data = []
    source_labels = {
        'referral': 'Referral from colleague',
        'facebook': 'Facebook',
        'youtube': 'YouTube',
        'linkedin': 'LinkedIn',
        'google': 'Google Search',
        'other': 'Other',
        '': 'Not Specified',
        None: 'Not Specified'
    }
    
    for item in source_distribution:
        source_value = item['referral_source'] if item['referral_source'] else ''
        source_name = source_labels.get(source_value, 'Not Specified')
        
        # Avoid duplicate "Not Specified" entries
        existing = next((x for x in source_data if x['source'] == source_name), None)
        if existing:
            existing['count'] += item['count']
        else:
            source_data.append({
                'source': source_name,
                'count': item['count']
            })
    
    # ============ USER ACTIVITY ANALYTICS ============
    # Calculate date range based on period
    period_duration = (end_date.date() - start_date.date()).days
    previous_period_end = start_date
    previous_period_start = previous_period_end - timedelta(days=period_duration)
    
    # Active Users (users who performed any activity)
    current_active_users = User.objects.filter(
        Q(demo_views__viewed_at__range=[start_date, end_date]) |
        Q(demo_requests__created_at__range=[start_date, end_date]) |
        Q(enquiries__created_at__range=[start_date, end_date]),
        is_staff=False,
        is_superuser=False
    ).distinct().count()
    
    previous_active_users = User.objects.filter(
        Q(demo_views__viewed_at__range=[previous_period_start, previous_period_end]) |
        Q(demo_requests__created_at__range=[previous_period_start, previous_period_end]) |
        Q(enquiries__created_at__range=[previous_period_start, previous_period_end]),
        is_staff=False,
        is_superuser=False
    ).distinct().count()
    
    active_users_change = ((current_active_users - previous_active_users) / max(previous_active_users, 1)) * 100 if previous_active_users > 0 else 0
    
    # Total Views
    current_views = DemoView.objects.filter(viewed_at__range=[start_date, end_date]).count()
    previous_views = DemoView.objects.filter(viewed_at__range=[previous_period_start, previous_period_end]).count()
    views_change = ((current_views - previous_views) / max(previous_views, 1)) * 100 if previous_views > 0 else 0
    
    # Demo Requests
    current_requests = DemoRequest.objects.filter(created_at__range=[start_date, end_date]).count()
    previous_requests = DemoRequest.objects.filter(created_at__range=[previous_period_start, previous_period_end]).count()
    requests_change = ((current_requests - previous_requests) / max(previous_requests, 1)) * 100 if previous_requests > 0 else 0
    
    # Enquiries
    current_enquiries = BusinessEnquiry.objects.filter(created_at__range=[start_date, end_date]).count()
    previous_enquiries = BusinessEnquiry.objects.filter(created_at__range=[previous_period_start, previous_period_end]).count()
    enquiries_change = ((current_enquiries - previous_enquiries) / max(previous_enquiries, 1)) * 100 if previous_enquiries > 0 else 0
    
    activity_stats = {
        'active_users': current_active_users,
        'active_users_change': round(active_users_change, 1),
        'total_views': current_views,
        'views_change': round(views_change, 1),
        'demo_requests': current_requests,
        'requests_change': round(requests_change, 1),
        'enquiries': current_enquiries,
        'enquiries_change': round(enquiries_change, 1),
    }
    
    # User Activity Timeline Data
    user_activity_data = []
    current_date = start_date.date()
    while current_date <= end_date.date():
        date_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
        date_end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
        
        views = DemoView.objects.filter(viewed_at__range=[date_start, date_end]).count()
        requests = DemoRequest.objects.filter(created_at__range=[date_start, date_end]).count()
        enquiries_count = BusinessEnquiry.objects.filter(created_at__range=[date_start, date_end]).count()
        logins = User.objects.filter(
            last_login__range=[date_start, date_end],
            is_staff=False,
            is_superuser=False
        ).count()
        
        user_activity_data.append({
            'date': current_date.strftime(date_format),
            'views': views,
            'requests': requests,
            'enquiries': enquiries_count,
            'logins': logins,
        })
        
        current_date += timedelta(days=1)
    
    # Peak Activity Hours (last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    
    # Get activity by hour
    demo_view_hours = DemoView.objects.filter(
        viewed_at__gte=last_30_days
    ).annotate(hour=ExtractHour('viewed_at')).values('hour').annotate(count=Count('id'))
    
    demo_request_hours = DemoRequest.objects.filter(
        created_at__gte=last_30_days
    ).annotate(hour=ExtractHour('created_at')).values('hour').annotate(count=Count('id'))
    
    enquiry_hours = BusinessEnquiry.objects.filter(
        created_at__gte=last_30_days
    ).annotate(hour=ExtractHour('created_at')).values('hour').annotate(count=Count('id'))
    
    # Aggregate by hour
    hour_counts = {}
    for item in demo_view_hours:
        hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
    for item in demo_request_hours:
        hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
    for item in enquiry_hours:
        hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
    
    # Sort and format
    total_activities = sum(hour_counts.values())
    sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    peak_hours_data = []
    for hour, count in sorted_hours:
        start_hour = f"{hour:02d}:00"
        end_hour = f"{(hour+1):02d}:00"
        time_slot = f"{start_hour} - {end_hour}"
        percentage = (count / total_activities * 100) if total_activities > 0 else 0
        
        peak_hours_data.append({
            'time_slot': time_slot,
            'count': count,
            'percentage': round(percentage, 1)
        })
    
    # Most Active Users (last 30 days)
    most_active_users_data = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).annotate(
        activity_count=(
            Count('demo_views', filter=Q(demo_views__viewed_at__gte=last_30_days)) + 
            Count('demo_requests', filter=Q(demo_requests__created_at__gte=last_30_days)) + 
            Count('enquiries', filter=Q(enquiries__created_at__gte=last_30_days))
        )
    ).filter(activity_count__gt=0).order_by('-activity_count')[:10]
    
    context = {
        # User Stats
        'total_users': total_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'pending_approvals': pending_approvals,
        'active_users': active_users,
        
        # Demo Stats
        'total_demos': total_demos,
        'active_demos': active_demos,
        'total_demo_views': total_demo_views,
        'demo_views_today': demo_views_today,
        'demo_requests_pending': demo_requests_pending,
        'demo_requests_today': demo_requests_today,
        
        # Enquiry Stats
        'total_enquiries': total_enquiries,
        'open_enquiries': open_enquiries,
        'new_enquiries_today': new_enquiries_today,
        'overdue_enquiries': overdue_enquiries,
        
        # Recent Activity
        'recent_users': recent_users,
        'recent_enquiries': recent_enquiries,
        'recent_demo_requests': recent_demo_requests,
        'recent_contact_messages': [],
        'popular_demos': popular_demos,
        
        # Chart Data
        'monthly_users': monthly_users,
        'weekly_activity': weekly_activity,
        'system_health': system_health,
        
        # Demographics Data
        'country_data': country_data,
        'source_data': source_data,
        
        # Activity Analytics
        'activity_stats': activity_stats,
        'user_activity_data': user_activity_data,
        'peak_hours': peak_hours_data,
        'most_active_users': most_active_users_data,
        'activity_period': activity_period,
    }
    
    return render(request, 'admin/dashboard.html', context)

# =====================================

def contact_view(request):
    """Contact page for general inquiries"""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone', '')
        company = request.POST.get('company', '')
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Save contact message
        contact_message = ContactMessage.objects.create(
            name=name,
            email=email,
            phone=phone,
            company=company,
            subject=subject,
            message=message,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Send email to admin
        try:
            admin_subject = f"New Contact Message: {subject}"
            admin_message = f"""
            New contact message received:
            
            Name: {name}
            Email: {email}
            Phone: {phone}
            Company: {company}
            
            Subject: {subject}
            
            Message:
            {message}
            
            ---
            Sent from Demo Portal
            """
            
            send_mail(
                admin_subject,
                admin_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=False,
            )
        except Exception as e:
            pass  # Continue even if email fails
        
        messages.success(request, 'Thank you for your message! We will get back to you soon.')
        return redirect('core:contact')
    
    site_settings = SiteSettings.load()
    return render(request, 'core/contact.html', {'site_settings': site_settings})

def contact_sales_view(request):
    """Contact sales form for business inquiries"""
    return render(request, 'core/contact_sales.html')

# =====================================
# ADMIN AUTHENTICATION
# =====================================

def admin_login_view(request):
    """Custom admin login page - supports both admin users and employees"""
    
    # If already logged in
    if request.user.is_authenticated:
        # Check if user is admin/staff or employee
        if is_admin(request.user) or (hasattr(request.user, 'user_type') and request.user.user_type == 'employee'):
            return redirect('core:admin_dashboard')
    
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        # ✅ Validate inputs first
        if not email:
            messages.error(request, 'Email address is required.')
            return render(request, 'admin/auth/login.html')
        
        if not password:
            messages.error(request, 'Password is required.')
            return render(request, 'admin/auth/login.html')
        
        # Authenticate user
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            # ✅ Check if user is admin OR employee
            if is_admin(user) or (hasattr(user, 'user_type') and user.user_type == 'employee'):
                
                # ✅ Additional checks for employees
                if hasattr(user, 'user_type') and user.user_type == 'employee':
                    # Check if employee is active
                    if not user.is_active:
                        messages.error(request, '❌ Your account has been deactivated. Please contact administrator.')
                        return render(request, 'admin/auth/login.html')
                    
                    # Optional: Check if email is verified
                    if hasattr(user, 'is_email_verified') and not user.is_email_verified:
                        messages.warning(request, '⚠️ Your email is not verified. Some features may be limited.')
                        # Still allow login but show warning
                    
                    # Optional: Check if account is approved
                    if hasattr(user, 'is_approved') and not user.is_approved:
                        messages.error(request, '❌ Your account is pending approval. Please wait for administrator approval.')
                        return render(request, 'admin/auth/login.html')
                
                # ✅ Login successful
                login(request, user)
                
                # Get user's full name or email
                user_name = user.get_full_name() if hasattr(user, 'get_full_name') and user.get_full_name() else user.email
                
                messages.success(request, f'✅ Welcome back, {user_name}!')
                
                # Redirect to next or dashboard
                next_url = request.GET.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('core:admin_dashboard')
            else:
                # User authenticated but not staff/employee
                messages.error(request, '❌ Access denied. This portal is for staff members and employees only.')
                return render(request, 'admin/auth/login.html')
        else:
            # Authentication failed
            messages.error(request, '❌ Invalid email or password. Please try again.')
            return render(request, 'admin/auth/login.html')
    
    # GET request - show login form
    return render(request, 'admin/auth/login.html')

@login_required
@user_passes_test(is_admin)
def admin_logout_view(request):
    """Admin logout"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('core:admin_login')

# =====================================
# ADMIN DASHBOARD - Fixed with proper context
# =====================================

@login_required
@user_passes_test(is_admin)
def admin_dashboard_view(request):
    """Main admin dashboard with statistics and demographics"""
    
    # Get activity period from request
    activity_period = request.GET.get('period', 'daily')
    
    # Date ranges for statistics
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # User Statistics - FILTER OUT ADMIN/STAFF USERS
    total_users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).count()
    
    new_users_today = User.objects.filter(
        created_at__date=today,
        is_staff=False,
        is_superuser=False
    ).count()
    
    new_users_week = User.objects.filter(
        created_at__date__gte=week_ago,
        is_staff=False,
        is_superuser=False
    ).count()
    
    pending_approvals = User.objects.filter(
        is_approved=False, 
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()
    
    active_users = User.objects.filter(
        is_active=True, 
        is_approved=True,
        is_staff=False,
        is_superuser=False
    ).count()
    
    # Demo Statistics
    total_demos = Demo.objects.count()
    active_demos = Demo.objects.filter(is_active=True).count()
    total_demo_views = DemoView.objects.count()
    demo_views_today = DemoView.objects.filter(viewed_at__date=today).count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    demo_requests_today = DemoRequest.objects.filter(created_at__date=today).count()
    
    # Enquiry Statistics
    total_enquiries = BusinessEnquiry.objects.count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    new_enquiries_today = BusinessEnquiry.objects.filter(created_at__date=today).count()
    overdue_enquiries = BusinessEnquiry.objects.filter(
        status='open',
        created_at__lt=timezone.now() - timedelta(hours=24)
    ).count()
    
    # System Health
    system_health = {
        'database': 'healthy',
        'email': 'healthy',
        'storage': 'healthy',
        'cache': 'healthy',
    }
    
    # Recent Activity - FILTER OUT ADMIN USERS
    recent_users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).order_by('-created_at')[:5]
    
    recent_enquiries = BusinessEnquiry.objects.order_by('-created_at')[:5]
    recent_demo_requests = DemoRequest.objects.select_related('user', 'demo').order_by('-created_at')[:5]
    
    # Popular Demos (most viewed)
    popular_demos = Demo.objects.annotate(
        views_count_calc=Count('demo_views')
    ).order_by('-views_count_calc')[:5]
    
    # ============ DYNAMIC USER REGISTRATION DATA (WITH FILTERS) ============
    end_date = timezone.now()
    
    if activity_period == 'daily':
        start_date = end_date - timedelta(days=7)  # Last 7 days
        date_format = '%m/%d'
    elif activity_period == 'weekly':
        start_date = end_date - timedelta(weeks=12)  # Last 12 weeks
        date_format = 'Week %W'
    elif activity_period == 'monthly':
        start_date = end_date - timedelta(days=365)  # Last 12 months
        date_format = '%b %Y'
    elif activity_period == 'custom':
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        if start_date_str and end_date_str:
            from datetime import datetime
            start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
            end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
        else:
            start_date = end_date - timedelta(days=30)
        date_format = '%m/%d'
    else:
        start_date = end_date - timedelta(days=7)
        date_format = '%m/%d'
    
    # Monthly User Growth Chart Data
    monthly_users = []
    
    if activity_period == 'monthly':
        # Monthly breakdown for last 12 months
        for i in range(12):
            date = today.replace(day=1) - timedelta(days=i*30)
            count = User.objects.filter(
                created_at__year=date.year,
                created_at__month=date.month,
                is_staff=False,
                is_superuser=False
            ).count()
            monthly_users.append({
                'month': date.strftime('%b %Y'),
                'count': count
            })
        monthly_users.reverse()
    elif activity_period == 'weekly':
        # Weekly breakdown for last 12 weeks
        current_date = start_date.date()
        while current_date <= end_date.date():
            week_end = current_date + timedelta(days=6)
            count = User.objects.filter(
                created_at__date__range=[current_date, week_end],
                is_staff=False,
                is_superuser=False
            ).count()
            monthly_users.append({
                'month': f"Week {current_date.strftime('%W')}",
                'count': count
            })
            current_date = week_end + timedelta(days=1)
    else:
        # Daily breakdown
        current_date = start_date.date()
        while current_date <= end_date.date():
            count = User.objects.filter(
                created_at__date=current_date,
                is_staff=False,
                is_superuser=False
            ).count()
            monthly_users.append({
                'month': current_date.strftime(date_format),
                'count': count
            })
            current_date += timedelta(days=1)
    
    # Weekly Activity Data (always last 7 days)
    weekly_activity = []
    for i in range(7):  # Last 7 days
        date = today - timedelta(days=i)
        demo_views = DemoView.objects.filter(viewed_at__date=date).count()
        enquiries = BusinessEnquiry.objects.filter(created_at__date=date).count()
        signups = User.objects.filter(
            created_at__date=date,
            is_staff=False,
            is_superuser=False
        ).count()
        
        weekly_activity.append({
            'date': date.strftime('%m/%d'),
            'demo_views': demo_views,
            'enquiries': enquiries,
            'signups': signups,
        })
    weekly_activity.reverse()
    
    # ============ USER DEMOGRAPHICS BY COUNTRY ============
    country_distribution = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).exclude(
        Q(country_code__isnull=True) | Q(country_code='')
    ).values('country_code').annotate(
        count=Count('id')
    ).order_by('-count')[:10]  # Top 10 countries
    
    # Phone code to country name mapping
    PHONE_CODE_TO_COUNTRY = {
        '+91': 'India', '+1': 'USA/Canada', '+44': 'United Kingdom', '+61': 'Australia',
        '+86': 'China', '+81': 'Japan', '+82': 'South Korea', '+49': 'Germany',
        '+33': 'France', '+39': 'Italy', '+34': 'Spain', '+7': 'Russia/Kazakhstan',
        '+52': 'Mexico', '+55': 'Brazil', '+62': 'Indonesia', '+63': 'Philippines',
        '+60': 'Malaysia', '+65': 'Singapore', '+66': 'Thailand', '+84': 'Vietnam',
        '+92': 'Pakistan', '+880': 'Bangladesh', '+94': 'Sri Lanka', '+977': 'Nepal',
        '+971': 'UAE', '+966': 'Saudi Arabia', '+27': 'South Africa', '+234': 'Nigeria',
        '+254': 'Kenya', '+20': 'Egypt', '+30': 'Greece', '+31': 'Netherlands',
        '+41': 'Switzerland', '+46': 'Sweden', '+47': 'Norway', '+48': 'Poland',
        '+351': 'Portugal', '+353': 'Ireland', '+358': 'Finland', '+380': 'Ukraine',
        '+420': 'Czech Republic', '+43': 'Austria', '+45': 'Denmark', '+90': 'Turkey',
    }
    
    # Format country data for chart
    country_data = []
    for item in country_distribution:
        phone_code = item['country_code']
        country_name = PHONE_CODE_TO_COUNTRY.get(phone_code, phone_code)
        country_data.append({
            'country': country_name,
            'count': item['count']
        })
    
    # Add "Not Specified" if there are users without country_code
    users_without_country = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).filter(
        Q(country_code__isnull=True) | Q(country_code='')
    ).count()
    
    if users_without_country > 0:
        country_data.append({
            'country': 'Not Specified',
            'count': users_without_country
        })
    
    # ============ USER SOURCE TRACKING ============
    source_distribution = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).values('referral_source').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Format source data for chart
    source_data = []
    source_labels = {
        'referral': 'Referral from colleague',
        'facebook': 'Facebook',
        'youtube': 'YouTube',
        'linkedin': 'LinkedIn',
        'google': 'Google Search',
        'other': 'Other',
        '': 'Not Specified',
        None: 'Not Specified'
    }
    
    for item in source_distribution:
        source_value = item['referral_source'] if item['referral_source'] else ''
        source_name = source_labels.get(source_value, 'Not Specified')
        
        # Avoid duplicate "Not Specified" entries
        existing = next((x for x in source_data if x['source'] == source_name), None)
        if existing:
            existing['count'] += item['count']
        else:
            source_data.append({
                'source': source_name,
                'count': item['count']
            })
    
    # ============ USER ACTIVITY ANALYTICS ============
    # Calculate date range based on period
    period_duration = (end_date.date() - start_date.date()).days
    previous_period_end = start_date
    previous_period_start = previous_period_end - timedelta(days=period_duration)
    
    # Active Users (users who performed any activity)
    current_active_users = User.objects.filter(
        Q(demo_views__viewed_at__range=[start_date, end_date]) |
        Q(demo_requests__created_at__range=[start_date, end_date]) |
        Q(enquiries__created_at__range=[start_date, end_date]),
        is_staff=False,
        is_superuser=False
    ).distinct().count()
    
    previous_active_users = User.objects.filter(
        Q(demo_views__viewed_at__range=[previous_period_start, previous_period_end]) |
        Q(demo_requests__created_at__range=[previous_period_start, previous_period_end]) |
        Q(enquiries__created_at__range=[previous_period_start, previous_period_end]),
        is_staff=False,
        is_superuser=False
    ).distinct().count()
    
    active_users_change = ((current_active_users - previous_active_users) / max(previous_active_users, 1)) * 100 if previous_active_users > 0 else 0
    
    # Total Views
    current_views = DemoView.objects.filter(viewed_at__range=[start_date, end_date]).count()
    previous_views = DemoView.objects.filter(viewed_at__range=[previous_period_start, previous_period_end]).count()
    views_change = ((current_views - previous_views) / max(previous_views, 1)) * 100 if previous_views > 0 else 0
    
    # Demo Requests
    current_requests = DemoRequest.objects.filter(created_at__range=[start_date, end_date]).count()
    previous_requests = DemoRequest.objects.filter(created_at__range=[previous_period_start, previous_period_end]).count()
    requests_change = ((current_requests - previous_requests) / max(previous_requests, 1)) * 100 if previous_requests > 0 else 0
    
    # Enquiries
    current_enquiries = BusinessEnquiry.objects.filter(created_at__range=[start_date, end_date]).count()
    previous_enquiries = BusinessEnquiry.objects.filter(created_at__range=[previous_period_start, previous_period_end]).count()
    enquiries_change = ((current_enquiries - previous_enquiries) / max(previous_enquiries, 1)) * 100 if previous_enquiries > 0 else 0
    
    activity_stats = {
        'active_users': current_active_users,
        'active_users_change': round(active_users_change, 1),
        'total_views': current_views,
        'views_change': round(views_change, 1),
        'demo_requests': current_requests,
        'requests_change': round(requests_change, 1),
        'enquiries': current_enquiries,
        'enquiries_change': round(enquiries_change, 1),
    }
    
    # User Activity Timeline Data
    user_activity_data = []
    current_date = start_date.date()
    while current_date <= end_date.date():
        date_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
        date_end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
        
        views = DemoView.objects.filter(viewed_at__range=[date_start, date_end]).count()
        requests = DemoRequest.objects.filter(created_at__range=[date_start, date_end]).count()
        enquiries_count = BusinessEnquiry.objects.filter(created_at__range=[date_start, date_end]).count()
        logins = User.objects.filter(
            last_login__range=[date_start, date_end],
            is_staff=False,
            is_superuser=False
        ).count()
        
        user_activity_data.append({
            'date': current_date.strftime(date_format),
            'views': views,
            'requests': requests,
            'enquiries': enquiries_count,
            'logins': logins,
        })
        
        current_date += timedelta(days=1)
    
    # Peak Activity Hours (last 30 days)
    last_30_days = timezone.now() - timedelta(days=30)
    
    # Get activity by hour
    demo_view_hours = DemoView.objects.filter(
        viewed_at__gte=last_30_days
    ).annotate(hour=ExtractHour('viewed_at')).values('hour').annotate(count=Count('id'))
    
    demo_request_hours = DemoRequest.objects.filter(
        created_at__gte=last_30_days
    ).annotate(hour=ExtractHour('created_at')).values('hour').annotate(count=Count('id'))
    
    enquiry_hours = BusinessEnquiry.objects.filter(
        created_at__gte=last_30_days
    ).annotate(hour=ExtractHour('created_at')).values('hour').annotate(count=Count('id'))
    
    # Aggregate by hour
    hour_counts = {}
    for item in demo_view_hours:
        hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
    for item in demo_request_hours:
        hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
    for item in enquiry_hours:
        hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
    
    # Sort and format
    total_activities = sum(hour_counts.values())
    sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    peak_hours_data = []
    for hour, count in sorted_hours:
        start_hour = f"{hour:02d}:00"
        end_hour = f"{(hour+1):02d}:00"
        time_slot = f"{start_hour} - {end_hour}"
        percentage = (count / total_activities * 100) if total_activities > 0 else 0
        
        peak_hours_data.append({
            'time_slot': time_slot,
            'count': count,
            'percentage': round(percentage, 1)
        })
    
    # Most Active Users (last 30 days)
    most_active_users_data = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).annotate(
        activity_count=(
            Count('demo_views', filter=Q(demo_views__viewed_at__gte=last_30_days)) + 
            Count('demo_requests', filter=Q(demo_requests__created_at__gte=last_30_days)) + 
            Count('enquiries', filter=Q(enquiries__created_at__gte=last_30_days))
        )
    ).filter(activity_count__gt=0).order_by('-activity_count')[:10]
    
    context = {
        # User Stats
        'total_users': total_users,
        'new_users_today': new_users_today,
        'new_users_week': new_users_week,
        'pending_approvals': pending_approvals,
        'active_users': active_users,
        
        # Demo Stats
        'total_demos': total_demos,
        'active_demos': active_demos,
        'total_demo_views': total_demo_views,
        'demo_views_today': demo_views_today,
        'demo_requests_pending': demo_requests_pending,
        'demo_requests_today': demo_requests_today,
        
        # Enquiry Stats
        'total_enquiries': total_enquiries,
        'open_enquiries': open_enquiries,
        'new_enquiries_today': new_enquiries_today,
        'overdue_enquiries': overdue_enquiries,
        
        # Recent Activity
        'recent_users': recent_users,
        'recent_enquiries': recent_enquiries,
        'recent_demo_requests': recent_demo_requests,
        'recent_contact_messages': [],
        'popular_demos': popular_demos,
        
        # Chart Data
        'monthly_users': monthly_users,
        'weekly_activity': weekly_activity,
        'system_health': system_health,
        
        # Demographics Data
        'country_data': country_data,
        'source_data': source_data,
        
        # Activity Analytics
        'activity_stats': activity_stats,
        'user_activity_data': user_activity_data,
        'peak_hours': peak_hours_data,
        'most_active_users': most_active_users_data,
        'activity_period': activity_period,
    }
    
    return render(request, 'admin/dashboard.html', context)

# =====================================
# ADMIN USER MANAGEMENT
# =====================================
@login_required
@user_passes_test(is_admin)
def admin_users_view(request):
    """Admin users management - FIXED to show only customers"""
    # FILTER OUT ADMIN/STAFF USERS - Only show customers
    users_list = User.objects.filter(
        is_staff=False,  # Exclude staff users
        is_superuser=False  # Exclude superusers
    ).order_by('-created_at')
    
    # Filtering
    status_filter = request.GET.get('status')
    search = request.GET.get('search')
    
    if status_filter == 'pending':
        users_list = users_list.filter(is_approved=False)
    elif status_filter == 'approved':
        users_list = users_list.filter(is_approved=True)
    elif status_filter == 'blocked':
        users_list = users_list.filter(is_active=False)
    elif status_filter == 'active':
        users_list = users_list.filter(is_active=True, is_approved=True)
    
    if search:
        users_list = users_list.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(organization__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users_list, 25)
    page_number = request.GET.get('page')
    users = paginator.get_page(page_number)
    
    # Context for sidebar badges - ALSO FILTER ADMIN USERS FROM COUNTS
    pending_approvals = User.objects.filter(
        is_approved=False, 
        is_active=True,
        is_staff=False,  # Only count customers
        is_superuser=False
    ).count()
    
    total_customers = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).count()
    
    active_customers = User.objects.filter(
        is_staff=False,
        is_superuser=False,
        is_active=True,
        is_approved=True
    ).count()
    
    blocked_customers = User.objects.filter(
        is_staff=False,
        is_superuser=False,
        is_active=False
    ).count()
    
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    context = {
        'users': users,
        'status_filter': status_filter,
        'search': search,
        'pending_approvals': pending_approvals,
        'open_enquiries': open_enquiries,
        'demo_requests_pending': demo_requests_pending,
        # Additional statistics for display
        'total_customers': total_customers,
        'active_customers': active_customers,
        'blocked_customers': blocked_customers,
    }
    
    return render(request, 'admin/users/list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_user_detail_view(request, user_id):
    """Admin user detail view"""
    user_detail = get_object_or_404(User, id=user_id)
    
    # User activity stats
    demo_views = DemoView.objects.filter(user=user_detail).count()
    demo_requests = DemoRequest.objects.filter(user=user_detail).count()
    enquiries = BusinessEnquiry.objects.filter(user=user_detail).count()
    
    # Recent activity
    recent_demo_views = DemoView.objects.filter(user=user_detail).select_related('demo').order_by('-viewed_at')[:10]
    recent_demo_requests = DemoRequest.objects.filter(user=user_detail).select_related('demo').order_by('-created_at')[:10]
    recent_enquiries = BusinessEnquiry.objects.filter(user=user_detail).order_by('-created_at')[:10]
    
    # Context for sidebar badges
    pending_approvals = User.objects.filter(is_approved=False, is_active=True).count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    context = {
        'user_detail': user_detail,
        'demo_views': demo_views,
        'demo_requests': demo_requests,
        'enquiries': enquiries,
        'recent_demo_views': recent_demo_views,
        'recent_demo_requests': recent_demo_requests,
        'recent_enquiries': recent_enquiries,
        'pending_approvals': pending_approvals,
        'open_enquiries': open_enquiries,
        'demo_requests_pending': demo_requests_pending,
    }
    
    return render(request, 'admin/users/detail.html', context)


# =====================================
# ADMIN DEMO MANAGEMENT
# =====================================

@login_required
@permission_required('view_demos')
def admin_demos_view(request):
    """Admin demos management - LIST VIEW with proper sorting & pagination"""
    
    # Get all demos - SORTED BY LATEST FIRST (created_at DESC)
    demos_list = Demo.objects.prefetch_related(
        'target_business_categories',
        'target_business_subcategories',
        'target_customers'
    ).select_related(
        'created_by'
    ).order_by('-created_at')  # ✅ LATEST FIRST - Most recent on top
    
    # Filtering
    search = request.GET.get('search', '')
    file_type_filter = request.GET.get('file_type', '')
    demo_type_filter = request.GET.get('demo_type', '')
    business_category_filter = request.GET.get('business_category', '')
    status_filter = request.GET.get('status', '')
    featured_filter = request.GET.get('featured', '')
    
    # Apply filters
    if search:
        demos_list = demos_list.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )
    
    if file_type_filter:
        demos_list = demos_list.filter(file_type=file_type_filter)
    
    if demo_type_filter:
        demos_list = demos_list.filter(demo_type=demo_type_filter)
    
    if business_category_filter:
        demos_list = demos_list.filter(
            Q(target_business_categories__id=business_category_filter) |
            Q(target_business_subcategories__category__id=business_category_filter)
        ).distinct()
    
    if status_filter:
        if status_filter == 'active':
            demos_list = demos_list.filter(is_active=True)
        elif status_filter == 'inactive':
            demos_list = demos_list.filter(is_active=False)
    
    if featured_filter == 'yes':
        demos_list = demos_list.filter(is_featured=True)
    
    # ✅ PAGINATION - 10 ITEMS PER PAGE
    paginator = Paginator(demos_list, 10)  # Show 10 demos per page
    page_number = request.GET.get('page', 1)
    demos = paginator.get_page(page_number)
    
    # Get business categories for filter dropdown
    business_categories = BusinessCategory.objects.filter(is_active=True).order_by('name')
    
    # Statistics (optional)
    stats = {
        'total': Demo.objects.count(),
        'active': Demo.objects.filter(is_active=True).count(),
        'inactive': Demo.objects.filter(is_active=False).count(),
        'featured': Demo.objects.filter(is_featured=True).count(),
        'total_views': Demo.objects.aggregate(total=Sum('views_count'))['total'] or 0,
        'video_count': Demo.objects.filter(file_type='video').count(),
        'webgl_count': Demo.objects.filter(file_type='webgl').count(),
    }
    
    # Sidebar context
    pending_approvals = User.objects.filter(
        is_approved=False, 
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()
    
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    context = {
        'demos': demos,
        'business_categories': business_categories,
        'demo_types': Demo.DEMO_TYPE_CHOICES if hasattr(Demo, 'DEMO_TYPE_CHOICES') else [],
        'file_types': Demo.FILE_TYPE_CHOICES if hasattr(Demo, 'FILE_TYPE_CHOICES') else [],
        'stats': stats,
        'search': search,
        'file_type_filter': file_type_filter,
        'demo_type_filter': demo_type_filter,
        'business_category_filter': business_category_filter,
        'status_filter': status_filter,
        'featured_filter': featured_filter,
        'pending_approvals': pending_approvals,
        'open_enquiries': open_enquiries,
        'demo_requests_pending': demo_requests_pending,
    }
    
    return render(request, 'admin/demos/list.html', context)


# core/views.py - UPDATE admin_add_demo_view

@login_required
def admin_add_demo_view(request):
    """Admin view to add new demo - 3 file types: video, webgl, lms"""
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title')
            description = request.POST.get('description')
            file_type = request.POST.get('file_type')
            is_featured = request.POST.get('is_featured') == 'on'
            is_active = request.POST.get('is_active') == 'on'
            
            # Validate required fields
            if not title or not description or not file_type:
                messages.error(request, 'Title, description, and file type are required.')
                return redirect('core:admin_add_demo')
            
            # Validate file type
            if file_type not in ['video', 'webgl', 'lms']:
                messages.error(request, 'Invalid file type selected.')
                return redirect('core:admin_add_demo')
            
            # Get the appropriate file
            file_field_mapping = {
                'video': 'video_file',
                'webgl': 'webgl_file',
                'lms': 'lms_file'
            }
            
            file_field_name = file_field_mapping.get(file_type)
            demo_file = request.FILES.get(file_field_name)
            
            if not demo_file:
                messages.error(request, f'Please upload the required {file_type} file.')
                return redirect('core:admin_add_demo')
            
            # Thumbnail is optional
            thumbnail = request.FILES.get('thumbnail')
            
            # Create demo instance
            demo = Demo(
                title=title,
                description=description,
                file_type=file_type,
                demo_type='product',  # Default value
                sort_order=0,  # Default value
                is_featured=is_featured,
                is_active=is_active,
                created_by=request.user
            )
            
            # Assign file based on type
            if file_type == 'video':
                demo.video_file = demo_file
            elif file_type == 'webgl':
                demo.webgl_file = demo_file
            elif file_type == 'lms':
                demo.lms_file = demo_file
            
            # Assign thumbnail if provided
            if thumbnail:
                demo.thumbnail = thumbnail
            
            # Calculate file size
            demo.file_size = demo_file.size
            
            # ✅ Save with skip_extraction for large files
            if demo_file.size > 10 * 1024 * 1024:  # > 10MB
                print(f"⏳ Large file detected ({demo_file.size} bytes), skipping extraction during upload")
                demo.save(skip_extraction=True)
                messages.warning(request, f'Demo "{title}" uploaded successfully! Large file extraction will happen in background.')
            else:
                demo.save()
                messages.success(request, f'Demo "{title}" created successfully!')
            
            # Handle business categories
            all_business_categories = request.POST.get('allBusinessCategoriesCheckbox')
            if not all_business_categories:
                selected_categories = request.POST.getlist('target_business_categories')
                if selected_categories:
                    demo.target_business_categories.set(selected_categories)
                
                selected_subcategories = request.POST.getlist('target_business_subcategories')
                if selected_subcategories:
                    demo.target_business_subcategories.set(selected_subcategories)
            
            # Handle customers
            all_customers = request.POST.get('allCustomersCheckbox')
            if not all_customers:
                selected_customers = request.POST.getlist('target_customers')
                if selected_customers:
                    demo.target_customers.set(selected_customers)
            
            return redirect('core:admin_demos')
            
        except Exception as e:
            messages.error(request, f'Error creating demo: {str(e)}')
            print(f"Error in admin_add_demo_view: {e}")
            import traceback
            traceback.print_exc()
            return redirect('core:admin_add_demo')
    
    # GET request
    business_categories = BusinessCategory.objects.prefetch_related('subcategories').all()
    customers = CustomUser.objects.filter(
        user_type='customer',
        is_active=True
    ).order_by('first_name', 'last_name')
    
    context = {
        'business_categories': business_categories,
        'customers': customers,
    }
    
    return render(request, 'admin/demos/add.html', context)


@login_required
def admin_edit_demo_view(request, demo_id):
    """
    Admin view to edit existing demo - 3 file types
    """
    demo = get_object_or_404(Demo, id=demo_id)
    
    if request.method == 'POST':
        try:
            # Update basic fields
            demo.title = request.POST.get('title')
            demo.description = request.POST.get('description')
            demo.file_type = request.POST.get('file_type')
            demo.is_featured = request.POST.get('is_featured') == 'on'
            demo.is_active = request.POST.get('is_active') == 'on'
            
            # Validate file type
            if demo.file_type not in ['video', 'webgl', 'lms']:
                messages.error(request, 'Invalid file type selected.')
                return redirect('core:admin_edit_demo', demo_id=demo_id)
            
            # Handle file updates
            file_field_mapping = {
                'video': 'video_file',
                'webgl': 'webgl_file',
                'lms': 'lms_file'
            }
            
            file_field_name = file_field_mapping.get(demo.file_type)
            new_demo_file = request.FILES.get(file_field_name)
            
            if new_demo_file:
                # Delete old file
                if demo.file_type == 'video' and demo.video_file:
                    demo.video_file.delete(save=False)
                    demo.video_file = new_demo_file
                elif demo.file_type == 'webgl' and demo.webgl_file:
                    demo.webgl_file.delete(save=False)
                    demo.webgl_file = new_demo_file
                elif demo.file_type == 'lms' and demo.lms_file:
                    demo.lms_file.delete(save=False)
                    demo.lms_file = new_demo_file
                
                # Update file size
                demo.file_size = new_demo_file.size
            
            # Handle thumbnail update
            new_thumbnail = request.FILES.get('thumbnail')
            if new_thumbnail:
                if demo.thumbnail:
                    demo.thumbnail.delete(save=False)
                demo.thumbnail = new_thumbnail
            
            # Save demo
            demo.save()
            
            # Update business categories
            all_business_categories = request.POST.get('allBusinessCategoriesCheckbox')
            if all_business_categories:
                demo.target_business_categories.clear()
                demo.target_business_subcategories.clear()
            else:
                selected_categories = request.POST.getlist('target_business_categories')
                demo.target_business_categories.set(selected_categories)
                
                selected_subcategories = request.POST.getlist('target_business_subcategories')
                demo.target_business_subcategories.set(selected_subcategories)
            
            # Update customers
            all_customers = request.POST.get('allCustomersCheckbox')
            if all_customers:
                demo.target_customers.clear()
            else:
                selected_customers = request.POST.getlist('target_customers')
                demo.target_customers.set(selected_customers)
            
            messages.success(request, f'Demo "{demo.title}" updated successfully!')
            return redirect('core:admin_demos')
            
        except Exception as e:
            messages.error(request, f'Error updating demo: {str(e)}')
            print(f"Error in admin_edit_demo_view: {e}")
            import traceback
            traceback.print_exc()
            return redirect('core:admin_edit_demo', demo_id=demo_id)
    
    # GET request
    business_categories = BusinessCategory.objects.prefetch_related('subcategories').all()
    customers = CustomUser.objects.filter(
        user_type='customer',
        is_active=True
    ).order_by('first_name', 'last_name')
    
    context = {
        'demo': demo,
        'business_categories': business_categories,
        'customers': customers,
        'form_data': {
            'title': demo.title,
            'description': demo.description,
            'file_type': demo.file_type,
            'is_featured': demo.is_featured,
            'is_active': demo.is_active,
            'all_business_categories': demo.is_for_all_business_categories,
            'selected_business_categories': list(demo.target_business_categories.values_list('id', flat=True)),
            'selected_business_subcategories': list(demo.target_business_subcategories.values_list('id', flat=True)),
            'selected_customers': list(demo.target_customers.values_list('id', flat=True)),
        }
    }
    
    return render(request, 'admin/demos/edit.html', context)

@login_required
def admin_demo_detail_view(request, demo_id):
    """
    View and edit demo details - Working version with all imports
    Features:
    - Two tabs: Edit | Details & Stats
    - Upload progress tracking
    - AJAX support for file uploads
    - Form data preservation
    """
    
    demo = get_object_or_404(Demo, id=demo_id)
    
    # Get all business categories with subcategories
    business_categories = BusinessCategory.objects.prefetch_related('subcategories').all()
    
    # Get all approved customers
    customers = CustomUser.objects.filter(
        is_approved=True
    ).order_by('first_name', 'last_name')
    
    # Calculate statistics
    total_views = demo.views.count() if hasattr(demo, 'views') else 0
    total_likes = demo.likes.count() if hasattr(demo, 'likes') else 0
    total_requests = demo.demo_requests.count() if hasattr(demo, 'demo_requests') else 0
    
    # Calculate accessible customers
    if demo.target_customers.exists():
        total_accessible_customers = demo.target_customers.count()
    elif demo.target_business_categories.exists() or demo.target_business_subcategories.exists():
        query = Q()
        if demo.target_business_categories.exists():
            query |= Q(business_category__in=demo.target_business_categories.all())
        if demo.target_business_subcategories.exists():
            query |= Q(business_subcategory__in=demo.target_business_subcategories.all())
        total_accessible_customers = CustomUser.objects.filter(
            is_approved=True
        ).filter(query).distinct().count()
    else:
        total_accessible_customers = CustomUser.objects.filter(
            is_approved=True
        ).count()
    
    # Get recent activity
    recent_views = []
    recent_requests = []
    
    if hasattr(demo, 'views'):
        recent_views = demo.views.select_related('user').order_by('-viewed_at')[:5]
    
    if hasattr(demo, 'demo_requests'):
        recent_requests = demo.demo_requests.select_related('user').order_by('-created_at')[:5]
    
    # Initialize form data
    form_data = {
        'title': demo.title,
        'description': demo.description,
        'demo_type': demo.demo_type if hasattr(demo, 'demo_type') else 'product',
        'file_type': demo.file_type,
        'duration': demo.duration or '',
        'is_featured': demo.is_featured,
        'is_active': demo.is_active,
        'all_business_categories': not demo.target_business_categories.exists(),
        'sort_order': demo.sort_order if hasattr(demo, 'sort_order') else 0,
        'selected_business_categories': [str(cat.id) for cat in demo.target_business_categories.all()],
        'selected_business_subcategories': [str(sub.id) for sub in demo.target_business_subcategories.all()],
        'selected_customers': [str(cust.id) for cust in demo.target_customers.all()],
    }
    
    # Handle POST request (Edit form submission)
    if request.method == 'POST':
        try:
            # Get form data
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            is_featured = request.POST.get('is_featured') == 'on'
            is_active = request.POST.get('is_active') == 'on'
            
            # Get file uploads (optional for edit)
            thumbnail = request.FILES.get('thumbnail')
            video_file = request.FILES.get('video_file')
            webgl_file = request.FILES.get('webgl_file')
            lms_file = request.FILES.get('lms_file')
            
            # Get targeting data
            all_business_categories_checked = request.POST.get('allBusinessCategoriesCheckbox') == 'on'
            target_business_categories = request.POST.getlist('target_business_categories')
            target_business_subcategories = request.POST.getlist('target_business_subcategories')
            target_customers = request.POST.getlist('target_customers')
            
            # Preserve form data before validation
            form_data.update({
                'title': title,
                'description': description,
                'is_featured': is_featured,
                'is_active': is_active,
                'all_business_categories': all_business_categories_checked,
                'selected_business_categories': target_business_categories,
                'selected_business_subcategories': target_business_subcategories,
                'selected_customers': target_customers,
            })
            
            # Validation
            if not title:
                messages.error(request, 'Title is required.')
                raise ValueError('Title required')
            
            if not description:
                messages.error(request, 'Description is required.')
                raise ValueError('Description required')
            
            # Update demo object
            demo.title = title
            demo.description = description
            demo.is_featured = is_featured
            demo.is_active = is_active
            
            # Update files if provided
            if thumbnail:
                # Delete old thumbnail
                if demo.thumbnail:
                    demo.thumbnail.delete(save=False)
                demo.thumbnail = thumbnail
            
            # Update main file based on file type
            if video_file and demo.file_type == 'video':
                if demo.video_file:
                    demo.video_file.delete(save=False)
                demo.video_file = video_file
                demo.file_size = video_file.size
            
            if webgl_file and demo.file_type == 'webgl':
                if demo.webgl_file:
                    demo.webgl_file.delete(save=False)
                demo.webgl_file = webgl_file
                demo.file_size = webgl_file.size
            
            if lms_file and demo.file_type == 'lms':
                if demo.lms_file:
                    demo.lms_file.delete(save=False)
                demo.lms_file = lms_file
                demo.file_size = lms_file.size
            
            # Check if large file - skip extraction
            has_large_file = False
            if video_file and video_file.size > 10 * 1024 * 1024:
                has_large_file = True
            elif webgl_file and webgl_file.size > 10 * 1024 * 1024:
                has_large_file = True
            elif lms_file and lms_file.size > 10 * 1024 * 1024:
                has_large_file = True
            
            # Save demo
            if has_large_file:
                demo.save(skip_extraction=True)
            else:
                demo.save()
            
            # Update target business categories
            if all_business_categories_checked:
                demo.target_business_categories.clear()
                demo.target_business_subcategories.clear()
            else:
                demo.target_business_categories.set(target_business_categories)
                demo.target_business_subcategories.set(target_business_subcategories)
            
            # Update target customers
            if target_customers:
                demo.target_customers.set(target_customers)
            else:
                demo.target_customers.clear()
            
            success_message = f'Demo "{title}" updated successfully!'
            messages.success(request, success_message)
            
            # Return JSON response for AJAX
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': success_message,
                    'redirect_url': reverse('core:admin_demos')
                })
            
            # Regular redirect for non-AJAX
            return redirect('core:admin_demos')
            
        except ValueError:
            # Validation errors already added to messages
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Validation failed. Please check the form.'
                }, status=400)
        except Exception as e:
            error_msg = f'Error updating demo: {str(e)}'
            messages.error(request, error_msg)
            print(f"Error in admin_demo_detail_view: {e}")
            import traceback
            traceback.print_exc()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': error_msg
                }, status=500)
    
    context = {
        'demo': demo,
        'business_categories': business_categories,
        'customers': customers,
        'form_data': form_data,
        
        # Statistics
        'total_views': total_views,
        'total_likes': total_likes,
        'total_requests': total_requests,
        'total_accessible_customers': total_accessible_customers,
        
        # Recent activity
        'recent_views': recent_views,
        'recent_requests': recent_requests,
    }
    
    return render(request, 'admin/demos/detail.html', context)


@login_required
@permission_required('view_demos')
def admin_demo_watch_view(request, demo_id):
    """Admin watch/preview demo"""
    demo = get_object_or_404(Demo, id=demo_id)
    
    # Auto-redirect WebGL to WebGL viewer
    if demo.file_type == 'webgl':
        return redirect('core:admin_webgl_preview', demo_id=demo.id)
    
    # Context for sidebar
    pending_approvals = User.objects.filter(
        is_approved=False,
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    # ✅ FIX: Get business categories and subcategories
    business_categories = demo.target_business_categories.all()
    business_subcategories = demo.target_business_subcategories.all()
    
    context = {
        'demo': demo,
        'is_admin_preview': True,
        'pending_approvals': pending_approvals,
        'open_enquiries': open_enquiries,
        'demo_requests_pending': demo_requests_pending,
        'business_categories': business_categories,       
        'business_subcategories': business_subcategories,  
    }
    
    return render(request, 'admin/demos/watch.html', context)


@login_required
@permission_required('delete_demo')
@require_http_methods(["POST"])
def admin_delete_demo_view(request, demo_id):
    """Delete demo"""
    demo = get_object_or_404(Demo, id=demo_id)
    demo_title = demo.title
    
    try:
        # Delete files
        if demo.video_file:
            demo.video_file.delete(save=False)
        if demo.webgl_file:
            demo.webgl_file.delete(save=False)
        if demo.thumbnail:
            demo.thumbnail.delete(save=False)
        
        demo.delete()
        
        messages.success(request, f'Demo "{demo_title}" has been deleted successfully.')
        return redirect('core:admin_demos')
        
    except Exception as e:
        messages.error(request, f'Error deleting demo: {str(e)}')
        return redirect('core:admin_demos')


@login_required
@permission_required('manage_demo_access')
@require_http_methods(["POST"])
def admin_toggle_demo_status_view(request, demo_id):
    """Toggle demo active/inactive status"""
    demo = get_object_or_404(Demo, id=demo_id)
    
    try:
        data = json.loads(request.body)
        activate = data.get('activate', not demo.is_active)
        
        demo.is_active = activate
        demo.save()
        
        status = "activated" if activate else "deactivated"
        
        return JsonResponse({
            'success': True,
            'message': f'Demo "{demo.title}" has been {status}.',
            'is_active': demo.is_active
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error updating demo status.'
        })


@login_required
@permission_required('manage_demo_access')
@require_http_methods(["POST"])
def admin_bulk_demo_actions_view(request):
    """Handle bulk demo actions"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        demo_ids = data.get('demo_ids', [])
        
        if not demo_ids:
            return JsonResponse({
                'success': False,
                'message': 'No demos selected.'
            })
        
        demos = Demo.objects.filter(id__in=demo_ids)
        
        if action == 'activate':
            demos.update(is_active=True)
            message = f'{len(demo_ids)} demos have been activated.'
        elif action == 'deactivate':
            demos.update(is_active=False)
            message = f'{len(demo_ids)} demos have been deactivated.'
        elif action == 'delete':
            # Check delete permission
            if not request.user.has_perm('delete_demo'):
                return JsonResponse({
                    'success': False,
                    'message': 'You do not have permission to delete demos.'
                })
            
            for demo in demos:
                if demo.video_file:
                    demo.video_file.delete()
                if demo.webgl_file:
                    demo.webgl_file.delete()
                if demo.thumbnail:
                    demo.thumbnail.delete()
            demos.delete()
            message = f'{len(demo_ids)} demos have been deleted.'
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid action.'
            })
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Error performing bulk action.'
        })

@login_required
@permission_required('view_demos')
@user_passes_test(is_admin)
def admin_demo_stats_view(request):
    """AJAX endpoint for demo stats"""
    stats = {
        'total_demos': Demo.objects.count(),
        'active_demos': Demo.objects.filter(is_active=True).count(),
        'featured_demos': Demo.objects.filter(is_featured=True).count(),
        'total_views': DemoView.objects.count(),
        'last_updated': timezone.now().isoformat()
    }
    
    return JsonResponse(stats)    

# =====================================
# PLACEHOLDER ADMIN VIEWS
# =====================================

@login_required
@user_passes_test(is_admin)
def admin_enquiries_view(request):
    """Admin enquiries management with full functionality"""
    from django.db.models import Q
    from django.core.paginator import Paginator
    
    # Get all enquiries
    enquiries_list = BusinessEnquiry.objects.select_related(
        'user', 'category', 'assigned_to'
    ).order_by('-created_at')
    
    # Filtering
    search = request.GET.get('search')
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    sort_by = request.GET.get('sort', '-created_at')
    
    if search:
        enquiries_list = enquiries_list.filter(
            Q(enquiry_id__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(business_email__icontains=search) |
            Q(organization__icontains=search) |
            Q(subject__icontains=search) |
            Q(message__icontains=search)
        )
    
    if status_filter:
        enquiries_list = enquiries_list.filter(status=status_filter)
    
    if priority_filter:
        enquiries_list = enquiries_list.filter(priority=priority_filter)
    
    # Sorting
    sort_options = {
        'created_at': 'created_at',
        '-created_at': '-created_at',
        'priority': 'priority',
        '-priority': '-priority',
    }
    if sort_by in sort_options:
        enquiries_list = enquiries_list.order_by(sort_options[sort_by])
    
    # Statistics
    total_enquiries = BusinessEnquiry.objects.count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    in_progress_enquiries = BusinessEnquiry.objects.filter(status='in_progress').count()
    answered_enquiries = BusinessEnquiry.objects.filter(status='answered').count()
    
    # Pagination
    paginator = Paginator(enquiries_list, 10)  # 10 enquiries per page
    page_number = request.GET.get('page')
    enquiries = paginator.get_page(page_number)
    
    # Context for sidebar badges
    pending_approvals = User.objects.filter(
        is_approved=False, 
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    context = {
        'enquiries': enquiries,
        'search': search,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'sort_by': sort_by,
        
        # Statistics
        'total_enquiries': total_enquiries,
        'open_enquiries': open_enquiries,
        'in_progress_enquiries': in_progress_enquiries,
        'answered_enquiries': answered_enquiries,
        
        # Pagination
        'is_paginated': paginator.num_pages > 1,
        'page_obj': enquiries,
        
        # Sidebar badges
        'pending_approvals': pending_approvals,
        'demo_requests_pending': demo_requests_pending,
    }
    
    return render(request, 'admin/enquiries/list.html', context)

@login_required
@user_passes_test(is_admin)
def admin_enquiry_detail_view(request, enquiry_id):
    """Enquiry detail view with full information and response history"""
    enquiry = get_object_or_404(BusinessEnquiry, id=enquiry_id)
    
    # Get response history
    responses = EnquiryResponse.objects.filter(
        enquiry=enquiry
    ).select_related('responded_by').order_by('-created_at')
    
    # Mark as read if it's the first view
    if enquiry.status == 'open' and not enquiry.first_response_at:
        enquiry.first_response_at = timezone.now()
        enquiry.save(update_fields=['first_response_at'])
    
    # Handle status update
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['open', 'in_progress', 'answered', 'closed']:
            enquiry.status = new_status
            if new_status == 'closed':
                enquiry.closed_at = timezone.now()
            enquiry.save()
            messages.success(request, f'Enquiry status updated to {enquiry.get_status_display()}')
            return redirect('core:admin_enquiry_detail', enquiry_id=enquiry.id)
    
    # Context for sidebar badges
    pending_approvals = User.objects.filter(
        is_approved=False, 
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    context = {
        'enquiry': enquiry,
        'responses': responses,
        'pending_approvals': pending_approvals,
        'open_enquiries': open_enquiries,
        'demo_requests_pending': demo_requests_pending,
    }
    
    return render(request, 'admin/enquiries/detail.html', context)


@login_required
@user_passes_test(is_admin)
def admin_respond_enquiry_view(request, enquiry_id):
    """Respond to enquiry with email notification"""
    enquiry = get_object_or_404(BusinessEnquiry, id=enquiry_id)
    
    if request.method == 'POST':
        response_text = request.POST.get('response_text')
        is_internal_note = request.POST.get('is_internal_note') == 'on'
        send_email = request.POST.get('send_email') == 'on'
        
        if response_text:
            # Create response
            response = EnquiryResponse.objects.create(
                enquiry=enquiry,
                response_text=response_text,
                is_internal_note=is_internal_note,
                responded_by=request.user
            )
            
            # Update enquiry status
            if not is_internal_note:
                enquiry.status = 'answered'
                enquiry.last_response_at = timezone.now()
                if not enquiry.first_response_at:
                    enquiry.first_response_at = timezone.now()
                enquiry.save()
            
            # Send email if requested
            if send_email and not is_internal_note:
                try:
                    subject = f"Re: {enquiry.subject or 'Your Enquiry'}"
                    message = f"""
                    Dear {enquiry.first_name} {enquiry.last_name},
                    
                    Thank you for your enquiry. Here is our response:
                    
                    {response_text}
                    
                    Best regards,
                    {request.user.get_full_name() or 'Support Team'}
                    """
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [enquiry.business_email],
                        fail_silently=False,
                    )
                    
                    response.email_sent = True
                    response.email_sent_at = timezone.now()
                    response.save()
                    
                    messages.success(request, 'Response sent successfully via email!')
                except Exception as e:
                    messages.warning(request, f'Response saved but email failed: {str(e)}')
            else:
                messages.success(request, 'Response saved successfully!')
            
            return redirect('core:admin_enquiry_detail', enquiry_id=enquiry.id)
        else:
            messages.error(request, 'Please enter a response.')
    
    # Get previous responses for context
    previous_responses = EnquiryResponse.objects.filter(
        enquiry=enquiry
    ).select_related('responded_by').order_by('-created_at')[:5]
    
    # Context for sidebar badges
    pending_approvals = User.objects.filter(
        is_approved=False, 
        is_active=True,
        is_staff=False,
        is_superuser=False
    ).count()
    open_enquiries = BusinessEnquiry.objects.filter(status='open').count()
    demo_requests_pending = DemoRequest.objects.filter(status='pending').count()
    
    context = {
        'enquiry': enquiry,
        'previous_responses': previous_responses,
        'pending_approvals': pending_approvals,
        'open_enquiries': open_enquiries,
        'demo_requests_pending': demo_requests_pending,
    }
    
    return render(request, 'admin/enquiries/respond.html', context)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_delete_enquiry_view(request, enquiry_id):
    """Delete enquiry via AJAX"""
    enquiry = get_object_or_404(BusinessEnquiry, id=enquiry_id)
    enquiry_code = enquiry.enquiry_id
    
    try:
        enquiry.delete()
        return JsonResponse({
            'success': True,
            'message': f'Enquiry {enquiry_code} deleted successfully.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting enquiry: {str(e)}'
        })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_assign_enquiry_view(request, enquiry_id):
    """Assign enquiry to admin user"""
    enquiry = get_object_or_404(BusinessEnquiry, id=enquiry_id)
    
    try:
        data = json.loads(request.body)
        assignee_id = data.get('assignee_id')
        
        if assignee_id:
            assignee = get_object_or_404(User, id=assignee_id, is_staff=True)
            enquiry.assigned_to = assignee
        else:
            enquiry.assigned_to = None
        
        enquiry.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Enquiry assigned to {assignee.get_full_name() if assignee else "Unassigned"}.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning enquiry: {str(e)}'
        })


@login_required
@user_passes_test(is_admin)
@require_http_methods(["POST"])
def admin_update_enquiry_priority_view(request, enquiry_id):
    """Update enquiry priority"""
    enquiry = get_object_or_404(BusinessEnquiry, id=enquiry_id)
    
    try:
        data = json.loads(request.body)
        priority = data.get('priority')
        
        if priority in ['low', 'medium', 'high', 'urgent']:
            enquiry.priority = priority
            enquiry.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Priority updated to {enquiry.get_priority_display()}.'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Invalid priority level.'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating priority: {str(e)}'
        })


@login_required
@user_passes_test(is_admin)
def admin_export_enquiries_view(request):
    """Export enquiries to CSV"""
    import csv
    from django.http import HttpResponse
    
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="enquiries_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Enquiry ID', 'Date', 'Status', 'Priority', 
        'Customer Name', 'Email', 'Organization', 'Phone',
        'Subject', 'Message', 'Category', 'Assigned To'
    ])
    
    enquiries = BusinessEnquiry.objects.all().select_related('category', 'assigned_to')
    
    for enquiry in enquiries:
        writer.writerow([
            enquiry.enquiry_id,
            enquiry.created_at.strftime('%Y-%m-%d %H:%M'),
            enquiry.get_status_display(),
            enquiry.get_priority_display(),
            enquiry.full_name,
            enquiry.business_email,
            enquiry.organization or '',
            enquiry.full_mobile,
            enquiry.subject or '',
            enquiry.message,
            enquiry.category.name if enquiry.category else '',
            enquiry.assigned_to.get_full_name() if enquiry.assigned_to else ''
        ])
    
    return response


@login_required
@user_passes_test(is_admin)
def ajax_system_health(request):
    """AJAX endpoint for system health check"""
    health_status = {
        'database': 'healthy',
        'email': 'healthy', 
        'storage': 'healthy',
        'cache': 'healthy',
        'last_updated': timezone.now().isoformat()
    }
    
    return JsonResponse(health_status)


# =====================================
# UTILITY FUNCTIONS
# =====================================

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# =====================================
# AJAX ENDPOINTS
# =====================================




@require_http_methods(["GET"])
def get_subcategories_ajax(request):
    """AJAX endpoint to get subcategories for selected categories"""
    category_ids = request.GET.get('categories', '').split(',')
    
    subcategories = []
    
    if category_ids and category_ids[0]:
        try:
            # Get all subcategories for the selected categories
            subcats = BusinessSubCategory.objects.filter(
                category_id__in=category_ids,
                is_active=True
            ).select_related('category').order_by('category__name', 'name')
            
            for subcat in subcats:
                subcategories.append({
                    'id': subcat.id,
                    'name': subcat.name,
                    'category_id': subcat.category_id,
                    'category_name': subcat.category.name
                })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    return JsonResponse({
        'success': True,
        'subcategories': subcategories
    })

# Alternative simpler version if you want to use a single category
@csrf_exempt
@require_http_methods(["GET"])
def get_subcategories_for_category(request):
    """
    Get subcategories for a category
    ✅ FIXED: Using 'accounts' app instead of 'core'
    """
    try:
        category_id = request.GET.get('category_id')
        
        print(f"📥 Subcategory request for category_id: {category_id}")
        
        if not category_id:
            return JsonResponse({
                'success': False,
                'error': 'No category ID provided',
                'subcategories': []
            })
        
        # Convert to int
        try:
            category_id = int(category_id)
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Invalid category ID',
                'subcategories': []
            })
        
        # ✅ CRITICAL FIX: Import from 'accounts' app, NOT 'core'
        from django.apps import apps
        BusinessSubCategory = apps.get_model('accounts', 'BusinessSubCategory')
        BusinessCategory = apps.get_model('accounts', 'BusinessCategory')
        
        # Check if category exists
        if not BusinessCategory.objects.filter(id=category_id, is_active=True).exists():
            print(f"⚠️ Category {category_id} not found or inactive")
            return JsonResponse({
                'success': False,
                'error': f'Category {category_id} not found',
                'subcategories': []
            })
        
        # Get subcategories
        subcategories = BusinessSubCategory.objects.filter(
            category_id=category_id,
            is_active=True
        ).values('id', 'name').order_by('sort_order', 'name')
        
        result = list(subcategories)
        print(f"✅ Found {len(result)} subcategories for category {category_id}")
        
        return JsonResponse({
            'success': True,
            'subcategories': result,
            'count': len(result)
        })
        
    except Exception as e:
        print(f"❌ ERROR in get_subcategories_for_category: {e}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'subcategories': []
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def ajax_contact_sales(request):
    """AJAX endpoint for contact sales form"""
    try:
        data = json.loads(request.body)
        
        # Create contact message
        contact_message = ContactMessage.objects.create(
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone', ''),
            company=data.get('company', ''),
            subject='Sales Inquiry',
            message=data.get('message'),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Send notification email to sales team
        try:
            subject = f"New Sales Inquiry from {data.get('name')}"
            message = f"""
            New sales inquiry received:
            
            Name: {data.get('name')}
            Email: {data.get('email')}
            Phone: {data.get('phone')}
            Company: {data.get('company')}
            
            Message:
            {data.get('message')}
            
            Please follow up promptly.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.DEFAULT_FROM_EMAIL],
                fail_silently=True,
            )
        except Exception as e:
            pass
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you! Our sales team will contact you within 24 hours.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'Sorry, something went wrong. Please try again.'
        })

# AJAX endpoint for real-time email validation
@csrf_exempt
@require_http_methods(["POST"])
def validate_business_email_ajax(request):
    """AJAX endpoint for real-time business email validation"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        allow_override = data.get('allow_override', False)
        
        if not email:
            return JsonResponse({'valid': False, 'message': 'Email is required'})
        
        # Check if email exists
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'valid': False, 
                'message': 'A customer with this email already exists'
            })
        
        # Check business email domain
        blocked_domains = getattr(settings, 'BLOCKED_EMAIL_DOMAINS', [])
        domain = email.split('@')[1] if '@' in email else ''
        
        if domain.lower() in [d.lower() for d in blocked_domains]:
            if allow_override:
                return JsonResponse({
                    'valid': True,
                    'message': f'Personal email ({domain}) - Override enabled',
                    'warning': True
                })
            else:
                return JsonResponse({
                    'valid': False,
                    'message': f'Personal email domain ({domain}). Check "Allow personal email" to override.'
                })
        
        return JsonResponse({
            'valid': True,
            'message': 'Valid business email address'
        })
    
    except Exception as e:
        return JsonResponse({'valid': False, 'message': 'Invalid request'})
    

@login_required
@require_GET
def available_time_slots_api(request):
    """API endpoint to get available time slots for a given date"""
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({
            'success': False,
            'error': 'Date parameter is required'
        })
    
    try:
        # Parse date from string
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Check if date is not in the past
        if date_obj < timezone.now().date():
            return JsonResponse({
                'success': False,
                'error': 'Cannot schedule for a past date'
            })
        
        # Check if date is not a Sunday (assuming Sunday is off)
        if date_obj.weekday() == 6:  # Sunday
            return JsonResponse({
                'success': False,
                'error': 'Cannot schedule for a Sunday'
            })
    except ValueError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid date format'
        })
    
    # Get all time slots
    time_slots = TimeSlot.objects.filter(is_active=True).order_by('start_time')
    
    # If date is today, filter out past time slots
    if date_obj == timezone.now().date():
        current_time = timezone.now().time()
        time_slots = time_slots.filter(start_time__gt=current_time)
    
    # Check if any time slots are already booked for this date
    booked_slots = DemoRequest.objects.filter(
        requested_date=date_obj, 
        status__in=['pending', 'confirmed']
    ).values_list('requested_time_slot_id', flat=True)
    
    # Filter out booked slots
    available_slots = []
    for slot in time_slots:
        if slot.id not in booked_slots:
            available_slots.append({
                'id': slot.id,
                'display_time': slot.get_display_time(),  # यदि यह मेथड मौजूद नहीं है, तो अगले कदम देखें
                'start_time': slot.start_time.strftime('%H:%M'),
                'end_time': slot.end_time.strftime('%H:%M'),
            })
    
    return JsonResponse({
        'success': True,
        'slots': available_slots,
        'date': date_str
    })