<template>
  <div class="notification-container">
    <TransitionGroup name="notification" tag="div">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        :class="['notification', `notification-${notification.type}`]"
        @click="removeNotification(notification.id)"
      >
        <div class="notification-icon">
          <svg v-if="notification.type === 'success'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
          <svg v-else-if="notification.type === 'error'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          <svg v-else-if="notification.type === 'warning'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <div class="notification-content">
          <div class="notification-message" v-html="formatMessage(notification.message)"></div>
        </div>
        <button class="notification-close" @click.stop="removeNotification(notification.id)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useNotifications } from '../composables/useNotifications';

const { notifications, removeNotification } = useNotifications();

const formatMessage = (message) => {
  if (!message) return '';
  
  // Заменяем переносы строк на <br> для HTML отображения
  return message
    .replace(/\n/g, '<br>')
    .replace(/\t/g, '&nbsp;&nbsp;&nbsp;&nbsp;'); // Заменяем табы на пробелы
};
</script>

<style scoped>
.notification-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  pointer-events: none;
}

.notification {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  backdrop-filter: blur(10px);
  cursor: pointer;
  pointer-events: auto;
  min-width: 300px;
  max-width: 500px;
  transition: all 0.3s ease;
}

.notification:hover {
  transform: translateX(-4px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}

.notification-success {
  background: rgba(40, 167, 69, 0.95);
  color: white;
  border-left: 4px solid #28a745;
}

.notification-error {
  background: rgba(220, 53, 69, 0.95);
  color: white;
  border-left: 4px solid #dc3545;
  max-width: 600px;
}

.notification-warning {
  background: rgba(255, 193, 7, 0.95);
  color: #212529;
  border-left: 4px solid #ffc107;
}

.notification-info {
  background: rgba(0, 123, 255, 0.95);
  color: white;
  border-left: 4px solid #007bff;
}

.notification-icon {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-message {
  font-weight: 500;
  line-height: 1.5;
  word-wrap: break-word;
  white-space: pre-wrap;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 14px;
}

.notification-error .notification-message {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  max-height: 200px;
  overflow-y: auto;
}

.notification-close {
  flex-shrink: 0;
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.notification-close:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.1);
}

/* Анимации */
.notification-enter-active {
  transition: all 0.3s ease;
}

.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-move {
  transition: transform 0.3s ease;
}

/* Мобильная адаптация */
@media (max-width: 768px) {
  .notification-container {
    top: 10px;
    right: 10px;
    left: 10px;
  }
  
  .notification {
    min-width: auto;
    max-width: none;
    margin-bottom: 8px;
    padding: 12px;
  }
  
  .notification-message {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .notification {
    padding: 10px;
    gap: 8px;
  }
  
  .notification-icon svg {
    width: 16px;
    height: 16px;
  }
  
  .notification-close svg {
    width: 14px;
    height: 14px;
  }
}
</style>