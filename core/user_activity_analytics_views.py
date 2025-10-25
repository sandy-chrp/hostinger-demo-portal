# core/user_activity_analytics_views.py - FIXED AGGREGATION

from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.functions import ExtractHour
from datetime import timedelta, datetime
import json

from django.contrib.auth import get_user_model
from demos.models import Demo, DemoView, DemoRequest
from enquiries.models import BusinessEnquiry

User = get_user_model()


def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@login_required
@user_passes_test(is_admin)
def user_activity_analytics_page(request):
    period = request.GET.get('period', 'today')
    context = {'activity_period': period, 'page_title': 'User Activity Analytics'}
    return render(request, 'admin/user_activity_analytics.html', context)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def ajax_activity_analytics(request):
    try:
        period = request.GET.get('period', 'today')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        end_date = timezone.now()
        today = timezone.now().date()
        
        if period == 'today':
            start_date = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
            end_date = timezone.now()
            date_format = '%H:%M'
            group_label = 'Today'
        elif period == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.min.time()))
            end_date = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.max.time()))
            date_format = '%H:%M'
            group_label = 'Yesterday'
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=12)
            date_format = 'Week %W'
            group_label = 'Last 12 Weeks'
        elif period == 'monthly':
            start_date = end_date - timedelta(days=365)
            date_format = '%b %Y'
            group_label = 'Last 12 Months'
        elif period == 'custom' and start_date_str and end_date_str:
            try:
                start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
                end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
                date_format = '%m/%d'
                group_label = f"{start_date_str} to {end_date_str}"
            except ValueError as e:
                return JsonResponse({'success': False, 'error': f'Invalid date format: {str(e)}'}, status=400)
        else:
            start_date = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
            date_format = '%H:%M'
            group_label = 'Today'
        
        period_duration = max((end_date.date() - start_date.date()).days, 1)
        previous_period_end = start_date
        previous_period_start = previous_period_end - timedelta(days=period_duration)
        
        # Stats calculations
        current_active_users = User.objects.filter(
            Q(demo_views__viewed_at__range=[start_date, end_date]) |
            Q(demo_requests__created_at__range=[start_date, end_date]) |
            Q(enquiries__created_at__range=[start_date, end_date]),
            is_staff=False, is_superuser=False
        ).distinct().count()
        
        previous_active_users = User.objects.filter(
            Q(demo_views__viewed_at__range=[previous_period_start, previous_period_end]) |
            Q(demo_requests__created_at__range=[previous_period_start, previous_period_end]) |
            Q(enquiries__created_at__range=[previous_period_start, previous_period_end]),
            is_staff=False, is_superuser=False
        ).distinct().count()
        
        active_users_change = round(((current_active_users - previous_active_users) / max(previous_active_users, 1)) * 100, 1) if previous_active_users > 0 else 0
        
        current_views = DemoView.objects.filter(viewed_at__range=[start_date, end_date]).count()
        previous_views = DemoView.objects.filter(viewed_at__range=[previous_period_start, previous_period_end]).count()
        views_change = round(((current_views - previous_views) / max(previous_views, 1)) * 100, 1) if previous_views > 0 else 0
        
        current_requests = DemoRequest.objects.filter(created_at__range=[start_date, end_date]).count()
        previous_requests = DemoRequest.objects.filter(created_at__range=[previous_period_start, previous_period_end]).count()
        requests_change = round(((current_requests - previous_requests) / max(previous_requests, 1)) * 100, 1) if previous_requests > 0 else 0
        
        current_enquiries = BusinessEnquiry.objects.filter(created_at__range=[start_date, end_date]).count()
        previous_enquiries = BusinessEnquiry.objects.filter(created_at__range=[previous_period_start, previous_period_end]).count()
        enquiries_change = round(((current_enquiries - previous_enquiries) / max(previous_enquiries, 1)) * 100, 1) if previous_enquiries > 0 else 0
        
        # Timeline data generation
        timeline_data = []
        
        if period in ['today', 'yesterday']:
            # Hourly breakdown
            for hour in range(24):
                hour_start = timezone.make_aware(timezone.datetime.combine(start_date.date(), timezone.datetime.min.time())) + timedelta(hours=hour)
                hour_end = hour_start + timedelta(hours=1)
                if hour_end > end_date:
                    hour_end = end_date
                
                views = DemoView.objects.filter(viewed_at__range=[hour_start, hour_end]).count()
                requests = DemoRequest.objects.filter(created_at__range=[hour_start, hour_end]).count()
                enquiries = BusinessEnquiry.objects.filter(created_at__range=[hour_start, hour_end]).count()
                logins = User.objects.filter(last_login__range=[hour_start, hour_end], is_staff=False, is_superuser=False).count()
                
                timeline_data.append({
                    'date': hour_start.strftime('%H:00'),
                    'views': views,
                    'requests': requests,
                    'enquiries': enquiries,
                    'logins': logins,
                })
        
        elif period == 'weekly':
            # Weekly aggregation - group by week
            current_date = start_date.date()
            week_data = {}
            
            while current_date <= end_date.date():
                # Get week number and year
                week_key = current_date.strftime('Week %W, %Y')
                
                date_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
                date_end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
                
                if week_key not in week_data:
                    week_data[week_key] = {'views': 0, 'requests': 0, 'enquiries': 0, 'logins': 0}
                
                week_data[week_key]['views'] += DemoView.objects.filter(viewed_at__range=[date_start, date_end]).count()
                week_data[week_key]['requests'] += DemoRequest.objects.filter(created_at__range=[date_start, date_end]).count()
                week_data[week_key]['enquiries'] += BusinessEnquiry.objects.filter(created_at__range=[date_start, date_end]).count()
                week_data[week_key]['logins'] += User.objects.filter(last_login__range=[date_start, date_end], is_staff=False, is_superuser=False).count()
                
                current_date += timedelta(days=1)
            
            # Convert to list
            for week_label, data in week_data.items():
                timeline_data.append({
                    'date': week_label.replace(', ' + str(end_date.year), ''),
                    'views': data['views'],
                    'requests': data['requests'],
                    'enquiries': data['enquiries'],
                    'logins': data['logins'],
                })
        
        elif period == 'monthly':
            # Monthly aggregation - group by month
            current_date = start_date.date()
            month_data = {}
            
            while current_date <= end_date.date():
                # Get month and year
                month_key = current_date.strftime('%b %Y')
                
                date_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
                date_end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
                
                if month_key not in month_data:
                    month_data[month_key] = {'views': 0, 'requests': 0, 'enquiries': 0, 'logins': 0}
                
                month_data[month_key]['views'] += DemoView.objects.filter(viewed_at__range=[date_start, date_end]).count()
                month_data[month_key]['requests'] += DemoRequest.objects.filter(created_at__range=[date_start, date_end]).count()
                month_data[month_key]['enquiries'] += BusinessEnquiry.objects.filter(created_at__range=[date_start, date_end]).count()
                month_data[month_key]['logins'] += User.objects.filter(last_login__range=[date_start, date_end], is_staff=False, is_superuser=False).count()
                
                current_date += timedelta(days=1)
            
            # Convert to list
            for month_label, data in month_data.items():
                timeline_data.append({
                    'date': month_label,
                    'views': data['views'],
                    'requests': data['requests'],
                    'enquiries': data['enquiries'],
                    'logins': data['logins'],
                })
        
        else:
            # Daily breakdown for custom range
            current_date = start_date.date()
            while current_date <= end_date.date():
                date_start = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.min.time()))
                date_end = timezone.make_aware(timezone.datetime.combine(current_date, timezone.datetime.max.time()))
                
                views = DemoView.objects.filter(viewed_at__range=[date_start, date_end]).count()
                requests = DemoRequest.objects.filter(created_at__range=[date_start, date_end]).count()
                enquiries = BusinessEnquiry.objects.filter(created_at__range=[date_start, date_end]).count()
                logins = User.objects.filter(last_login__range=[date_start, date_end], is_staff=False, is_superuser=False).count()
                
                timeline_data.append({
                    'date': current_date.strftime(date_format),
                    'views': views,
                    'requests': requests,
                    'enquiries': enquiries,
                    'logins': logins,
                })
                
                current_date += timedelta(days=1)
        
        # Peak hours calculation
        last_30_days = timezone.now() - timedelta(days=30)
        
        demo_view_hours = DemoView.objects.filter(viewed_at__gte=last_30_days).annotate(hour=ExtractHour('viewed_at')).values('hour').annotate(count=Count('id'))
        demo_request_hours = DemoRequest.objects.filter(created_at__gte=last_30_days).annotate(hour=ExtractHour('created_at')).values('hour').annotate(count=Count('id'))
        enquiry_hours = BusinessEnquiry.objects.filter(created_at__gte=last_30_days).annotate(hour=ExtractHour('created_at')).values('hour').annotate(count=Count('id'))
        
        hour_counts = {}
        for item in demo_view_hours:
            if item['hour'] is not None:
                hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
        for item in demo_request_hours:
            if item['hour'] is not None:
                hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
        for item in enquiry_hours:
            if item['hour'] is not None:
                hour_counts[item['hour']] = hour_counts.get(item['hour'], 0) + item['count']
        
        total_activities = sum(hour_counts.values()) if hour_counts else 0
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        peak_hours = []
        for hour, count in sorted_hours:
            percentage = round((count / total_activities * 100), 1) if total_activities > 0 else 0
            time_slot = f"{hour:02d}:00 - {(hour+1):02d}:00"
            peak_hours.append({'time_slot': time_slot, 'count': count, 'percentage': percentage})
        
        # Most active users
        most_active_users = User.objects.filter(is_staff=False, is_superuser=False).annotate(
            activity_count=(
                Count('demo_views', filter=Q(demo_views__viewed_at__gte=last_30_days)) + 
                Count('demo_requests', filter=Q(demo_requests__created_at__gte=last_30_days)) + 
                Count('enquiries', filter=Q(enquiries__created_at__gte=last_30_days))
            )
        ).filter(activity_count__gt=0).order_by('-activity_count')[:10]
        
        active_users_list = []
        for user in most_active_users:
            active_users_list.append({
                'full_name': user.get_full_name() or user.email,
                'email': user.email,
                'organization': user.organization if hasattr(user, 'organization') else 'N/A',
                'activity_count': user.activity_count
            })
        
        response_data = {
            'success': True,
            'period': period,
            'period_label': group_label,
            'stats': {
                'active_users': {'value': current_active_users, 'change': active_users_change, 'previous': previous_active_users},
                'total_views': {'value': current_views, 'change': views_change, 'previous': previous_views},
                'demo_requests': {'value': current_requests, 'change': requests_change, 'previous': previous_requests},
                'enquiries': {'value': current_enquiries, 'change': enquiries_change, 'previous': previous_enquiries}
            },
            'timeline': timeline_data,
            'peak_hours': peak_hours,
            'most_active_users': active_users_list,
            'date_range': {'start': start_date.strftime('%Y-%m-%d'), 'end': end_date.strftime('%Y-%m-%d')}
        }
        
        return JsonResponse(response_data)
    
    except Exception as e:
        import traceback
        print(f"Error in ajax_activity_analytics: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def ajax_quick_stats(request):
    try:
        today = timezone.now().date()
        today_views = DemoView.objects.filter(viewed_at__date=today).count()
        today_requests = DemoRequest.objects.filter(created_at__date=today).count()
        today_enquiries = BusinessEnquiry.objects.filter(created_at__date=today).count()
        today_signups = User.objects.filter(created_at__date=today, is_staff=False, is_superuser=False).count()
        
        last_hour = timezone.now() - timedelta(hours=1)
        active_now = User.objects.filter(last_login__gte=last_hour, is_staff=False, is_superuser=False).count()
        
        return JsonResponse({
            'success': True,
            'today': {'views': today_views, 'requests': today_requests, 'enquiries': today_enquiries, 'signups': today_signups, 'active_now': active_now},
            'timestamp': timezone.now().isoformat()
        })
    except Exception as e:
        import traceback
        print(f"Error in ajax_quick_stats: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@user_passes_test(is_admin)
@require_http_methods(["GET"])
def ajax_registration_data(request):
    try:
        period = request.GET.get('period', 'today')
        start_date_str = request.GET.get('start_date')
        end_date_str = request.GET.get('end_date')
        
        today = timezone.now().date()
        end_date = timezone.now()
        
        if period == 'today':
            start_date = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
            date_format = '%H:00'
        elif period == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.min.time()))
            end_date = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.max.time()))
            date_format = '%H:00'
        elif period == 'weekly':
            start_date = end_date - timedelta(weeks=12)
            date_format = 'Week %W'
        elif period == 'monthly':
            start_date = end_date - timedelta(days=365)
            date_format = '%b %Y'
        elif period == 'custom' and start_date_str and end_date_str:
            try:
                start_date = timezone.make_aware(datetime.strptime(start_date_str, '%Y-%m-%d'))
                end_date = timezone.make_aware(datetime.strptime(end_date_str, '%Y-%m-%d'))
                date_format = '%m/%d'
            except ValueError as e:
                return JsonResponse({'success': False, 'error': f'Invalid date format: {str(e)}'}, status=400)
        else:
            start_date = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
            date_format = '%H:00'
        
        monthly_users = []
        
        if period == 'monthly':
            # Monthly aggregation
            current_date = start_date.date()
            month_data = {}
            
            while current_date <= end_date.date():
                month_key = current_date.strftime('%b %Y')
                
                if month_key not in month_data:
                    month_data[month_key] = 0
                
                count = User.objects.filter(created_at__date=current_date, is_staff=False, is_superuser=False).count()
                month_data[month_key] += count
                
                current_date += timedelta(days=1)
            
            for month_label, count in month_data.items():
                monthly_users.append({'month': month_label, 'count': count})
        
        elif period == 'weekly':
            # Weekly aggregation
            current_date = start_date.date()
            week_data = {}
            
            while current_date <= end_date.date():
                week_key = current_date.strftime('Week %W, %Y')
                
                if week_key not in week_data:
                    week_data[week_key] = 0
                
                count = User.objects.filter(created_at__date=current_date, is_staff=False, is_superuser=False).count()
                week_data[week_key] += count
                
                current_date += timedelta(days=1)
            
            for week_label, count in week_data.items():
                monthly_users.append({'month': week_label.replace(', ' + str(end_date.year), ''), 'count': count})
        
        elif period in ['today', 'yesterday']:
            # Hourly breakdown
            for hour in range(24):
                hour_start = start_date + timedelta(hours=hour)
                hour_end = hour_start + timedelta(hours=1)
                if hour_end > end_date:
                    hour_end = end_date
                count = User.objects.filter(created_at__range=[hour_start, hour_end], is_staff=False, is_superuser=False).count()
                monthly_users.append({'month': hour_start.strftime('%H:00'), 'count': count})
        
        else:
            # Daily breakdown
            current_date = start_date.date()
            while current_date <= end_date.date():
                count = User.objects.filter(created_at__date=current_date, is_staff=False, is_superuser=False).count()
                monthly_users.append({'month': current_date.strftime(date_format), 'count': count})
                current_date += timedelta(days=1)
        
        return JsonResponse({'success': True, 'period': period, 'monthly_users': monthly_users})
    except Exception as e:
        import traceback
        print(f"Error in ajax_registration_data: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': f'Server error: {str(e)}'}, status=500)