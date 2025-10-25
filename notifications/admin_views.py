from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.db.models import Q
from accounts.decorators import permission_required
from accounts.models import CustomUser as User  # ✅ Fixed: Import with alias
from .models import Notification
from .services import NotificationService
from django.core.paginator import Paginator
from django.utils import timezone

@login_required
@permission_required('view_notifications')
def admin_notification_center(request):
    """
    Admin notification center page
    Shows all notifications for the logged-in admin user with enhanced date filtering
    """
    # Get filter parameters
    filter_type = request.GET.get('type', 'all')
    filter_status = request.GET.get('status', 'all')
    filter_date = request.GET.get('date_filter', 'all')
    search = request.GET.get('search', '')
    
    # Custom date filter parameters
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    
    # Base query
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('user', 'content_type').order_by('-created_at')
    
    # Apply notification type filter
    if filter_type != 'all':
        notifications = notifications.filter(notification_type=filter_type)
    
    # Apply read status filter
    if filter_status == 'unread':
        notifications = notifications.filter(is_read=False)
    elif filter_status == 'read':
        notifications = notifications.filter(is_read=True)
    
    # Apply date filters
    now = timezone.now()
    if filter_date == 'today':
        # Today's notifications (last 24 hours)
        notifications = notifications.filter(
            created_at__gte=now.replace(hour=0, minute=0, second=0, microsecond=0)
        )
    elif filter_date == 'yesterday':
        # Yesterday's notifications
        yesterday_start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_end = now.replace(hour=0, minute=0, second=0, microsecond=0)
        notifications = notifications.filter(
            created_at__gte=yesterday_start,
            created_at__lt=yesterday_end
        )
    elif filter_date == 'week':
        # Last 7 days
        week_ago = now - timedelta(days=7)
        notifications = notifications.filter(
            created_at__gte=week_ago
        )
    elif filter_date == 'month':
        # Last 30 days
        month_ago = now - timedelta(days=30)
        notifications = notifications.filter(
            created_at__gte=month_ago
        )
    elif filter_date == 'custom' and start_date and end_date:
        # Custom date range
        try:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.get_current_timezone())
            # Add one day to end_date to make it inclusive
            end_date_obj = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).replace(tzinfo=timezone.get_current_timezone())
            
            notifications = notifications.filter(
                created_at__gte=start_date_obj,
                created_at__lt=end_date_obj
            )
        except ValueError:
            # If date parsing fails, don't apply the filter
            pass
    
    # Apply search filter
    if search:
        notifications = notifications.filter(
            Q(title__icontains=search) | Q(message__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Stats
    total_count = Notification.objects.filter(user=request.user).count()
    unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    read_count = total_count - unread_count
    
    # Notification type counts
    type_counts = {}
    for ntype, label in Notification.NOTIFICATION_TYPES:
        count = Notification.objects.filter(
            user=request.user,
            notification_type=ntype
        ).count()
        if count > 0:
            type_counts[ntype] = {'label': label, 'count': count}
    
    # Date filter options
    date_filters = [
        ('all', 'All Time'),
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('week', 'Last 7 Days'),
        ('month', 'Last 30 Days'),
        ('custom', 'Custom Range')
    ]
    
    context = {
        'notifications': page_obj,
        'total_count': total_count,
        'unread_count': unread_count,
        'read_count': read_count,
        'type_counts': type_counts,
        'filter_type': filter_type,
        'filter_status': filter_status,
        'filter_date': filter_date,
        'date_filters': date_filters,
        'start_date': start_date,
        'end_date': end_date,
        'search': search,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    
    return render(request, 'notifications/admin_notifications.html', context)

@login_required
@permission_required('change_notification')
def mark_all_notifications_read(request):
    """Mark all notifications as read for the current user"""
    if request.method == 'POST':
        unread_notifications = Notification.objects.filter(
            user=request.user,
            is_read=False
        )
        
        current_time = timezone.now()
        
        # Use bulk update for better performance with many notifications
        unread_count = unread_notifications.count()
        if unread_count > 0:
            # Create a list of notifications to update
            notifications_to_update = list(unread_notifications)
            for notification in notifications_to_update:
                notification.is_read = True
                notification.read_at = current_time
            
            # Perform bulk update
            Notification.objects.bulk_update(
                notifications_to_update, 
                ['is_read', 'read_at']
            )
            
            # Add success message
            messages.success(request, f"{unread_count} notifications marked as read.")
    
    # Redirect with filter parameters preserved
    redirect_url = 'admin_notification_center'
    filter_params = {}
    
    for param in ['type', 'status', 'date_filter', 'search', 'start_date', 'end_date', 'page']:
        value = request.GET.get(param)
        if value:
            filter_params[param] = value
    
    return redirect(redirect_url + '?' + '&'.join([f'{k}={v}' for k, v in filter_params.items()]))

# Mark a single notification as read
@login_required
@permission_required('change_notification')
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        
        # Only mark as read if it's currently unread
        if not notification.is_read:
            notification.mark_as_read()
            
            # Return success response for AJAX calls
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'success'})
        else:
            # Already read
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'already_read'})
                
    except Notification.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
    
    # If not an AJAX request, redirect back to notification center with filters preserved
    redirect_url = 'admin_notification_center'
    filter_params = {}
    
    for param in ['type', 'status', 'date_filter', 'search', 'start_date', 'end_date', 'page']:
        value = request.GET.get(param)
        if value:
            filter_params[param] = value
    
    return redirect(redirect_url + '?' + '&'.join([f'{k}={v}' for k, v in filter_params.items()]))

