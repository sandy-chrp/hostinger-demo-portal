# notifications/admin_api_views.py
"""
Admin Notification API Endpoints - FINAL FIXED VERSION
✅ Correct timezone handling
✅ Fixed variable name typo
✅ Function names match existing URLs
✅ WebSocket integration
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
import logging

logger = logging.getLogger(__name__)


# ============================================
# HELPER FUNCTIONS
# ============================================

def should_show_notification(user, notification):
    """Check if user should see notification based on permissions"""
    permission_map = {
        'new_customer': 'view_customers',
        'demo_request': 'view_demo_requests',
        'demo_cancellation': 'view_demo_requests',
        'enquiry': 'view_enquiries',
        'milestone': None,
        'system_announcement': None,
    }
    
    required_permission = permission_map.get(notification.notification_type)
    
    if not required_permission:
        return True
    
    return user.has_permission(required_permission)


def get_notification_url(notification):
    """Generate URL based on notification type"""
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
        logger.error(f"Error generating URL: {e}")
        return reverse('notifications:admin_notifications')


def send_websocket_update(user_id, count):
    """Send WebSocket unread count update"""
    try:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'user_{user_id}',
            {
                'type': 'unread_count_update',
                'count': count
            }
        )
        logger.info(f"WebSocket: Sent count to user_{user_id}: {count}")
        return True
    except Exception as e:
        logger.warning(f"WebSocket failed: {e}")
        return False


# ============================================
# API ENDPOINTS (Names match existing URLs)
# ============================================

@login_required
@require_http_methods(["GET"])
def admin_unread_count(request):
    """
    API: Get unread notification count
    URL: /notifications/api/admin/unread-count/
    """
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
        logger.error(f"Error in admin_unread_count: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def admin_notification_list(request):
    """
    API: Get admin notifications list
    URL: /notifications/api/admin/list/
    ✅ FIXED: Correct timezone handling + variable name
    """
    try:
        limit = min(int(request.GET.get('limit', 20)), 100)
        
        notifications = Notification.objects.filter(
            user=request.user
        ).select_related('user', 'content_type').order_by('-created_at')[:limit]
        
        notifications_data = []
        for notif in notifications:
            if should_show_notification(request.user, notif):
                url = get_notification_url(notif)
                
                # ✅ FIX: Use timezone.localtime() + correct variable name 'notif'
                created_at_local = timezone.localtime(notif.created_at)
                
                data = {
                    'id': notif.id,
                    'title': notif.title,
                    'message': notif.message,
                    'notification_type': notif.notification_type,
                    'is_read': notif.is_read,
                    'created_at': created_at_local.strftime('%b %d, %Y %I:%M %p'),  # ✅ FIXED
                    'link': url,
                    'object_id': notif.object_id,
                }
                notifications_data.append(data)
        
        return JsonResponse({
            'success': True,
            'notifications': notifications_data,
            'count': len(notifications_data)
        })
        
    except Exception as e:
        logger.error(f"Error in admin_notification_list: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def admin_mark_as_read(request, notification_id):
    """
    API: Mark notification as read
    URL: /notifications/api/admin/<id>/read/
    ✅ Sends WebSocket update
    """
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            
            # Get updated count
            unread_count = Notification.objects.filter(
                user=request.user,
                is_read=False
            ).count()
            
            # ✅ Send WebSocket update
            send_websocket_update(request.user.id, unread_count)
            
            return JsonResponse({
                'success': True,
                'unread_count': unread_count,
                'message': 'Notification marked as read'
            })
        else:
            return JsonResponse({
                'success': True,
                'message': 'Already marked as read'
            })
        
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in admin_mark_as_read: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["POST"])
def admin_mark_all_as_read(request):
    """
    API: Mark all notifications as read
    URL: /notifications/api/admin/mark-all-read/
    ✅ Sends WebSocket update
    """
    try:
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        # ✅ Send WebSocket update
        send_websocket_update(request.user.id, 0)
        
        return JsonResponse({
            'success': True,
            'message': f'{count} notification(s) marked as read',
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error in admin_mark_all_as_read: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["DELETE", "POST"])
def admin_delete_notification(request, notification_id):
    """
    API: Delete a notification
    URL: /notifications/api/admin/<id>/delete/
    ✅ Sends WebSocket update if unread
    """
    try:
        notification = Notification.objects.get(
            id=notification_id,
            user=request.user
        )
        
        was_unread = not notification.is_read
        notification.delete()
        
        # Get updated count
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        # ✅ Send WebSocket if unread deleted
        if was_unread:
            send_websocket_update(request.user.id, unread_count)
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted',
            'unread_count': unread_count
        })
        
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in admin_delete_notification: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)