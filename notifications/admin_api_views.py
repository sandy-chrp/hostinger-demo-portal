from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from .models import Notification
from accounts.models import CustomUser as User

@staff_member_required
@require_http_methods(["GET"])
def admin_notification_list(request):
    """Get admin notifications list"""
    limit = int(request.GET.get('limit', 20))
    
    # ✅ FIXED: Change recipient to user
    notifications = Notification.objects.filter(
        user__is_staff=True
    ).select_related('user').order_by('-created_at')[:limit]
    
    notifications_data = []
    for notif in notifications:
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
            'email_sent': notif.email_sent if hasattr(notif, 'email_sent') else False,
            # ✅ ADD: User information
            'user_name': notif.user.get_full_name() if notif.user else 'N/A',
            'user_email': notif.user.email if notif.user else 'N/A',
        }
        notifications_data.append(data)
    
    return JsonResponse({
        'success': True,
        'notifications': notifications_data
    })


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


@staff_member_required
@require_http_methods(["GET"])
def admin_unread_count(request):
    """Get unread notification count for admin"""
    # ✅ FIXED: Change recipient to user
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).count()
    
    return JsonResponse({
        'success': True,
        'count': count
    })


@staff_member_required
@require_http_methods(["POST"])
def admin_mark_as_read(request, notification_id):
    """Mark a notification as read"""
    try:
        # ✅ FIXED: Change recipient to user
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


@staff_member_required
@require_http_methods(["POST"])
def admin_mark_all_as_read(request):
    """Mark all notifications as read for admin"""
    # ✅ FIXED: Change recipient to user
    count = Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)
    
    return JsonResponse({
        'success': True,
        'message': f'{count} notifications marked as read',
        'count': count
    })


@staff_member_required
@require_http_methods(["DELETE", "POST"])
def admin_delete_notification(request, notification_id):
    """Delete a notification"""
    try:
        # ✅ FIXED: Change recipient to user
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