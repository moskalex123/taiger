import { ref, reactive } from 'vue';

// Define types for notifications
export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: number;
  message: string;
  type: NotificationType;
  duration: number;
  timestamp: number;
}

// Global notification state
const notifications = ref<Notification[]>([]);
let notificationId = 0;

export function useNotifications() {
  
  // Add a notification
  const addNotification = (message: string, type: NotificationType = 'success', duration = 5000): number => {
    const id = ++notificationId;
    const notification: Notification = {
      id,
      message,
      type,
      duration,
      timestamp: Date.now()
    };
    
    notifications.value.push(notification);
    
    // Automatically remove after the specified duration
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, duration);
    }
    
    return id;
  };
  
  // Remove a notification
  const removeNotification = (id: number): void => {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index > -1) {
      notifications.value.splice(index, 1);
    }
  };
  
  // Clear all notifications
  const clearNotifications = (): void => {
    notifications.value = [];
  };
  
  // Show a success notification
  const showSuccess = (message: string, duration = 5000): number => {
    return addNotification(message, 'success', duration);
  };
  
  // Show an error notification
  const showError = (message: string, duration = 8000): number => {
    return addNotification(message, 'error', duration);
  };
  
  // Show a warning notification
  const showWarning = (message: string, duration = 6000): number => {
    return addNotification(message, 'warning', duration);
  };
  
  // Show an info notification
  const showInfo = (message: string, duration = 5000): number => {
    return addNotification(message, 'info', duration);
  };
  
  return {
    notifications,
    addNotification,
    removeNotification,
    clearNotifications,
    showSuccess,
    showError,
    showWarning,
    showInfo
  };
}