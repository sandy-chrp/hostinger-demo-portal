from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.apps import apps
import logging

logger = logging.getLogger(__name__)


# Import here to avoid circular imports
def get_notification_service():
    """Lazy import to avoid circular dependency"""
    from .services import NotificationService
    return NotificationService


# ============================================
# User Signals
# ============================================

@receiver(pre_save, sender='accounts.CustomUser')
def store_old_user_approval(sender, instance, **kwargs):
    """Store old approval status before save"""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_is_approved = old.is_approved
        except sender.DoesNotExist:
            instance._old_is_approved = False


@receiver(post_save, sender='accounts.CustomUser')
def notify_user_approval(sender, instance, created, **kwargs):
    """Notify user when account approved"""
    if not created and instance.is_approved:
        if hasattr(instance, '_old_is_approved'):
            if not instance._old_is_approved and instance.is_approved:
                NotificationService = get_notification_service()
                NotificationService.notify_account_approved(instance)
                logger.info(f"Sent approval notification to {instance.email}")


@receiver(post_save, sender='accounts.CustomUser')
def notify_admin_new_customer(sender, instance, created, **kwargs):
    """Notify admins about new customer"""
    if created and not instance.is_staff:
        NotificationService = get_notification_service()
        NotificationService.notify_admin_new_customer(instance)


# ============================================
# Demo Request Signals
# ============================================

@receiver(pre_save, sender='demos.DemoRequest')
def store_old_demo_request_status(sender, instance, **kwargs):
    """Store old status before save"""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = old.status
            instance._old_date = old.confirmed_date or old.requested_date
            instance._old_slot = old.confirmed_time_slot or old.requested_time_slot
        except sender.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender='demos.DemoRequest')
def notify_demo_request_changes(sender, instance, created, **kwargs):
    """
    Notify on demo request status changes ONLY
    ✅ FIXED: New requests handled by demos/signals.py
    ✅ FIXED: Confirmation handled by view
    ✅ This only handles reschedule
    """
    NotificationService = get_notification_service()
    
    # ✅ REMOVED: New request notification (handled by demos/signals.py)
    # Only handle status changes for existing requests
    if created:
        return  # Skip new requests - handled by demos app signal
    
    # Notify customer on status change
    if hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.status
        
        if old_status != new_status:
            # ✅ REMOVED: Confirmation notification
            # Handled by view via create_demo_confirmation_notification()
            # View sends both email AND in-app notification
            
            # Only handle reschedule in signal
            if new_status == 'rescheduled':
                NotificationService.notify_demo_request_rescheduled(
                    instance,
                    instance._old_date,
                    instance._old_slot
                )


# ============================================
# Enquiry Signals
# ============================================

@receiver(pre_save, sender='enquiries.BusinessEnquiry')
def store_old_enquiry_status(sender, instance, **kwargs):
    """Store old status before save"""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except sender.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender='enquiries.BusinessEnquiry')
def notify_enquiry_changes(sender, instance, created, **kwargs):
    """Notify on enquiry changes"""
    NotificationService = get_notification_service()

    # Confirmation on new enquiry
    if created:
        NotificationService.notify_enquiry_received(instance)
        NotificationService.notify_admin_new_enquiry(instance)
        return

    # ✅ REMOVED: notify_enquiry_response on status='answered'
    # Response notifications now handled by EnquiryResponse signal
    # which fires when admin actually adds a response (better UX)
    # This prevents duplicate notifications


# ============================================
# Demo Signals
# ============================================

@receiver(post_save, sender='demos.Demo')
def notify_new_demo(sender, instance, created, **kwargs):
    """Notify users about new demo"""
    if created and instance.is_active:
        NotificationService = get_notification_service()
        NotificationService.notify_new_demo_available(instance)
        logger.info(f"Sent new demo notifications for {instance.title}")


@receiver(pre_save, sender='accounts.CustomUser')
def store_old_block_status(sender, instance, **kwargs):
    """Store old block status"""
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_is_blocked = old.is_blocked if hasattr(old, 'is_blocked') else False
        except sender.DoesNotExist:
            instance._old_is_blocked = False


@receiver(post_save, sender='accounts.CustomUser')
def notify_block_status_change(sender, instance, created, **kwargs):
    """Notify on block/unblock"""
    if not created and not instance.is_staff:
        if hasattr(instance, '_old_is_blocked'):
            old_blocked = instance._old_is_blocked
            new_blocked = instance.is_blocked if hasattr(instance, 'is_blocked') else False

            if old_blocked != new_blocked:
                from notifications.services import NotificationService
                if new_blocked:
                    NotificationService.notify_account_blocked(instance)
                else:
                    NotificationService.notify_account_unblocked(instance)


# ============================================
# Demo Request Rejection Signal
# ============================================

@receiver(post_save, sender='demos.DemoRequest')
def notify_demo_rejection(sender, instance, created, **kwargs):
    """Notify on demo request rejection"""
    if not created:
        if hasattr(instance, '_old_status'):
            old_status = instance._old_status
            new_status = instance.status

            if old_status != new_status and new_status == 'rejected':
                from notifications.services import NotificationService
                reason = instance.admin_notes or 'Not available for requested date'
                NotificationService.notify_demo_request_rejected(instance, reason)


# ============================================
# Enquiry Status Change Signal
# ============================================

@receiver(post_save, sender='enquiries.BusinessEnquiry')
def notify_enquiry_status_change(sender, instance, created, **kwargs):
    """Notify on enquiry status changes (all statuses)"""
    if not created:
        if hasattr(instance, '_old_status'):
            old_status = instance._old_status
            new_status = instance.status

            if old_status != new_status:
                from notifications.services import NotificationService

                # Send notification for any status change
                if new_status in ['in_progress', 'pending']:
                    NotificationService.notify_enquiry_status_change(
                        instance, old_status, new_status
                    )


# ============================================
# Enquiry Response Signal (NEW)
# ============================================

@receiver(post_save, sender='enquiries.EnquiryResponse')
def notify_customer_on_enquiry_response(sender, instance, created, **kwargs):
    """
    ✅ NEW: Notify customer when admin responds to their enquiry
    """
    if not created:
        return
    
    # Skip internal notes
    if instance.is_internal_note:
        return
    
    try:
        from notifications.services import NotificationService
        from notifications.models import Notification
        
        enquiry = instance.enquiry
        customer = enquiry.user
        
        # Create notification for customer
        notification = Notification.objects.create(
            user=customer,
            title='Response to Your Enquiry',
            message=f'Your enquiry "{enquiry.enquiry_id}" has received a response from our team.',
            notification_type='enquiry_response',
            content_object=enquiry
        )
        
        # ✅ Push via WebSocket
        NotificationService.push_to_websocket(customer, notification)
        
        logger.info(f"✅ Enquiry response notification sent to {customer.email}")
        
    except Exception as e:
        logger.error(f"❌ Error sending enquiry response notification: {e}")
        import traceback
        traceback.print_exc()

