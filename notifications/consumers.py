# notifications/consumers.py
"""
WebSocket Consumer for Real-time Notifications
Supports: Customer, Employee, Admin roles
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Notification
from django.urls import reverse
import logging

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Real-time notification consumer
    Handles WebSocket connections for all user roles
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.user = self.scope["user"]
        
        # Reject anonymous users
        if self.user.is_anonymous:
            logger.warning("❌ Anonymous user attempted WebSocket connection")
            await self.close()
            return
        
        # ============================================
        # ROLE-BASED GROUP ASSIGNMENT
        # ============================================
        
        # Personal channel for this user
        self.user_group_name = f'user_{self.user.id}'
        
        # Broadcast groups based on role
        self.broadcast_groups = []
        
        if self.user.is_staff:
            # Admin/Staff users
            self.broadcast_groups.append('all_admins')
            if self.user.is_superuser:
                self.broadcast_groups.append('super_admins')
            logger.info(f"✅ Admin connected: {self.user.email} (ID: {self.user.id})")
        
        if self.user.user_type == 'employee' and not self.user.is_superuser:
            # Regular employees (not super admins)
            self.broadcast_groups.append('all_employees')
            logger.info(f"✅ Employee connected: {self.user.email} (ID: {self.user.id})")
        
        if self.user.user_type == 'customer':
            # Customers
            self.broadcast_groups.append('all_customers')
            logger.info(f"✅ Customer connected: {self.user.email} (ID: {self.user.id})")
        
        # ============================================
        # JOIN CHANNEL GROUPS
        # ============================================
        
        # Join personal group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Join broadcast groups
        for group in self.broadcast_groups:
            await self.channel_layer.group_add(
                group,
                self.channel_name
            )
        
        # Accept connection
        await self.accept()
        
        # Send connection confirmation
        unread_count = await self.get_unread_count()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'user_id': self.user.id,
            'user_type': self.user.user_type,
            'is_staff': self.user.is_staff,
            'unread_count': unread_count,
            'groups': [self.user_group_name] + self.broadcast_groups,
            'message': '🔌 WebSocket connected successfully',
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(
            f"🔌 WebSocket connected: {self.user.email} "
            f"(Groups: {', '.join([self.user_group_name] + self.broadcast_groups)})"
        )
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'user_group_name'):
            # Leave personal group
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
            
            # Leave broadcast groups
            for group in self.broadcast_groups:
                await self.channel_layer.group_discard(
                    group,
                    self.channel_name
                )
            
            logger.info(
                f"🔌 WebSocket disconnected: {self.user.email} "
                f"(Code: {close_code})"
            )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket (from frontend)
        Supported actions:
        - mark_read: Mark single notification as read
        - mark_all_read: Mark all notifications as read
        - get_notifications: Fetch recent notifications
        - ping: Heartbeat check
        """
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                notification_id = data.get('notification_id')
                success = await self.mark_notification_read(notification_id)
                
                await self.send(text_data=json.dumps({
                    'type': 'mark_read_response',
                    'success': success,
                    'notification_id': notification_id,
                    'timestamp': timezone.now().isoformat()
                }))
                
                if success:
                    # Send updated unread count
                    unread_count = await self.get_unread_count()
                    await self.send(text_data=json.dumps({
                        'type': 'unread_count',
                        'count': unread_count
                    }))
            
            elif action == 'mark_all_read':
                count = await self.mark_all_read()
                
                await self.send(text_data=json.dumps({
                    'type': 'mark_all_read_response',
                    'success': True,
                    'count': count,
                    'timestamp': timezone.now().isoformat()
                }))
                
                # Send updated unread count (should be 0)
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': 0
                }))
            
            elif action == 'get_notifications':
                limit = data.get('limit', 10)
                notifications = await self.get_recent_notifications(limit)
                
                await self.send(text_data=json.dumps({
                    'type': 'notifications_list',
                    'notifications': notifications,
                    'count': len(notifications),
                    'timestamp': timezone.now().isoformat()
                }))
            
            elif action == 'ping':
                # Heartbeat response
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': timezone.now().isoformat()
                }))
            
            else:
                logger.warning(f"⚠️ Unknown action received: {action}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown action: {action}'
                }))
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON received: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"❌ Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Server error'
            }))
    
    # ============================================
    # GROUP MESSAGE HANDLERS (from Channel Layer)
    # ============================================
    
    async def notification_message(self, event):
        """
        Send notification to WebSocket
        Called when notification is pushed via channel layer
        """
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification'],
            'timestamp': timezone.now().isoformat()
        }))
        
        logger.info(f"📨 Notification sent to {self.user.email}: {event['notification']['title']}")
    
    async def unread_count_update(self, event):
        """Update unread count"""
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': event['count'],
            'timestamp': timezone.now().isoformat()
        }))
    
    async def broadcast_message(self, event):
        """Handle broadcast messages"""
        await self.send(text_data=json.dumps({
            'type': 'broadcast',
            'message': event['message'],
            'timestamp': timezone.now().isoformat()
        }))
    
    # ============================================
    # DATABASE OPERATIONS (async wrappers)
    # ============================================
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for current user"""
        try:
            count = Notification.objects.filter(
                user=self.user,
                is_read=False
            ).count()
            return count
        except Exception as e:
            logger.error(f"❌ Error getting unread count: {e}")
            return 0
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark single notification as read"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=self.user
            )
            if not notification.is_read:
                notification.mark_as_read()
                logger.info(f"✓ Notification {notification_id} marked as read")
            return True
        except Notification.DoesNotExist:
            logger.warning(f"⚠️ Notification {notification_id} not found")
            return False
        except Exception as e:
            logger.error(f"❌ Error marking notification as read: {e}")
            return False
    
    @database_sync_to_async
    def mark_all_read(self):
        """Mark all notifications as read for current user"""
        try:
            count = Notification.objects.filter(
                user=self.user,
                is_read=False
            ).count()
            
            Notification.objects.filter(
                user=self.user,
                is_read=False
            ).update(
                is_read=True,
                read_at=timezone.now()
            )
            
            logger.info(f"✓ {count} notifications marked as read for {self.user.email}")
            return count
        except Exception as e:
            logger.error(f"❌ Error marking all notifications as read: {e}")
            return 0
    
    @database_sync_to_async
    def get_recent_notifications(self, limit=10):
        """Get recent notifications for current user with PERMISSION FILTERING"""
        try:
            notifications = Notification.objects.filter(
                user=self.user
            ).select_related('content_type').order_by('-created_at')[:limit]
            
            # ✅ FILTER by permissions
            filtered_notifications = []
            for n in notifications:
                if self.should_show_notification(n):
                    filtered_notifications.append({
                        'id': n.id,
                        'title': n.title,
                        'message': n.message,
                        'notification_type': n.notification_type,
                        'is_read': n.is_read,
                        'created_at': n.created_at.strftime('%b %d, %Y %I:%M %p'),
                        'link': self.get_notification_link(n),
                        'object_id': n.object_id,
                    })
            
            return filtered_notifications
        except Exception as e:
            logger.error(f"❌ Error getting notifications: {e}")
            return []
  
    def should_show_notification(self, notification):
            """
            ✅ NEW METHOD: Check if user has permission to see this notification
            """
            # Permission mapping
            permission_map = {
                'new_customer': 'view_customers',
                'demo_request': 'view_demo_requests',
                'demo_cancellation': 'view_demo_requests',
                'enquiry': 'view_enquiries',
                'milestone': None,  # Everyone can see
                'system_announcement': None,  # Everyone can see
                'demo_confirmation': 'view_demo_requests',
                'demo_rejection': 'view_demo_requests',
                'demo_reschedule': 'view_demo_requests',
            }
            
            required_permission = permission_map.get(notification.notification_type)
            
            # If no permission required, show to everyone
            if not required_permission:
                return True
            
            # Check if user has required permission
            return self.user.has_permission(required_permission)
    def get_notification_link(self, notification):
        """
        Generate notification link based on type
        """
        obj_id = notification.object_id
        notif_type = notification.notification_type
        
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
        except Exception as e:
            logger.error(f"❌ Error generating notification link: {e}")
            return '/notifications/admin/'