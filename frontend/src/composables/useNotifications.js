import { ref, reactive } from 'vue';

// Глобальное состояние уведомлений
const notifications = ref([]);
let notificationId = 0;

export function useNotifications() {
  
  // Добавить уведомление
  const addNotification = (message, type = 'success', duration = 5000) => {
    const id = ++notificationId;
    const notification = {
      id,
      message,
      type, // success, error, warning, info
      duration,
      timestamp: Date.now()
    };
    
    notifications.value.push(notification);
    
    // Автоматически удалить через указанное время
    if (duration > 0) {
      setTimeout(() => {
        removeNotification(id);
      }, duration);
    }
    
    return id;
  };
  
  // Удалить уведомление
  const removeNotification = (id) => {
    const index = notifications.value.findIndex(n => n.id === id);
    if (index > -1) {
      notifications.value.splice(index, 1);
    }
  };
  
  // Очистить все уведомления
  const clearNotifications = () => {
    notifications.value = [];
  };
  
  // Показать уведомление об успехе
  const showSuccess = (message, duration = 5000) => {
    return addNotification(message, 'success', duration);
  };
  
  // Показать уведомление об ошибке
  const showError = (message, duration = 8000) => {
    return addNotification(message, 'error', duration);
  };
  
  // Показать предупреждение
  const showWarning = (message, duration = 6000) => {
    return addNotification(message, 'warning', duration);
  };
  
  // Показать информационное уведомление
  const showInfo = (message, duration = 5000) => {
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