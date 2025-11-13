# demos/signals.py - COMPLETE WITH WEBSOCKET PUSH
"""
Demo-related signals
✅ File cleanup (existing)
✅ Notification triggers with WebSocket push (FIXED)
"""

from django.db.models.signals import pre_delete, pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import Demo, DemoLike, DemoFeedback, DemoRequest
import os
import shutil
from django.conf import settings
from notifications.services import NotificationService
import logging

logger = logging.getLogger(__name__)


# ============================================
# EXISTING: File Cleanup Signals
# ============================================

@receiver(pre_delete, sender=Demo)
def cleanup_demo_files(sender, instance, **kwargs):
    """Clean up extracted WebGL files when demo is deleted"""
    if instance.extracted_path:
        extract_dir = os.path.join(settings.MEDIA_ROOT, instance.extracted_path)
        if os.path.exists(extract_dir):
            try:
                shutil.rmtree(extract_dir)
            except Exception as e:
                print(f"Error cleaning up extracted files: {e}")


@receiver(pre_save, sender=Demo)
def cleanup_old_extracted_files(sender, instance, **kwargs):
    """Clean up old extracted files when WebGL file is changed"""
    if instance.pk:
        try:
            old_demo = Demo.objects.get(pk=instance.pk)
            if old_demo.webgl_file != instance.webgl_file and old_demo.extracted_path:
                extract_dir = os.path.join(settings.MEDIA_ROOT, old_demo.extracted_path)
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
        except Demo.DoesNotExist:
            pass


# ============================================
# NOTIFICATION SIGNALS WITH WEBSOCKET PUSH
# ============================================

@receiver(post_save, sender=DemoLike)
def notify_admin_on_demo_like(sender, instance, created, **kwargs):
    """
    ✅ FIXED: Notify superadmin when customer LIKES a demo
    Includes WebSocket push for real-time delivery
    """
    if not created:  # Only on NEW like
        return
    
    try:
        from accounts.models import CustomUser
        from notifications.models import Notification
        
        # Get all superadmins
        superadmins = CustomUser.objects.filter(
            is_staff=True,
            is_active=True,
            is_superuser=True
        )
        
        customer_name = instance.user.get_full_name()
        demo_title = instance.demo.title
        
        for admin in superadmins:
            # Create notification
            notification = Notification.objects.create(
                user=admin,
                title='Demo Liked by Customer',
                message=f'{customer_name} liked the demo "{demo_title}"',
                notification_type='demo_liked',
                content_object=instance.demo
            )
            
            # ✅ CRITICAL: Push via WebSocket for real-time delivery
            NotificationService.push_to_websocket(admin, notification)
            
            logger.info(f"✅ Demo LIKE notification sent to {admin.email} (ID: {notification.id})")
        
    except Exception as e:
        logger.error(f"❌ Error sending demo like notification: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_delete, sender=DemoLike)
def notify_admin_on_demo_unlike(sender, instance, **kwargs):
    """
    ✅ NEW: Notify superadmin when customer UNLIKES a demo (optional)
    """
    try:
        from accounts.models import CustomUser
        from notifications.models import Notification
        
        # Get all superadmins
        superadmins = CustomUser.objects.filter(
            is_staff=True,
            is_active=True,
            is_superuser=True
        )
        
        customer_name = instance.user.get_full_name()
        demo_title = instance.demo.title
        
        for admin in superadmins:
            # Create notification
            notification = Notification.objects.create(
                user=admin,
                title='Demo Unliked by Customer',
                message=f'{customer_name} unliked the demo "{demo_title}"',
                notification_type='demo_liked',  # Same type as like
                content_object=instance.demo
            )
            
            # ✅ Push via WebSocket for real-time delivery
            NotificationService.push_to_websocket(admin, notification)
            
            logger.info(f"✅ Demo UNLIKE notification sent to {admin.email} (ID: {notification.id})")
        
    except Exception as e:
        logger.error(f"❌ Error sending demo unlike notification: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=DemoFeedback)
def notify_admin_on_demo_feedback(sender, instance, created, **kwargs):
    """
    ✅ FIXED: Notify superadmin when customer submits demo feedback
    Includes WebSocket push for real-time delivery
    """
    if not created:  # Only on new feedback
        return
    
    try:
        from accounts.models import CustomUser
        from notifications.models import Notification
        
        # Get all superadmins
        superadmins = CustomUser.objects.filter(
            is_staff=True,
            is_active=True,
            is_superuser=True
        )
        
        customer_name = instance.user.get_full_name()
        demo_title = instance.demo.title
        rating = instance.rating if instance.rating else 'No rating'
        
        for admin in superadmins:
            # Create notification
            notification = Notification.objects.create(
                user=admin,
                title='New Demo Feedback',
                message=f'{customer_name} submitted feedback for "{demo_title}" (Rating: {rating})',
                notification_type='demo_feedback',
                content_object=instance.demo
            )
            
            # ✅ CRITICAL: Push via WebSocket for real-time delivery
            NotificationService.push_to_websocket(admin, notification)
            
            logger.info(f"✅ Demo feedback notification sent to {admin.email} (ID: {notification.id})")
        
    except Exception as e:
        logger.error(f"❌ Error sending demo feedback notification: {e}")
        import traceback
        traceback.print_exc()


@receiver(post_save, sender=DemoRequest)
def notify_admin_on_demo_request(sender, instance, created, **kwargs):
    """
    ✅ FIXED: Only trigger for NEW demo requests
    Status changes (like cancellation) are handled by views
    """
    if not created:  # Only on NEW request, not updates
        return
    
    # Skip if status is already cancelled (shouldn't happen, but safety check)
    if instance.status == 'cancelled':
        return
    
    try:
        # Use the existing notification service method
        # This already includes WebSocket push
        NotificationService.notify_admin_new_demo_request(instance, send_email=True)
        logger.info(f"✅ Demo request notification sent for: {instance.demo.title}")
        
    except Exception as e:
        logger.error(f"❌ Error sending demo request notification: {e}")
        import traceback
        traceback.print_exc()