@login_required
@require_http_methods(["GET"])
def admin_notification_list_api(request):
    """API: Get admin notifications list - with permission filtering"""
    limit = int(request.GET.get('limit', 20))
    
    # Get all notifications
    notifications = Notification.objects.filter(
        user=request.user
    ).select_related('user', 'content_type').order_by('-created_at')[:limit]
    
    notifications_data = []
    for notif in notifications:
        # ✅ Check permission based on notification type
        if should_show_notification(request.user, notif):
            url = get_notification_url(notif)
            
            data = {
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'notification_type': notif.notification_type,
                'is_read': notif.is_read,
                'created_at': notif.created_at.strftime('%b %d, %Y %I:%M %p'),
                'link': url,
                'object_id': notif.object_id,
                'content_type': notif.content_type.model if notif.content_type else None,
            }
            notifications_data.append(data)
    
    return JsonResponse({
        'success': True,
        'notifications': notifications_data
    })


def should_show_notification(user, notification):
    """Check if user should see this notification based on permissions"""
    
    permission_map = {
        'new_customer': 'view_customers',
        'demo_request': 'view_demo_requests',
        'demo_cancellation': 'view_demo_requests',
        'enquiry': 'view_enquiries',
        'milestone': None,  # Everyone can see
        'system_announcement': None,  # Everyone can see
    }
    
    required_permission = permission_map.get(notification.notification_type)
    
    # If no permission required, show to everyone
    if not required_permission:
        return True
    
    # Check if user has required permission
    return user.has_permission(required_permission)

def get_notification_url(notification):
    """Generate URL for notification based on type"""
    obj_id = notification.object_id
    notif_type = notification.notification_type
    
    try:
        if notif_type == 'new_customer':
            if obj_id:
                return reverse('core:admin_customer_detail', kwargs={'customer_id': obj_id})
            return reverse('core:admin_users')
        
        elif notif_type == 'demo_request':
            if obj_id:
                return reverse('core:admin_demo_request_detail', kwargs={'request_id': obj_id})
            return reverse('core:admin_demo_requests')
        
        elif notif_type == 'demo_cancellation':
            if obj_id:
                return reverse('core:admin_demo_request_detail', kwargs={'request_id': obj_id})
            return reverse('core:admin_demo_requests') + '?status=cancelled'
        
        elif notif_type == 'enquiry':
            if obj_id:
                return reverse('core:admin_enquiry_detail', kwargs={'enquiry_id': obj_id})
            return reverse('core:admin_enquiries')
        
        elif notif_type == 'milestone':
            return reverse('core:admin_dashboard')
        
        elif notif_type == 'system_announcement':
            return reverse('notifications:admin_notifications')
        
        else:
            return reverse('notifications:admin_notifications')
            
    except Exception as e:
        print(f"Error generating notification URL: {e}")
        return reverse('notifications:admin_notifications')


@login_required
@require_http_methods(["GET"])
def admin_unread_count_api(request):
    """API: Get unread notification count for admin"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'success': True,
        'count': count
    })


@login_required
@require_http_methods(["POST"])
def admin_mark_as_read_api(request, notification_id):
    """API: Mark a notification as read"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.is_read = True
        notification.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found'
        }, status=404)


