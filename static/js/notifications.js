/**
 * Real-tim    init() {
        if (typeof window.djangoData === 'undefined' || !window.djangoData.userId) {
            console.log('User not authenticated, skipping notification WebSocket');
            return;
        }
        
        this.connect();
        this.setupEventListeners();
    }ations WebSocket Handler
 * Handles real-time notifications and updates the UI accordingly
 */

class NotificationManager {
    constructor() {
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectInterval = 3000; // 3 seconds
        this.notificationCount = 0;
        
        this.init();
    }
    
    init() {
        if (!window.djangoData || !window.djangoData.userId) {
            console.log('User not authenticated, skipping notification WebSocket');
            return;
        }
        
        this.connect();
        this.setupEventListeners();
    }
    
    connect() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            this.setupSocketEventListeners();
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.scheduleReconnect();
        }
    }
    
    setupSocketEventListeners() {
        this.socket.onopen = (event) => {
            console.log('Notification WebSocket connected');
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };
        
        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        this.socket.onclose = (event) => {
            console.log('Notification WebSocket disconnected');
            this.updateConnectionStatus(false);
            
            if (!event.wasClean) {
                this.scheduleReconnect();
            }
        };
        
        this.socket.onerror = (error) => {
            console.error('Notification WebSocket error:', error);
        };
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'notification':
                this.showNotification(data.data);
                this.updateNotificationCount(1);
                break;
            case 'count_update':
                this.setNotificationCount(data.count);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    showNotification(notificationData) {
        // Update notification dropdown
        this.addToNotificationDropdown(notificationData);
        
        // Show browser notification if permission granted
        if (Notification.permission === 'granted') {
            new Notification(notificationData.title, {
                body: notificationData.message,
                icon: '/static/images/favicon.ico', // Adjust path as needed
                tag: 'elearning-notification'
            });
        }
        
        // Show in-page toast notification
        this.showToastNotification(notificationData);
    }
    
    addToNotificationDropdown(notificationData) {
        const dropdown = document.getElementById('notification-dropdown');
        if (!dropdown) return;
        
        // Create notification item
        const notificationItem = document.createElement('div');
        notificationItem.className = 'dropdown-item notification-item';
        notificationItem.innerHTML = `
            <div class="d-flex">
                <div class="notification-icon">
                    <i class="fas ${this.getNotificationIcon(notificationData.type)}"></i>
                </div>
                <div class="notification-content flex-grow-1">
                    <div class="notification-title">${notificationData.title}</div>
                    <div class="notification-message">${notificationData.message}</div>
                    <div class="notification-time text-muted">${notificationData.created_at}</div>
                </div>
            </div>
        `;
        
        // Add to top of dropdown
        const firstChild = dropdown.firstElementChild;
        if (firstChild) {
            dropdown.insertBefore(notificationItem, firstChild);
        } else {
            dropdown.appendChild(notificationItem);
        }
        
        // Limit to 10 notifications in dropdown
        const notifications = dropdown.querySelectorAll('.notification-item');
        if (notifications.length > 10) {
            dropdown.removeChild(notifications[notifications.length - 1]);
        }
    }
    
    showToastNotification(notificationData) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast-notification ${notificationData.is_important ? 'important' : ''}`;
        toast.innerHTML = `
            <div class="toast-content">
                <div class="toast-icon">
                    <i class="fas ${this.getNotificationIcon(notificationData.type)}"></i>
                </div>
                <div class="toast-body">
                    <div class="toast-title">${notificationData.title}</div>
                    <div class="toast-message">${notificationData.message}</div>
                </div>
                <button class="toast-close" onclick="this.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Add to page
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        // Animate in
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 5000);
    }
    
    getNotificationIcon(type) {
        const icons = {
            'enrollment': 'fa-user-plus',
            'material': 'fa-book',
            'feedback': 'fa-star',
            'system': 'fa-bell',
            'announcement': 'fa-bullhorn'
        };
        return icons[type] || 'fa-bell';
    }
    
    updateNotificationCount(increment) {
        this.notificationCount += increment;
        this.setNotificationCount(this.notificationCount);
    }
    
    setNotificationCount(count) {
        this.notificationCount = count;
        const badge = document.getElementById('notification-count');
        if (badge) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    }
    
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnection attempts reached');
            return;
        }
        
        this.reconnectAttempts++;
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        
        setTimeout(() => {
            this.connect();
        }, this.reconnectInterval * this.reconnectAttempts);
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('connection-status');
        if (statusIndicator) {
            statusIndicator.className = connected ? 'connected' : 'disconnected';
            statusIndicator.title = connected ? 'Connected to real-time notifications' : 'Disconnected from real-time notifications';
        }
    }
    
    setupEventListeners() {
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        
        // Mark notification as read when clicked
        document.addEventListener('click', (event) => {
            const notificationItem = event.target.closest('.notification-item');
            if (notificationItem) {
                const notificationId = notificationItem.dataset.notificationId;
                if (notificationId) {
                    this.markNotificationRead(notificationId);
                }
            }
        });
    }
    
    markNotificationRead(notificationId) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                type: 'mark_read',
                notification_id: notificationId
            }));
        }
    }
    
    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }
}

// CSS for toast notifications
const toastCSS = `
.toast-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    max-width: 400px;
}

.toast-notification {
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    margin-bottom: 10px;
    transform: translateX(100%);
    transition: all 0.3s ease;
    border-left: 4px solid #007bff;
}

.toast-notification.important {
    border-left-color: #dc3545;
}

.toast-notification.show {
    transform: translateX(0);
}

.toast-content {
    display: flex;
    align-items: flex-start;
    padding: 12px;
}

.toast-icon {
    margin-right: 10px;
    color: #007bff;
    font-size: 18px;
    margin-top: 2px;
}

.toast-notification.important .toast-icon {
    color: #dc3545;
}

.toast-body {
    flex: 1;
}

.toast-title {
    font-weight: 600;
    margin-bottom: 4px;
    color: #333;
}

.toast-message {
    font-size: 14px;
    color: #666;
    line-height: 1.4;
}

.toast-close {
    background: none;
    border: none;
    color: #999;
    cursor: pointer;
    padding: 0;
    margin-left: 10px;
}

.toast-close:hover {
    color: #333;
}

.notification-item {
    padding: 10px 15px !important;
    border-bottom: 1px solid #eee;
}

.notification-item:hover {
    background-color: #f8f9fa;
}

.notification-icon {
    margin-right: 10px;
    color: #007bff;
    width: 20px;
    text-align: center;
}

.notification-title {
    font-weight: 600;
    margin-bottom: 2px;
}

.notification-message {
    font-size: 13px;
    color: #666;
    margin-bottom: 2px;
}

.notification-time {
    font-size: 11px;
}

#connection-status {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
    margin-left: 5px;
}

#connection-status.connected {
    background-color: #28a745;
}

#connection-status.disconnected {
    background-color: #dc3545;
}
`;

// Add CSS to page
const style = document.createElement('style');
style.textContent = toastCSS;
document.head.appendChild(style);

// Initialize notification manager when page loads
let notificationManager;
document.addEventListener('DOMContentLoaded', () => {
    notificationManager = new NotificationManager();
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (notificationManager) {
        notificationManager.disconnect();
    }
});
