// static/js/websocket-notifications.js
/**
 * WebSocket Notification System
 * Real-time push notifications for Demo Portal
 */

class NotificationWebSocket {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.heartbeatInterval = null;
        this.isConnecting = false;
        
        console.log('🔌 Initializing WebSocket Notification System...');
        this.connect();
    }
    
    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            console.log('⚠️ Already connected or connecting');
            return;
        }
        
        this.isConnecting = true;
        
        // WebSocket URL
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        console.log(`🔌 Connecting to: ${wsUrl}`);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = (event) => {
            console.log('✅ WebSocket connected successfully!');
            this.isConnecting = false;
            this.reconnectAttempts = 0;
            
            // Start heartbeat
            this.startHeartbeat();
            
            // Update connection indicator
            this.updateConnectionStatus(true);
            
            // Show connection toast
            this.showConnectionToast('Connected', 'success');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('❌ Error parsing message:', error);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('❌ WebSocket error:', error);
            this.isConnecting = false;
        };
        
        this.ws.onclose = (event) => {
            console.log(`🔌 WebSocket closed (Code: ${event.code})`);
            this.isConnecting = false;
            this.stopHeartbeat();
            this.updateConnectionStatus(false);
            
            // Attempt reconnection
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                console.log(`🔄 Reconnecting... (Attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                
                setTimeout(() => {
                    this.connect();
                }, this.reconnectDelay * this.reconnectAttempts);
            } else {
                console.error('❌ Max reconnection attempts reached');
                this.showConnectionToast('Disconnected - Refresh page to reconnect', 'error');
                this.showReconnectButton();
            }
        };
    }
    
    handleMessage(data) {
        console.log('📨 Received:', data.type, data);
        
        switch(data.type) {
            case 'connection_established':
                console.log(`✅ Connected as ${data.user_type} (ID: ${data.user_id})`);
                console.log(`📋 Groups: ${data.groups.join(', ')}`);
                this.updateUnreadBadge(data.unread_count);
                break;
            
            case 'new_notification':
                // ✅ NEW NOTIFICATION ARRIVED - INSTANT!
                console.log('🔔 NEW NOTIFICATION (REAL-TIME):', data.notification.title);
                this.handleNewNotification(data.notification);
                break;
            
            case 'unread_count':
                this.updateUnreadBadge(data.count);
                break;
            
            case 'mark_read_response':
                console.log(`✓ Notification ${data.notification_id} marked as read`);
                break;
            
            case 'mark_all_read_response':
                console.log(`✓ ${data.count} notifications marked as read`);
                this.updateUnreadBadge(0);
                break;
            
            case 'notifications_list':
                this.renderNotifications(data.notifications);
                break;
            
            case 'pong':
                console.log('💓 Heartbeat OK');
                break;
            
            default:
                console.warn('Unknown message type:', data.type);
        }
    }
    
    handleNewNotification(notification) {
        console.log('🎯 Processing new notification...');
        
        // Update badge count
        const badge = document.getElementById('adminNotifBadge');
        if (badge) {
            const currentCount = parseInt(badge.textContent || '0');
            this.updateUnreadBadge(currentCount + 1);
        }
        
        // Play sound (optional)
        this.playNotificationSound();
        
        // Show browser notification
        this.showBrowserNotification(notification);
        
        // Show toast notification
        this.showNotificationToast(notification);
        
        // Reload list if dropdown is open
        const menu = document.getElementById('adminNotifMenu');
        if (menu && menu.classList.contains('show')) {
            console.log('📋 Dropdown open - reloading list...');
            this.loadNotifications();
        }
    }
    
    updateUnreadBadge(count) {
        const badge = document.getElementById('adminNotifBadge');
        if (!badge) return;
        
        console.log(`🔢 Updating badge: ${count}`);
        
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.add('show');
            badge.style.display = 'block';
        } else {
            badge.classList.remove('show');
            badge.style.display = 'none';
        }
    }
    
    showNotificationToast(notification) {
        // Check if toast container exists
        let container = document.getElementById('ws-toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'ws-toast-container';
            container.style.cssText = `
                position: fixed;
                top: 80px;
                right: 20px;
                z-index: 99999;
                max-width: 400px;
            `;
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = 'ws-notification-toast';
        toast.style.cssText = `
            background: white;
            border-left: 4px solid #087fc2;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            margin-bottom: 10px;
            cursor: pointer;
            animation: slideInRight 0.3s ease-out;
        `;
        
        toast.innerHTML = `
            <div style="font-weight: 600; color: #1f2937; margin-bottom: 5px; display: flex; align-items: center;">
                <span style="font-size: 1.2em; margin-right: 8px;">🔔</span>
                ${this.escapeHtml(notification.title)}
            </div>
            <div style="font-size: 0.875rem; color: #6b7280;">
                ${this.escapeHtml(notification.message.substring(0, 100))}${notification.message.length > 100 ? '...' : ''}
            </div>
        `;
        
        container.appendChild(toast);
        
        // Click to view
        toast.addEventListener('click', () => {
            if (notification.link) {
                window.location.href = notification.link;
            }
            toast.remove();
        });
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }
    
    showBrowserNotification(notification) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(notification.title, {
                body: notification.message,
                icon: '/static/img/logo.png',
                tag: `notification-${notification.id}`,
                requireInteraction: false
            });
        }
    }
    
    showConnectionToast(message, type = 'info') {
        const colors = {
            success: '#10b981',
            error: '#ef4444',
            info: '#087fc2'
        };
        
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${colors[type]};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            z-index: 99999;
            font-weight: 500;
            animation: slideInRight 0.3s ease-out;
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutRight 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
    
playNotificationSound() {
    try {
        // Create AudioContext
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Create oscillator (tone generator)
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        // Connect nodes
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        // Configure sound
        oscillator.frequency.value = 800; // Frequency in Hz
        oscillator.type = 'sine'; // Sine wave for smooth sound
        
        // Volume control
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
        
        // Play
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.3);
        
        console.log('🔊 Notification sound played');
    } catch (e) {
        console.log('🔇 Sound failed (non-critical):', e.message);
    }
}
    // ============================================
    // Actions (send to server)
    // ============================================
    
    markAsRead(notificationId) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                action: 'mark_read',
                notification_id: notificationId
            }));
        }
    }
    
    markAllAsRead() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                action: 'mark_all_read'
            }));
        }
    }
    
    loadNotifications(limit = 10) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({
                action: 'get_notifications',
                limit: limit
            }));
        }
    }
    
    // ============================================
    // Heartbeat
    // ============================================
    
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ action: 'ping' }));
            }
        }, 30000); // 30 seconds
    }
    
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }
    
    // ============================================
    // UI Helpers
    // ============================================
    
    updateConnectionStatus(isConnected) {
        const indicator = document.getElementById('ws-connection-indicator');
        if (!indicator) return;
        
        if (isConnected) {
            indicator.style.background = '#10b981';
            indicator.title = 'Real-time connected';
        } else {
            indicator.style.background = '#ef4444';
            indicator.title = 'Disconnected';
        }
    }
    
    showReconnectButton() {
        const btn = document.createElement('button');
        btn.id = 'ws-reconnect-btn';
        btn.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #ef4444;
            color: white;
            padding: 12px 24px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(239, 68, 68, 0.3);
            z-index: 99999;
            font-weight: 600;
        `;
        btn.innerHTML = '🔌 Reconnect Notifications';
        
        document.body.appendChild(btn);
        
        btn.addEventListener('click', () => {
            this.reconnectAttempts = 0;
            this.connect();
            btn.remove();
        });
    }
    
    renderNotifications(notifications) {
        const list = document.getElementById('adminNotifList');
        if (!list) return;
        
        if (notifications.length === 0) {
            list.innerHTML = `
                <div class="admin-notif-empty">
                    <div class="admin-notif-empty-icon"><i class="fas fa-inbox"></i></div>
                    <div class="admin-notif-empty-text">No notifications yet</div>
                </div>
            `;
            return;
        }
        
        list.innerHTML = notifications.map(n => `
            <a href="${n.link}" class="admin-notif-item ${n.is_read ? '' : 'unread'}" 
               data-id="${n.id}">
                <div class="admin-notif-item-content">
                    <div class="admin-notif-icon ${this.getIconClass(n.notification_type)}">
                        ${this.getIcon(n.notification_type)}
                    </div>
                    <div class="admin-notif-text">
                        <div class="admin-notif-title">${this.escapeHtml(n.title)}</div>
                        <div class="admin-notif-message">${this.escapeHtml(n.message)}</div>
                        <div class="admin-notif-time">${n.created_at}</div>
                    </div>
                </div>
            </a>
        `).join('');
        
        // Add click handlers
        list.querySelectorAll('.admin-notif-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const id = item.dataset.id;
                const link = item.getAttribute('href');
                this.markAsRead(id);
                setTimeout(() => window.location.href = link, 100);
            });
        });
    }
    
    getIconClass(type) {
        const map = {
            'new_customer': 'customer',
            'demo_request': 'demo',
            'demo_cancellation': 'cancellation',
            'enquiry': 'enquiry',
            'milestone': 'milestone',
        };
        return map[type] || 'customer';
    }
    
    getIcon(type) {
        const map = {
            'new_customer': '<i class="fas fa-user-plus"></i>',
            'demo_request': '<i class="fas fa-calendar-check"></i>',
            'demo_cancellation': '<i class="fas fa-times-circle"></i>',
            'enquiry': '<i class="fas fa-comment-dots"></i>',
            'milestone': '<i class="fas fa-trophy"></i>',
        };
        return map[type] || '<i class="fas fa-bell"></i>';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// ============================================
// CSS Animations
// ============================================
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ============================================
// Initialize WebSocket
// ============================================
let notificationWS = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing WebSocket notifications...');
    notificationWS = new NotificationWebSocket();
    
    // Request browser notification permission
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
            console.log('📢 Notification permission:', permission);
        });
    }
    
    // ✅ IMPORTANT: Disable old polling when WebSocket is active
    const oldPolling = setInterval(() => {}, 30000);
    clearInterval(oldPolling);
    console.log('⏸️ Old polling disabled - using WebSocket now!');
    
    // Update mark all button to use WebSocket
    const markAllBtn = document.getElementById('adminMarkAllBtn');
    if (markAllBtn) {
        markAllBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            if (notificationWS && notificationWS.ws.readyState === WebSocket.OPEN) {
                notificationWS.markAllAsRead();
            }
        });
    }
});