@login_required
@require_http_methods(["POST"])
def admin_mark_all_as_read_api(request):
    """API: Mark all notifications as read for admin"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)
    
    return JsonResponse({
        'success': True,
        'message': f'{count} notifications marked as read',
        'count': count
    })


@login_required
@require_http_methods(["DELETE", "POST"])
def admin_delete_notification_api(request, notification_id):
    """API: Delete a notification"""
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted successfully'
        })
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found'
        }, status=404)


# ===== NOTIFICATION PREFERENCES =====
@login_required
def admin_notification_preferences(request):
    """Admin notification preferences page"""
    
    if request.method == 'POST':
        # Save preferences (you can extend User model with preferences field)
        email_enabled = request.POST.get('email_enabled') == 'on'
        sms_enabled = request.POST.get('sms_enabled') == 'on'
        
        # Save to user profile or settings
        # request.user.notification_preferences = {...}
        # request.user.save()
        
        messages.success(request, '✅ Notification preferences updated successfully!')
        return redirect('notifications:admin_preferences')
    
    context = {
        # Get current preferences
        'email_enabled': True,
        'sms_enabled': False,
    }
    
    return render(request, 'notifications/admin_preferences.html', context)


# ===== BULK NOTIFICATION SENDER =====
@login_required
@permission_required('send_notification')  # ✅ Permission required
def admin_send_bulk_notification(request):
    """Send bulk notifications to customers"""
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        recipient_type = request.POST.get('recipient_type', 'all')
        send_email = request.POST.get('send_email') == 'on'
        notification_type = request.POST.get('notification_type', 'system_announcement')
        
        # Validate inputs
        if not title or not message:
            messages.error(request, '❌ Title and message are required!')
            return redirect('notifications:admin_bulk_send')
        
        if len(title) < 5:
            messages.error(request, '❌ Title must be at least 5 characters!')
            return redirect('notifications:admin_bulk_send')
        
        if len(message) < 10:
            messages.error(request, '❌ Message must be at least 10 characters!')
            return redirect('notifications:admin_bulk_send')
        
        # Get recipients based on type
        if recipient_type == 'active':
            recipients = User.objects.filter(
                is_active=True,
                user_type='customer',
                is_approved=True
            )
        elif recipient_type == 'inactive':
            recipients = User.objects.filter(
                is_active=False,
                user_type='customer'
            )
        elif recipient_type == 'pending':
            recipients = User.objects.filter(
                user_type='customer',
                is_approved=False
            )
        elif recipient_type == 'staff':
            recipients = User.objects.filter(is_staff=True)
        else:  # all
            recipients = User.objects.filter(user_type='customer')
        
        # Send notifications
        success_count = 0
        error_count = 0
        
        for user in recipients:
            try:
                NotificationService.send_custom_notification(
                    user=user,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    send_email=send_email
                )
                success_count += 1
            except Exception as e:
                print(f"Error sending notification to {user.email}: {e}")
                error_count += 1
        
        if success_count > 0:
            messages.success(
                request,
                f'✅ Bulk notification sent to {success_count} user(s)!'
            )
        
        if error_count > 0:
            messages.warning(
                request,
                f'⚠️ Failed to send to {error_count} user(s)'
            )
        
        return redirect('notifications:admin_bulk_send')
    
    # GET request - show form
    # Get user statistics
    total_customers = User.objects.filter(user_type='customer').count()
    active_customers = User.objects.filter(
        user_type='customer',
        is_active=True,
        is_approved=True
    ).count()
    inactive_customers = User.objects.filter(
        user_type='customer',
        is_active=False
    ).count()
    pending_customers = User.objects.filter(
        user_type='customer',
        is_approved=False
    ).count()
    total_staff = User.objects.filter(is_staff=True).count()
    
    context = {
        'total_customers': total_customers,
        'active_customers': active_customers,
        'inactive_customers': inactive_customers,
        'pending_customers': pending_customers,
        'total_staff': total_staff,
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    
    return render(request, 'notifications/admin_bulk_send.html', context)


# ===== CREATE ANNOUNCEMENT =====
@login_required
@permission_required('create_announcement')  # ✅ Permission required
def admin_create_announcement(request):
    """Create system-wide announcement"""
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        priority = request.POST.get('priority', 'normal')
        send_to_all = request.POST.get('send_to_all') == 'on'
        send_email = request.POST.get('send_email') == 'on'
        
        if not title or not message:
            messages.error(request, '❌ Title and message are required!')
            return redirect('notifications:admin_create_announcement')
        
        # Create announcement for all users or specific groups
        if send_to_all:
            recipients = User.objects.all()
        else:
            recipients = User.objects.filter(is_staff=True)
        
        success_count = 0
        for user in recipients:
            try:
                NotificationService.send_custom_notification(
                    user=user,
                    title=f"📢 Announcement: {title}",
                    message=message,
                    notification_type='system_announcement',
                    send_email=send_email
                )
                success_count += 1
            except Exception as e:
                print(f"Error sending announcement to {user.email}: {e}")
        
        messages.success(
            request,
            f'✅ Announcement sent to {success_count} user(s)!'
        )
        return redirect('notifications:admin_notifications')
    
    return render(request, 'notifications/admin_create_announcement.html')


# ===== NOTIFICATION TEMPLATES =====
@login_required
@permission_required('manage_templates')  # ✅ Permission required
def admin_notification_templates(request):
    """Manage notification templates"""
    # This can be extended to manage reusable templates
    
    templates = [
        {
            'id': 1,
            'name': 'Welcome Customer',
            'title': 'Welcome to CHRP India!',
            'message': 'Thank you for registering...',
            'type': 'new_customer'
        },
        {
            'id': 2,
            'name': 'Demo Confirmed',
            'title': 'Your demo has been confirmed',
            'message': 'Your demo request has been approved...',
            'type': 'demo_request'
        },
    ]
    
    context = {
        'templates': templates,
    }
    
    return render(request, 'notifications/admin_templates.html', context)