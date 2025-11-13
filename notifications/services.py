# notifications/services.py - ENHANCED WITH WEBSOCKET PUSH
"""
Notification Service - UPDATED WITH WEBSOCKET SUPPORT
✅ Backward compatible - existing code will work
✅ WebSocket push added to all notification methods
✅ Permission-based filtering maintained
✅ No breaking changes
"""

from django.utils import timezone
from django.template import Template, Context
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from .models import Notification, NotificationTemplate
import logging

# ✅ NEW: WebSocket imports
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


class NotificationService:
    """Service class for all notification operations"""
    
    # ============================================
    # NEW: WebSocket Helper Methods
    # ============================================
    
    @staticmethod
    def push_to_websocket(user, notification):
        """
        ✅ NEW METHOD: Push notification via WebSocket
        Falls back gracefully if WebSocket not available
        
        Args:
            user: User object
            notification: Notification object
        """
        try:
            channel_layer = get_channel_layer()
            
            if not channel_layer:
                logger.debug("Channel layer not configured, skipping WebSocket push")
                return
            
            # Prepare notification data
            notification_data = {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'notification_type': notification.notification_type,
                'is_read': notification.is_read,
                'created_at': notification.created_at.strftime('%b %d, %Y %I:%M %p'),
                'link': NotificationService._get_notification_link(notification),
                'object_id': notification.object_id,
            }
            
            # Send to user's personal channel
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}',
                {
                    'type': 'notification_message',
                    'notification': notification_data
                }
            )
            
            # Update unread count
            unread_count = Notification.objects.filter(
                user=user,
                is_read=False
            ).count()
            
            async_to_sync(channel_layer.group_send)(
                f'user_{user.id}',
                {
                    'type': 'unread_count_update',
                    'count': unread_count
                }
            )
            
            logger.info(f"✅ WebSocket push sent to user {user.id}")
            
        except Exception as e:
            logger.error(f"❌ WebSocket push failed (non-critical): {e}")
            # Non-critical error - notification still created in DB
    
    @staticmethod
    def _get_notification_link(notification):
        """Generate notification link"""
        obj_id = notification.object_id
        notif_type = notification.notification_type
        
        from django.urls import reverse
        
        try:
            link_map = {
                'new_customer': reverse('core:admin_customer_detail', kwargs={'customer_id': obj_id}) if obj_id else reverse('core:admin_users'),
                'demo_request': reverse('core:admin_demo_request_detail', kwargs={'request_id': obj_id}) if obj_id else reverse('core:admin_demo_requests'),
                'demo_cancellation': reverse('core:admin_demo_request_detail', kwargs={'request_id': obj_id}) if obj_id else reverse('core:admin_demo_requests') + '?status=cancelled',
                'enquiry': reverse('core:admin_enquiry_detail', kwargs={'enquiry_id': obj_id}) if obj_id else reverse('core:admin_enquiries'),
                'milestone': reverse('core:admin_dashboard'),
                'system_announcement': reverse('notifications:admin_notifications'),
            }
            return link_map.get(notif_type, reverse('notifications:admin_notifications'))
        except:
            return '/notifications/admin/'
    
    # ============================================
    # EXISTING METHODS (UNCHANGED)
    # ============================================
    
    @staticmethod
    def send_email_notification(user, subject, template_name, context=None):
        """Send HTML email notification"""
        if not user.email:
            logger.warning(f"User {user.id} has no email address")
            return False
        
        try:
            email_context = {
                'user': user,
                'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
                'site_name': getattr(settings, 'SITE_NAME', 'Demo Portal'),
            }
            if context:
                email_context.update(context)
            
            html_content = render_to_string(
                f'emails/{template_name}.html',
                email_context
            )
            
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@demoportal.com'),
                to=[user.email]
            )
            
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            
            logger.info(f"✅ Email sent to {user.email}: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error sending email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def create_notification(user, notification_type, context_data=None, related_object=None, send_email=True):
        """Create notification from template"""
        try:
            template = NotificationTemplate.objects.filter(
                notification_type=notification_type,
                is_active=True
            ).first()
            
            if not template:
                logger.warning(f"No template found for {notification_type}")
                return None
            
            context = Context(context_data or {})
            title = Template(template.title_template).render(context)
            message = Template(template.message_template).render(context)
            
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                content_object=related_object
            )
            
            # ✅ NEW: Push via WebSocket
            NotificationService.push_to_websocket(user, notification)
            
            if send_email and template.send_email:
                NotificationService._send_email_from_template(user, template, context_data, notification)
            
            logger.info(f"✅ Created notification {notification.id} for {user.email}")
            return notification
            
        except Exception as e:
            logger.error(f"❌ Error creating notification: {e}")
            return None
    
    @staticmethod
    def _send_email_from_template(user, template, context_data, notification):
        """Internal method to send email from template"""
        try:
            context = Context(context_data or {})
            subject = Template(template.email_subject).render(context) if template.email_subject else template.title_template
            body = Template(template.email_body).render(context) if template.email_body else template.message_template
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=strip_tags(body),
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@demoportal.com'),
                to=[user.email]
            )
            
            email.attach_alternative(body, "text/html")
            email.send(fail_silently=False)
            
            notification.email_sent = True
            notification.email_sent_at = timezone.now()
            notification.save(update_fields=['email_sent', 'email_sent_at'])
            
            logger.info(f"✅ Email sent to {user.email}")
            
        except Exception as e:
            notification.email_error = str(e)
            notification.save(update_fields=['email_error'])
            logger.error(f"❌ Email error: {e}")
    
    # ============================================
    # Customer Notification Methods (ENHANCED WITH WEBSOCKET)
    # ============================================
    
    @staticmethod
    def notify_account_approved(user, send_email=True):
        """Customer account approved"""
        notification = Notification.objects.create(
            user=user,
            title='Account Approved',
            message='Your account has been approved! You now have full access to our demo library.',
            notification_type='account_approved'
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(user, notification)
        
        if send_email:
            NotificationService.send_email_notification(
                user=user,
                subject='🎉 Your Demo Portal Account is Approved!',
                template_name='account_approved'
            )
        
        return notification
    
    @staticmethod
    def notify_account_blocked(user, reason='Policy violation', send_email=True):
        """Account blocked notification"""
        notification = Notification.objects.create(
            user=user,
            title='Account Blocked',
            message=f'Your account has been blocked. Reason: {reason}',
            notification_type='account_blocked'
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(user, notification)
        
        if send_email:
            context = {
                'reason': reason,
                'blocked_date': timezone.now().strftime('%B %d, %Y'),
            }
            NotificationService.send_email_notification(
                user=user,
                subject='Account Status Update - Demo Portal',
                template_name='account_blocked',
                context=context
            )
        
        return notification
    
    @staticmethod
    def notify_account_unblocked(user, send_email=True):
        """Account unblocked notification"""
        notification = Notification.objects.create(
            user=user,
            title='Account Reactivated',
            message='Good news! Your Demo Portal account has been reactivated. You can now access all features.',
            notification_type='account_unblocked'
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(user, notification)
        
        if send_email:
            from django.urls import reverse
            site_url = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')
            login_url = f"{site_url}/auth/signin/"
            
            context = {
                'login_url': login_url,
                'reactivation_date': timezone.now().strftime('%B %d, %Y at %I:%M %p'),
            }
            NotificationService.send_email_notification(
                user=user,
                subject='✅ Account Reactivated - Demo Portal',
                template_name='account_unblocked',
                context=context
            )
        
        return notification

    @staticmethod
    def notify_demo_request_confirmed(demo_request, send_email=True):
        """Demo request confirmed"""
        
        confirmed_date_str = demo_request.confirmed_date.strftime('%B %d, %Y')
        confirmed_time_str = f"{demo_request.confirmed_time_slot.start_time.strftime('%I:%M %p')} - {demo_request.confirmed_time_slot.end_time.strftime('%I:%M %p')}"
        
        try:
            template = NotificationTemplate.objects.get(
                notification_type='demo_confirmation',
                is_active=True
            )
            
            context = Context({
                'demo_title': demo_request.demo.title,
                'confirmed_date': confirmed_date_str,
                'confirmed_time': confirmed_time_str,
            })
            
            notification_title = Template(template.title_template).render(context)
            notification_message = Template(template.message_template).render(context)
            
        except NotificationTemplate.DoesNotExist:
            notification_title = 'Demo Request Confirmed'
            notification_message = f'Your demo request for "{demo_request.demo.title}" has been confirmed for {confirmed_date_str} at {confirmed_time_str}.'
        
        notification = Notification.objects.create(
            user=demo_request.user,
            title=notification_title,
            message=notification_message,
            notification_type='demo_confirmation',
            content_object=demo_request
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(demo_request.user, notification)
        
        if send_email:
            NotificationService.send_email_notification(
                user=demo_request.user,
                subject=notification_title,
                template_name='demo_confirmed',
                context={
                    'demo_request': demo_request,
                    'year': 2025,
                }
            )
        
        return notification

    @staticmethod
    def notify_demo_request_rejected(demo_request, reason='Not available', send_email=True):
        """Demo request rejected"""
        notification = Notification.objects.create(
            user=demo_request.user,
            title='Demo Request Rejected',
            message=f'Your demo request for "{demo_request.demo.title}" has been rejected. Reason: {reason}',
            notification_type='demo_rejection',
            content_object=demo_request
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(demo_request.user, notification)
        
        if send_email:
            context = {
                'demo_title': demo_request.demo.title,
                'reason': reason,
                'request_date': demo_request.created_at.strftime('%B %d, %Y'),
            }
            NotificationService.send_email_notification(
                user=demo_request.user,
                subject=f'Demo Request Update - {demo_request.demo.title}',
                template_name='demo_rejected',
                context=context
            )
        
        return notification

    @staticmethod
    def notify_demo_request_rescheduled(demo_request, old_date, old_slot, send_email=True):
        """Demo request rescheduled"""
        old_date_str = old_date.strftime('%B %d, %Y') if old_date else 'Previous date'
        new_date_str = demo_request.requested_date.strftime('%B %d, %Y')
        
        old_time_str = f"{old_slot.start_time.strftime('%I:%M %p')} - {old_slot.end_time.strftime('%I:%M %p')}" if old_slot else 'Previous time'
        new_time_str = f"{demo_request.requested_time_slot.start_time.strftime('%I:%M %p')} - {demo_request.requested_time_slot.end_time.strftime('%I:%M %p')}"
        
        notification = Notification.objects.create(
            user=demo_request.user,
            title='Demo Request Rescheduled',
            message=f'Your demo for "{demo_request.demo.title}" has been rescheduled to {new_date_str} at {new_time_str}.',
            notification_type='demo_reschedule',
            content_object=demo_request
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(demo_request.user, notification)
        
        if send_email:
            reschedule_reason = ''
            if demo_request.admin_notes:
                if "Rescheduled:" in demo_request.admin_notes:
                    reason_start = demo_request.admin_notes.find("Rescheduled:") + len("Rescheduled:")
                    reason_end = demo_request.admin_notes.find("\n", reason_start)
                    if reason_end == -1:
                        reason_end = len(demo_request.admin_notes)
                    reschedule_reason = demo_request.admin_notes[reason_start:reason_end].strip()
            
            context = {
                'demo_request': demo_request,
                'old_date': old_date_str,
                'old_time': old_time_str,
                'new_date': new_date_str,
                'new_time': new_time_str,
                'reschedule_reason': reschedule_reason or 'Schedule adjustment',
                'demo_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/customer/demo-requests/{demo_request.id}/",
                'year': timezone.now().year,
            }
            
            NotificationService.send_email_notification(
                user=demo_request.user,
                subject=f'Demo Rescheduled - {demo_request.demo.title}',
                template_name='demo_rescheduled',
                context=context
            )
        
        return notification

    @staticmethod
    def notify_demo_request_cancelled(demo_request, reason='', send_email=True):
        """Demo request cancelled"""
        notification = Notification.objects.create(
            user=demo_request.user,
            title='Demo Request Cancelled',
            message=f'Your demo request for "{demo_request.demo.title}" has been cancelled. {reason if reason else ""}',
            notification_type='demo_cancellation',
            content_object=demo_request
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(demo_request.user, notification)
        
        if send_email:
            context = {
                'demo_title': demo_request.demo.title,
                'reason': reason or 'No reason provided',
            }
            NotificationService.send_email_notification(
                user=demo_request.user,
                subject=f'Demo Cancelled - {demo_request.demo.title}',
                template_name='demo_cancelled',
                context=context
            )
        
        return notification
    
    @staticmethod
    def notify_enquiry_received(enquiry, send_email=True):
        """Enquiry received confirmation"""
        enquiry_id = enquiry.enquiry_id if hasattr(enquiry, "enquiry_id") else enquiry.id
        
        notification = Notification.objects.create(
            user=enquiry.user,
            title='Enquiry Received',
            message=f'We have received your enquiry (ID: {enquiry_id}). Our team will respond within 24-48 hours.',
            notification_type='enquiry_received',
            content_object=enquiry
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(enquiry.user, notification)
        
        if send_email:
            context = {
                'enquiry_id': enquiry_id,
                'subject': getattr(enquiry, 'subject', 'Business Enquiry'),
                'enquiry_date': enquiry.created_at.strftime('%B %d, %Y'),
            }
            NotificationService.send_email_notification(
                user=enquiry.user,
                subject='✓ Enquiry Received - We\'ll Get Back to You Soon',
                template_name='enquiry_received',
                context=context
            )
        
        return notification
    
    @staticmethod
    def notify_enquiry_response(enquiry, response_summary='', send_email=True):
        """Enquiry answered"""
        notification = Notification.objects.create(
            user=enquiry.user,
            title='Enquiry Response Received',
            message='Your enquiry has been answered. Please check your enquiry dashboard for details.',
            notification_type='enquiry_response',
            content_object=enquiry
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(enquiry.user, notification)
        
        if send_email:
            context = {
                'enquiry_id': enquiry.enquiry_id if hasattr(enquiry, 'enquiry_id') else enquiry.id,
                'response_summary': response_summary[:200] if response_summary else 'Your enquiry has been answered.',
            }
            NotificationService.send_email_notification(
                user=enquiry.user,
                subject='✓ Response to Your Enquiry',
                template_name='enquiry_response',
                context=context
            )
        
        return notification
    
    @staticmethod
    def notify_enquiry_status_change(enquiry, old_status, new_status, send_email=True):
        """Enquiry status changed"""
        notification = Notification.objects.create(
            user=enquiry.user,
            title='Enquiry Status Updated',
            message=f'Your enquiry status has been updated from "{old_status}" to "{new_status}".',
            notification_type='enquiry_status',
            content_object=enquiry
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(enquiry.user, notification)
        
        if send_email:
            context = {
                'enquiry_id': enquiry.enquiry_id if hasattr(enquiry, 'enquiry_id') else enquiry.id,
                'old_status': old_status.upper(),
                'new_status': new_status.upper(),
            }
            NotificationService.send_email_notification(
                user=enquiry.user,
                subject=f'Enquiry Status Update - {new_status.upper()}',
                template_name='enquiry_status_update',
                context=context
            )
        
        return notification
    
    # ============================================
    # Admin Notification Methods (WITH PERMISSION CHECK + WEBSOCKET)
    # ============================================
    
    @staticmethod
    def notify_admin_new_customer(customer, send_email=True):
        """Notify admins about new customer registration - WITH PERMISSIONS"""
        from accounts.models import CustomUser
        
        admins = CustomUser.objects.filter(is_staff=True, is_active=True)
        
        notifications = []
        for admin in admins:
            # ✅ PERMISSION CHECK
            if not admin.has_permission('view_customers'):
                continue
                
            notification = Notification.objects.create(
                user=admin,
                title='New Customer Registration',
                message=f'{customer.get_full_name()} ({customer.email}) has registered and needs approval.',
                notification_type='new_customer',
                content_object=customer
            )
            notifications.append(notification)
            
            # ✅ WebSocket push
            NotificationService.push_to_websocket(admin, notification)
            
            if send_email:
                context = {
                    'customer_name': customer.get_full_name(),
                    'customer_email': customer.email,
                    'customer_company': getattr(customer, 'company_name', 'N/A'),
                    'registration_date': customer.date_joined.strftime('%B %d, %Y at %I:%M %p'),
                }
                NotificationService.send_email_notification(
                    user=admin,
                    subject=f'🆕 New Customer Registration - {customer.get_full_name()}',
                    template_name='admin_new_customer',
                    context=context
                )
        
        logger.info(f"✅ Sent new customer notifications to {len(notifications)} admins")
        return notifications

    @staticmethod
    def notify_admin_new_demo_request(demo_request, send_email=True):
            """
            Notify about NEW demo request
            ✅ FIXED: Only SUPERADMIN gets notification
            ✅ Regular staff will get notification when ASSIGNED via notify_employee_demo_assigned()
            """
            from accounts.models import CustomUser
            
            customer_name = demo_request.user.get_full_name()
            demo_title = demo_request.demo.title
            requested_date_str = demo_request.requested_date.strftime('%B %d, %Y')
            requested_time_str = f"{demo_request.requested_time_slot.start_time.strftime('%I:%M %p')} - {demo_request.requested_time_slot.end_time.strftime('%I:%M %p')}"
            
            # ✅ FIX: Only notify superadmin for NEW unassigned requests
            # Regular staff will be notified when demo is ASSIGNED to them
            admins = CustomUser.objects.filter(
                is_staff=True, 
                is_active=True,
                is_superuser=True  # ✅ ONLY SUPERADMIN
            )
            
            notifications = []
            for admin in admins:
                try:
                    template = NotificationTemplate.objects.get(
                        notification_type='demo_request',
                        is_active=True
                    )
                    
                    context = Context({
                        'customer_name': customer_name,
                        'demo_title': demo_title,
                        'requested_date': requested_date_str,
                        'requested_time': requested_time_str,
                    })
                    
                    notification_title = Template(template.title_template).render(context)
                    notification_message = Template(template.message_template).render(context)
                    
                except NotificationTemplate.DoesNotExist:
                    notification_title = 'New Demo Request'
                    notification_message = f'{customer_name} requested a demo for "{demo_title}" on {requested_date_str} at {requested_time_str}.'
                
                notification = Notification.objects.create(
                    user=admin,
                    title=notification_title,
                    message=notification_message,
                    notification_type='demo_request',
                    content_object=demo_request
                )
                notifications.append(notification)
                
                # ✅ WebSocket push
                NotificationService.push_to_websocket(admin, notification)
                
                if send_email:
                    NotificationService.send_email_notification(
                        user=admin,
                        subject=notification_title,
                        template_name='admin_new_demo_request',
                        context={
                            'customer_name': customer_name,
                            'demo_title': demo_title,
                            'requested_date': requested_date_str,
                            'requested_time': requested_time_str,
                        }
                    )
            
            logger.info(f"✅ Sent demo request notifications to {len(notifications)} superadmin(s)")
            return notifications

    @staticmethod
    def notify_admin_new_enquiry(enquiry, send_email=True):
        """Notify admins about new enquiry - WITH PERMISSIONS"""
        from accounts.models import CustomUser
        
        admins = CustomUser.objects.filter(is_staff=True, is_active=True)
        enquiry_id = enquiry.enquiry_id if hasattr(enquiry, 'enquiry_id') else enquiry.id
        
        notifications = []
        for admin in admins:
            # ✅ PERMISSION CHECK
            if not admin.has_permission('view_enquiries'):
                continue
                
            notification = Notification.objects.create(
                user=admin,
                title='New Business Enquiry',
                message=f'New enquiry received from {enquiry.user.get_full_name()} (ID: {enquiry_id})',
                notification_type='enquiry',
                content_object=enquiry
            )
            notifications.append(notification)
            
            # ✅ WebSocket push
            NotificationService.push_to_websocket(admin, notification)
            
            if send_email:
                context = {
                    'customer_name': enquiry.user.get_full_name(),
                    'enquiry_id': enquiry_id,
                    'subject': getattr(enquiry, 'subject', 'Business Enquiry'),
                    'enquiry_date': enquiry.created_at.strftime('%B %d, %Y'),
                }
                NotificationService.send_email_notification(
                    user=admin,
                    subject=f'💬 New Enquiry - {enquiry_id}',
                    template_name='admin_new_enquiry',
                    context=context
                )
        
        logger.info(f"✅ Sent enquiry notifications to {len(notifications)} admins")
        return notifications
    
    @staticmethod
    def notify_admin_demo_request_cancelled(demo_request, cancelled_by_customer=True, send_email=True):
        """Notify admins when demo request is cancelled - WITH PERMISSIONS"""
        from accounts.models import CustomUser
        
        admins = CustomUser.objects.filter(is_staff=True, is_active=True)
        
        cancellation_reason = demo_request.get_cancellation_reason_display() if demo_request.cancellation_reason else 'No reason provided'
        cancellation_details = demo_request.cancellation_details or 'No additional details'
        
        notifications = []
        for admin in admins:
            # ✅ PERMISSION CHECK
            if not admin.has_permission('view_demo_requests'):
                continue
                
            if cancelled_by_customer:
                title = 'Demo Request Cancelled by Customer'
                message = f'{demo_request.user.get_full_name()} cancelled their demo request for "{demo_request.demo.title}". Reason: {cancellation_reason}'
            else:
                title = 'Demo Request Cancelled'
                message = f'Demo request for "{demo_request.demo.title}" by {demo_request.user.get_full_name()} has been cancelled.'
            
            notification = Notification.objects.create(
                user=admin,
                title=title,
                message=message,
                notification_type='demo_cancellation',
                content_object=demo_request
            )
            notifications.append(notification)
            
            # ✅ WebSocket push
            NotificationService.push_to_websocket(admin, notification)
            
            if send_email:
                context = {
                    'admin_name': admin.get_full_name() or 'Admin',
                    'customer_name': demo_request.user.get_full_name(),
                    'customer_email': demo_request.user.email,
                    'demo_title': demo_request.demo.title,
                    'request_id': demo_request.id,
                    'requested_date': demo_request.requested_date.strftime('%B %d, %Y'),
                    'requested_time': demo_request.requested_time_slot.start_time.strftime('%I:%M %p'),
                    'cancellation_reason': cancellation_reason,
                    'cancellation_details': cancellation_details,
                    'cancelled_at': demo_request.cancelled_at.strftime('%B %d, %Y at %I:%M %p') if demo_request.cancelled_at else 'Recently',
                    'cancelled_by': 'Customer' if cancelled_by_customer else 'Admin',
                }
                
                NotificationService.send_email_notification(
                    user=admin,
                    subject=f'🚫 Demo Cancelled - {demo_request.demo.title}',
                    template_name='admin_demo_cancelled',
                    context=context
                )
        
        logger.info(f"✅ Sent cancellation notifications to {len(notifications)} admins")
        return notifications

    # ============================================
    # Remaining methods (unchanged)
    # ============================================
    
    @staticmethod
    def notify_employee_demo_assigned(demo_request, employee, send_email=True):
        """Send notification to employee when demo is assigned"""
        try:
            employee_name = employee.get_full_name()
            demo_title = demo_request.demo.title
            customer_name = demo_request.user.get_full_name()
            customer_email = demo_request.user.email
            customer_phone = getattr(demo_request.user, 'mobile', None) or 'Not provided'
            requested_date_str = demo_request.requested_date.strftime('%B %d, %Y')
            requested_time_str = f"{demo_request.requested_time_slot.start_time.strftime('%I:%M %p')} - {demo_request.requested_time_slot.end_time.strftime('%I:%M %p')}"
            demo_type_str = demo_request.demo.get_demo_type_display()
            customer_notes_str = demo_request.notes or 'No additional notes provided'
            
            try:
                template = NotificationTemplate.objects.get(
                    notification_type='demo_assigned_to_employee',
                    is_active=True
                )
                
                context = Context({
                    'employee_name': employee_name,
                    'demo_title': demo_title,
                    'customer_name': customer_name,
                    'customer_email': customer_email,
                    'customer_phone': customer_phone,
                    'requested_date': requested_date_str,
                    'requested_time': requested_time_str,
                    'demo_type': demo_type_str,
                    'customer_notes': customer_notes_str,
                })
                
                notification_title = Template(template.title_template).render(context)
                notification_message = Template(template.message_template).render(context)
                
            except NotificationTemplate.DoesNotExist:
                notification_title = f"New Demo Assigned: {demo_title}"
                notification_message = f"You have been assigned to conduct a demo for {customer_name}.\n\nDemo: {demo_title}\nDate: {requested_date_str}\nTime: {requested_time_str}\n\nCustomer: {customer_name} ({customer_email})\n\nPlease review the details and prepare accordingly."
            
            from django.contrib.contenttypes.models import ContentType
            from demos.models import DemoRequest
            
            notification = Notification.objects.create(
                user=employee,
                notification_type='demo_assigned_to_employee',
                title=notification_title,
                message=notification_message,
                content_type=ContentType.objects.get_for_model(DemoRequest),
                object_id=demo_request.id
            )
            
            # ✅ WebSocket push
            NotificationService.push_to_websocket(employee, notification)
            
            if send_email:
                from django.core.mail import send_mail
                
                email_body = f"""
Dear {employee_name},

{notification_message}

Demo Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Demo: {demo_title}
- Type: {demo_type_str}
- Date: {requested_date_str}
- Time: {requested_time_str}

Customer Information:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Name: {customer_name}
- Email: {customer_email}
- Phone: {customer_phone}

Additional Notes:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{customer_notes_str}

Please log in to the admin portal to view full details.

Best regards,
Demo Management System
                """
                
                send_mail(
                    subject=notification_title,
                    message=email_body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[employee.email],
                    fail_silently=False,
                )
            
            return notification
            
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return None

    @staticmethod
    def notify_employee_demo_unassigned(demo_request, employee, send_email=True):
        """Notify employee when demo assignment is removed"""
        notification = Notification.objects.create(
            user=employee,
            title='Demo Assignment Removed',
            message=f'Your assignment for demo "{demo_request.demo.title}" (Customer: {demo_request.user.get_full_name()}) has been removed.',
            notification_type='demo_request',
            content_object=demo_request
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(employee, notification)
        
        if send_email:
            context = {
                'employee_name': employee.get_full_name(),
                'demo_title': demo_request.demo.title,
                'customer_name': demo_request.user.get_full_name(),
            }
            
            NotificationService.send_email_notification(
                user=employee,
                subject=f'Demo Assignment Removed - {demo_request.demo.title}',
                template_name='employee_demo_unassigned',
                context=context
            )
        
        return notification
    
    @staticmethod
    def send_custom_notification(user, title, message, notification_type='system_announcement', link=None, send_email=False, email_subject=None):
        """Send a custom notification"""
        notification = Notification.objects.create(
            user=user,
            title=title,
            message=message,
            notification_type=notification_type
        )
        
        # ✅ WebSocket push
        NotificationService.push_to_websocket(user, notification)
        
        if send_email:
            context = {
                'title': title,
                'message': message,
                'link': link,
            }
            
            NotificationService.send_email_notification(
                user=user,
                subject=email_subject or title,
                template_name='custom_notification',
                context=context
            )
        
        return notification
    
    # ============================================
    # Utility Methods
    # ============================================
    
    @staticmethod
    def get_unread_count(user):
        """Get unread notification count"""
        try:
            return Notification.objects.filter(user=user, is_read=False).count()
        except Exception as e:
            logger.error(f"❌ Error getting unread count: {e}")
            return 0
    
    @staticmethod
    def mark_as_read(notification_id, user):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=['is_read', 'read_at'])
            return True
        except Notification.DoesNotExist:
            return False
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return False
    
    @staticmethod
    def mark_all_as_read(user):
        """Mark all notifications as read"""
        try:
            return Notification.objects.filter(
                user=user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return 0
    
    @staticmethod
    def get_recent_notifications(user, limit=10):
        """Get recent notifications"""
        try:
            return Notification.objects.filter(user=user).order_by('-created_at')[:limit]
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return []
    
    @staticmethod
    def delete_old_notifications(days=90):
        """Clean up old notifications"""
        try:
            from datetime import timedelta
            cutoff = timezone.now() - timedelta(days=days)
            count, _ = Notification.objects.filter(
                created_at__lt=cutoff,
                is_read=True
            ).delete()
            logger.info(f"✅ Deleted {count} old notifications")
            return count
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return 0