# notifications/api_views.py
"""
Customer-facing notification APIs with WebSocket integration
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from .services import NotificationService
import logging

logger = logging.getLogger(__name__)


def get_time_ago(dt):
    """Convert datetime to human readable time ago"""
    now = timezone.now()
    diff = (now - dt).total_seconds()
    
    if diff < 60:
        return 'Just now'
    elif diff < 3600:
        mins = int(diff / 60)
        return f'{mins} min ago' if mins > 1 else '1 min ago'
    elif diff < 86400:
        hours = int(diff / 3600)
        return f'{hours} hour ago' if hours > 1 else '1 hour ago'
    elif diff < 604800:
        days = int(diff / 86400)
        return f'{days} day ago' if days > 1 else '1 day ago'
    else:
        return dt.strftime('%b %d, %Y')


def get_icon(notification_type):
    """Get FontAwesome icon for notification type"""
    icons = {
        'account_approved': 'fa-check-circle',
        'demo_confirmation': 'fa-calendar-check',
        'demo_reschedule': 'fa-calendar-alt',
        'demo_cancellation': 'fa-calendar-times',
        'enquiry_received': 'fa-envelope',
        'enquiry_response': 'fa-reply',
        'new_demo_available': 'fa-video',
        'system_announcement': 'fa-bullhorn',
    }
    return icons.get(notification_type, 'fa-bell')


def get_color(notification_type):
    """Get color class for notification type"""
    colors = {
        'account_approved': 'success',
        'demo_confirmation': 'primary',
        'demo_reschedule': 'warning',
        'demo_cancellation': 'danger',
        'enquiry_received': 'info',
        'enquiry_response': 'success',
        'new_demo_available': 'primary',
        'system_announcement': 'info',
    }
    return colors.get(notification_type, 'secondary')


@login_required
@require_http_methods(["GET"])
def get_notifications_api(request):
    """
    API: Get user notifications with optional filtering
    Query params:
      - limit: Number of notifications (default: 10)
      - unread_only: true/false (default: false)
    """
    try:
        limit = int(request.GET.get('limit', 10))
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
        
        # Base query
        notifications = Notification.objects.filter(user=request.user)
        
        # Apply filters
        if unread_only:
            notifications = notifications.filter(is_read=False)
        
        # Get unread count
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # Limit results
        notifications = notifications.select_related('content_type').order_by('-created_at')[:limit]
        
        # Format response
        data = []
        for n in notifications:
            data.append({
                'id': n.id,
                'type': n.notification_type,
                'title': n.title,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat(),
                'time_ago': get_time_ago(n.created_at),
                'icon': get_icon(n.notification_type),
                'color': get_color(n.notification_type),
                'link': n.link if hasattr(n, 'link') else None,
            })
        
        return JsonResponse({
            'success': True,
            'notifications': data,
            'unread_count': unread_count,
        })
        
    except Exception as e:
        logger.error(f"Error in get_notifications_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def mark_as_read_api(request, notification_id):
    """
    API: Mark notification as read
    ✅ Sends WebSocket update with new unread count
    """
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user
        )
        
        # Mark as read
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        
        # Get updated unread count
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # ✅ Send WebSocket update
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{request.user.id}',
                {
                    'type': 'unread_count_update',
                    'count': unread_count
                }
            )
            logger.info(f"WebSocket: Sent unread count to user_{request.user.id}: {unread_count}")
        except Exception as ws_error:
            logger.warning(f"WebSocket send failed (non-critical): {ws_error}")
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count,
        })
        
    except Exception as e:
        logger.error(f"Error in mark_as_read_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def mark_all_as_read_api(request):
    """
    API: Mark all notifications as read for user
    ✅ Sends WebSocket update
    """
    try:
        # Mark all as read
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # ✅ Send WebSocket update
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'user_{request.user.id}',
                {
                    'type': 'unread_count_update',
                    'count': 0
                }
            )
            logger.info(f"WebSocket: Sent mark all read to user_{request.user.id}")
        except Exception as ws_error:
            logger.warning(f"WebSocket send failed (non-critical): {ws_error}")
        
        return JsonResponse({
            'success': True,
            'count': count,
            'message': f'{count} notifications marked as read'
        })
        
    except Exception as e:
        logger.error(f"Error in mark_all_as_read_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def get_unread_count_api(request):
    """API: Get unread notification count"""
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return JsonResponse({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error in get_unread_count_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])
def delete_notification_api(request, notification_id):
    """
    API: Delete a notification
    ✅ Sends WebSocket update if unread notification deleted
    """
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user
        )
        
        was_unread = not notification.is_read
        notification.delete()
        
        # Get updated unread count
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # ✅ Send WebSocket update if unread deleted
        if was_unread:
            try:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'user_{request.user.id}',
                    {
                        'type': 'unread_count_update',
                        'count': unread_count
                    }
                )
            except Exception as ws_error:
                logger.warning(f"WebSocket send failed: {ws_error}")
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted',
            'unread_count': unread_count
        })
        
    except Exception as e:
        logger.error(f"Error in delete_notification_api: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)