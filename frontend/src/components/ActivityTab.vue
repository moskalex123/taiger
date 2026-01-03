<template>
  <div class="agent-log-tab">


    <!-- Agent Log Feed -->
    <div class="redesigned-card">
      <div class="card-header">
        <h3 class="card-title">{{ $t('agent_log') || 'Журнал агента' }}</h3>
        <span class="activity-count">{{ (filteredLogs || []).length }} {{ $t('entries') }}</span>
      </div>
      
      <div class="log-feed-container">
        <div v-if="loading" class="loading-state">
          <div class="loading-spinner"></div>
          <span>{{ $t('loading_logs') || 'Загрузка логов...' }}</span>
        </div>
        
        <div v-else-if="(filteredLogs || []).length === 0" class="empty-state">
          <div class="empty-icon">📋</div>
          <div class="empty-message">{{ getEmptyStateMessage() }}</div>
        </div>
        
        <div v-else class="log-feed">
          <div 
            v-for="log in paginatedLogs" 
            :key="log.id"
            class="log-item"
            :class="{ 'log-expanded': expandedLogs[log.id] }"
          >
            <div class="log-content" @click="toggleLogExpansion(log.id)">
              <span class="log-message">{{ log.message }}</span>
            </div>
              
            <!-- Expanded Details -->
            <div v-if="expandedLogs[log.id] && log.details" class="log-details">
              <div v-if="log.details.post_content" class="detail-section">
                <div class="detail-label">Содержимое поста:</div>
                <div class="detail-content">{{ log.details.post_content }}</div>
              </div>
              <div v-if="log.details.processing_time" class="detail-section">
                <div class="detail-label">Время обработки:</div>
                <div class="detail-content">{{ log.details.processing_time }}мс</div>
              </div>
              <div v-if="log.details.model_used" class="detail-section">
                <div class="detail-label">Модель ИИ:</div>
                <div class="detail-content">{{ log.details.model_used }}</div>
              </div>
              <div v-if="log.details.tokens_used" class="detail-section">
                <div class="detail-label">Токенов использовано:</div>
                <div class="detail-content">{{ log.details.tokens_used }}</div>
              </div>
              <div v-if="log.details.cost" class="detail-section">
                <div class="detail-label">Стоимость:</div>
                <div class="detail-content">${{ log.details.cost }}</div>
              </div>
              <div v-if="log.details.error_details" class="detail-section error-details">
                <div class="detail-label">Детали ошибки:</div>
                <div class="detail-content">{{ log.details.error_details }}</div>
              </div>
            </div>
            
            <div class="log-actions">
              <button v-if="log.level === 'error'" @click="copyError(log)" class="btn-redesigned btn-secondary btn-sm">
                📋
              </button>
              <button v-if="log.details" @click="toggleLogExpansion(log.id)" class="btn-redesigned btn-secondary btn-sm">
                {{ expandedLogs[log.id] ? '▲' : '▼' }}
              </button>
            </div>
          </div>
        </div>
        
        <!-- Load More Button -->
        <div v-if="hasMoreLogs" class="load-more-container">
          <button @click="loadMore" class="btn-redesigned btn-secondary">
            {{ $t('load_more') || 'Загрузить ещё' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted, onUnmounted, watch, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'

const { t: $t, locale } = useI18n()

interface LogItem {
  id: string
  level: string
  message: string
  timestamp: string
  source?: string
  channel?: string
  log_type?: string
  details?: {
    post_content?: string
    processing_time?: number
    model_used?: string
    tokens_used?: number
    cost?: number
    error_details?: string
  }
}

// Inject data from parent - using the same logic as Dashboard
const scheduledPosts = inject<Ref<any[]>>('scheduledPosts', ref([]))
const realtimeLogs = inject<Ref<any[]>>('realtimeLogs', ref([]))
const workerErrors = inject<Ref<any[]>>('workerErrors', ref([]))
const fetchScheduledPosts = inject<() => Promise<void>>('fetchScheduledPosts', async () => {})
const fetchWorkerErrors = inject<() => Promise<void>>('fetchWorkerErrors', async () => {})

// Local state
const selectedFilter = ref('all')
const refreshing = ref(false)
const loading = ref(false)
const currentPage = ref(1)
const itemsPerPage = 20
const expandedLogs = ref<{ [key: string]: boolean }>({})

// WebSocket connection for real-time logs (same as Dashboard)
const websocket = ref<WebSocket | null>(null)
const websocketConnected = ref(false)
const fallbackLogTimer = ref<number | null>(null)

// Function to check if message contains post content that should not be translated
const isPostContentMessage = (message: string) => {
  return message.includes('Выходной текст:') || 
         message.includes('Output text:') ||
         message.includes('Сообщение запланировано:') ||
         message.includes('Message scheduled:')
}

// Function to translate log messages (same as Dashboard)
const translateLogMessage = (message: string) => {
  if (locale.value !== 'ru') {
    return message
  }

  const translations: { [key: string]: string } = {
    'Dashboard connected to real-time logs': 'Панель управления подключена к журналу в реальном времени',
    'Using fallback mode for real-time logs (WebSocket unavailable)': 'Использование резервного режима для логов (WebSocket недоступен)',
    '⏳ Worker is now idle and waiting for new messages': '⏳ Агент готов и ожидает новые сообщения',
    'Worker is now idle and waiting for new messages': 'Агент готов и ожидает новые сообщения',
    '🔗 Connecting to Telegram...': '🔗 Подключение к Telegram...',
    'Connecting to Telegram...': 'Подключение к Telegram...',
    '🚀 Worker initialized successfully': '🚀 Агент успешно инициализирован',
    'Worker initialized successfully': 'Агент успешно инициализирован',
    '✅ Worker ready and waiting for new messages': '✅ Агент готов и ожидает новые сообщения',
    'Worker ready and waiting for new messages': 'Агент готов и ожидает новые сообщения',
    'Worker connected to Telegram and ready to process messages': 'Агент подключился к Telegram и готов обрабатывать сообщения',
    'Message handler registered for all message types': 'Обработчик сообщений зарегистрирован для всех типов сообщений',
    'Worker is ready and listening for messages': 'Агент готов и прослушивает сообщения',
    'Connection established': 'Соединение установлено',
    'Connection lost': 'Соединение потеряно',
    'Reconnecting...': 'Переподключение...',
    'Worker started successfully': 'Агент успешно запущен',
    'Worker stopped': 'Агент остановлен',
    'Processing message': 'Обработка сообщения',
    'Message sent successfully': 'Сообщение успешно отправлено',
    'Error processing message': 'Ошибка при обработке сообщения',
    '✅ Batch processing completed': '✅ Пакетная обработка завершена',
    'Batch processing completed': 'Пакетная обработка завершена',
    '🔄 Starting batch processing of accumulated posts': '🔄 Начинается пакетная обработка накопленных постов',
    'Starting batch processing of accumulated posts': 'Начинается пакетная обработка накопленных постов',
    'Insufficient funds': 'Недостаточно средств',
    'Authentication failed': 'Ошибка аутентификации',
    'Rate limit exceeded': 'Превышен лимит запросов',
    'Network error': 'Ошибка сети'
  }

  if (translations[message]) {
    return translations[message]
  }

  // Pattern matching for common messages
  if (message.toLowerCase().includes('worker is now idle') || message.toLowerCase().includes('waiting for new messages')) {
    return 'Агент готов и ожидает новые сообщения'
  }
  
  if (message.toLowerCase().includes('connecting to telegram')) {
    return 'Подключение к Telegram...'
  }
  
  if (message.toLowerCase().includes('worker initialized successfully')) {
    return 'Агент успешно инициализирован'
  }

  // Handle dynamic messages with patterns
  if (message.includes('Connected to Telegram as')) {
    return message.replace('Connected to Telegram as', 'Подключен к Telegram как')
  }

  if (message.includes('New message') && message.includes('from')) {
    return message.replace('New message', 'Новое сообщение').replace('from', 'из')
  }

  if (message.includes('Message scheduled:')) {
    return message.replace('Message scheduled:', 'Сообщение запланировано:')
  }

  return message
}

// Get userInfo from inject at the top level
const userInfo = inject<Ref<any>>('userInfo', ref(null))

// Debug injected data
console.log('🎯 ActivityTab: Injected data:', {
  scheduledPosts: scheduledPosts.value?.length || 0,
  realtimeLogs: realtimeLogs.value?.length || 0,
  workerErrors: workerErrors.value?.length || 0,
  userInfo: userInfo.value?.id || 'no user'
})

// WebSocket connection logic (same as Dashboard)
const connectWebSocket = () => {
  if (!userInfo.value?.id) return
  
  // Используем текущий хост и протокол
  // В production (включая TMA) используем nginx proxy без порта
  let host = window.location.host
  let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  
  // Для TMA и production используем nginx proxy (без порта 8000)
  if (window.Telegram && window.Telegram.WebApp || !host.includes(':5173')) {
    // Убираем порт из хоста если он есть (используем nginx proxy)
    if (host.includes(':')) {
      host = host.split(':')[0];
    }
    // Используем стандартный порт (через nginx)
    // protocol остается как есть (wss: для https, ws: для http)
  }
  
  const wsUrl = protocol + '//' + host + '/api/ws/' + userInfo.value.id
  console.log('ActivityTab: Connecting to WebSocket:', wsUrl)
  websocket.value = new WebSocket(wsUrl)
  
  setTimeout(() => {
    if (!websocketConnected.value) {
      console.log('ActivityTab: WebSocket failed to connect, starting fallback')
      startFallbackLogUpdates()
    }
  }, 5000)
  
  websocket.value.onopen = () => {
    console.log('ActivityTab: WebSocket connected for real-time logs')
    websocketConnected.value = true
    
    if (fallbackLogTimer.value) {
      clearInterval(fallbackLogTimer.value)
      fallbackLogTimer.value = null
    }
  }
  
  websocket.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      console.log('🎯 ActivityTab: Raw WebSocket message:', data)
      
      if (data.type === 'log') {
        // Получаем сообщение и очищаем от префиксов
        let logMessage = data.message || data.message_key || 'Пустое сообщение'
        
        // Убираем префиксы типа "success26.09.2025, 14:52:09" или "info26.09.2025, 14:51:46"
        logMessage = logMessage.replace(/^(success|info|error|warning)\d{2}\.\d{2}\.\d{4},\s*\d{2}:\d{2}:\d{2}\s*/, '')
        
        // Убираем эмодзи в начале если есть
        logMessage = logMessage.replace(/^[✅🔗📋🚀⚠️❌📱]\s*/, '')
        
        // Проверяем на дубликаты
        const isDuplicate = (realtimeLogs.value || []).some(log => 
          log.message === logMessage && 
          Math.abs(new Date(log.timestamp).getTime() - new Date(data.timestamp).getTime()) < 5000
        )
        
        if (!isDuplicate) {
          if (!realtimeLogs.value) {
            realtimeLogs.value = []
          }
          realtimeLogs.value.unshift({
            id: Date.now() + Math.random(),
            timestamp: data.timestamp,
            log_type: data.log_type,
            level: data.level,
            message: logMessage
          })
          
          // Ограничиваем количество логов
          if ((realtimeLogs.value || []).length > 100) {
            realtimeLogs.value = realtimeLogs.value.slice(0, 100)
          }
          
          console.log('🎯 ActivityTab: Added log:', logMessage, 'Total logs:', (realtimeLogs.value || []).length)
        }
      }
    } catch (error) {
      console.error('ActivityTab: Error parsing WebSocket message:', error)
    }
  }
  
  websocket.value.onclose = () => {
    console.log('ActivityTab: WebSocket disconnected, attempting to reconnect...')
    websocketConnected.value = false
    startFallbackLogUpdates()
    setTimeout(connectWebSocket, 3000)
  }
  
  websocket.value.onerror = (error) => {
    console.error('ActivityTab: WebSocket error:', error)
    websocketConnected.value = false
    startFallbackLogUpdates()
  }
}

const disconnectWebSocket = () => {
  if (websocket.value) {
    websocket.value.close()
    websocket.value = null
  }
  websocketConnected.value = false
  
  if (fallbackLogTimer.value) {
    clearInterval(fallbackLogTimer.value)
    fallbackLogTimer.value = null
  }
}

const startFallbackLogUpdates = () => {
  if (websocketConnected.value || fallbackLogTimer.value) return
  
  console.log('ActivityTab: НЕТ FALLBACK - ТОЛЬКО WEBSOCKET ДЛЯ ЖИВЫХ ЛОГОВ')
  // НЕ ДЕЛАЕМ HTTP ЗАПРОСЫ - ТОЛЬКО WEBSOCKET!
  // Просто пытаемся переподключиться к WebSocket
  fallbackLogTimer.value = setInterval(() => {
    if (websocketConnected.value) {
      clearInterval(fallbackLogTimer.value!)
      fallbackLogTimer.value = null
      return
    }
    
    console.log('ActivityTab: Attempting WebSocket reconnection...')
    connectWebSocket()
  }, 5000)
}

// Computed properties
const allLogs = computed(() => {
  console.log('🎯 ActivityTab: Computing allLogs, realtimeLogs:', (realtimeLogs.value || []).length)
  
  // Просто возвращаем все логи как есть, без фильтрации
  const logsArray = realtimeLogs.value || []
  if (!Array.isArray(logsArray)) {
    return []
  }
  
  const logs = logsArray.map((log: any) => ({
    id: `realtime-${log.id}`,
    level: log.level || 'info',
    message: log.message || 'Пустое сообщение',
    timestamp: log.timestamp,
    source: 'Воркер',
    log_type: log.log_type,
    details: log.details
  }))
  
  console.log('🎯 ActivityTab: Returning logs:', logs.length)
  return logs
})

const filteredLogs = computed(() => {
  return allLogs.value
})

const paginatedLogs = computed(() => {
  const start = 0
  const end = currentPage.value * itemsPerPage
  return filteredLogs.value.slice(start, end)
})

const hasMoreLogs = computed(() => {
  return (filteredLogs.value || []).length > currentPage.value * itemsPerPage
})

// Methods
const refreshLogs = async () => {
  console.log('🎯 ActivityTab: refreshLogs called - очищаем все логи')
  refreshing.value = true
  try {
    // Очищаем все логи
    if (realtimeLogs.value) {
      realtimeLogs.value.splice(0)
      console.log('🎯 ActivityTab: All logs cleared')
    }
    
    // Переподключаемся к WebSocket если нужно
    if (!websocketConnected.value && userInfo.value?.id) {
      connectWebSocket()
    }
  } catch (error) {
    console.error('ActivityTab: Error refreshing logs:', error)
  } finally {
    refreshing.value = false
  }
}

const loadMore = () => {
  currentPage.value++
}

const toggleLogExpansion = (logId: string) => {
  expandedLogs.value[logId] = !expandedLogs.value[logId]
}

const copyError = (log: any) => {
  const errorText = log.message + '\n' + (log.details?.error_details || '')
  navigator.clipboard.writeText(errorText).then(() => {
    // Show success message
    console.log('Error details copied to clipboard')
  }).catch(err => {
    console.error('Failed to copy error details:', err)
  })
}

const getEmptyStateMessage = () => {
  if (websocketConnected.value) {
    return $t('no_logs_yet') || 'Пока нет записей в журнале. Агент подключен и ожидает активности.'
  }
  return $t('no_logs_available') || 'Нет доступных записей в журнале.'
}

// Lifecycle
onMounted(() => {
  // Connect to WebSocket for real-time logs
  if (userInfo.value?.id) {
    connectWebSocket()
  }
})

onUnmounted(() => {
  disconnectWebSocket()
})

// Watch for data changes
watch(() => realtimeLogs.value, (newLogs) => {
  console.log('🎯 ActivityTab: realtimeLogs changed:', (newLogs || []).length)
}, { deep: true })
</script>

<style scoped>
.agent-log-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.filter-controls {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.filter-controls .form-select {
  flex: 1;
  margin: 0;
}

.activity-count {
  font-size: var(--text-sm);
  color: var(--text-hint);
}

.log-feed-container {
  height: calc(100vh - 200px);
  overflow-y: auto;
  background: var(--bg-primary);
  border-radius: var(--radius-md);
  padding: var(--space-sm);
}

.log-feed {
  background: var(--bg-primary);
  height: 100%;
  padding-bottom: var(--space-md);
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-xl);
  color: var(--text-secondary);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-xl);
  color: var(--text-hint);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: var(--space-md);
  opacity: 0.5;
}

.empty-message {
  font-size: var(--text-md);
  font-style: italic;
}

.log-item {
  padding: 8px 12px;
  border-bottom: 1px solid #e0e0e0 !important; /* Светлая граница для светлой темы */
  transition: all 0.2s ease;
  cursor: pointer;
  background: #ffffff !important; /* Белый фон для светлой темы */
  margin-bottom: 2px;
  border-radius: 4px;
  border: 1px solid #e0e0e0 !important; /* Граница для четкости */
}

.log-item:hover {
  background: #f8f9fa !important; /* Светло-серый фон при наведении */
}

.log-item:last-child {
  border-bottom: none;
  margin-bottom: 0;
}

.log-item.log-expanded {
  background: var(--bg-section);
  border-left: 3px solid var(--primary);
}

.log-content {
  width: 100%;
  line-height: 1.4;
  cursor: pointer;
  text-align: left;
  padding: var(--space-xs);
}

.log-message {
  font-size: 14px;
  color: #1a1a1a !important; /* Темный текст для светлой темы */
  word-wrap: break-word;
  display: block;
  line-height: 1.4;
}

.log-message:hover {
  color: var(--primary);
}

/* Темная тема для TMA */
.tma-environment .log-item {
  background: rgba(255, 255, 255, 0.1) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 6px;
  margin-bottom: 4px;
}

.tma-environment .log-item:hover {
  background: rgba(255, 255, 255, 0.15) !important;
}

.tma-environment .log-message {
  color: #ffffff !important;
  font-size: 13px;
  font-weight: 500;
}

.tma-environment .log-message:hover {
  color: #4CAF50;
}

.tma-environment .log-item.log-expanded {
  background: rgba(255, 255, 255, 0.1);
  border-left: 3px solid #4CAF50;
}



.log-details {
  margin-top: var(--space-md);
  padding: var(--space-md);
  background: var(--bg-card);
  border-radius: var(--radius-sm);
  border: 1px solid var(--bg-secondary);
}

/* Темная тема для деталей логов */
.tma-environment .log-details {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.detail-section {
  margin-bottom: var(--space-sm);
}

.detail-section:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  font-weight: var(--weight-medium);
  margin-bottom: var(--space-xs);
}

.detail-content {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.4;
  word-wrap: break-word;
}

/* Темная тема для содержимого деталей */
.tma-environment .detail-content {
  color: rgba(255, 255, 255, 0.8);
}

.tma-environment .detail-label {
  color: rgba(255, 255, 255, 0.6);
}

.error-details .detail-content {
  color: var(--error);
  font-family: monospace;
  font-size: var(--text-xs);
  background: rgba(var(--error-rgb), 0.1);
  padding: var(--space-xs);
  border-radius: var(--radius-xs);
}

.log-actions {
  display: flex;
  gap: var(--space-xs);
  align-items: flex-start;
  flex-shrink: 0;
}

.load-more-container {
  padding: var(--space-md);
  text-align: center;
  border-top: 1px solid var(--bg-secondary);
}



@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
}

.btn-sm {
  padding: var(--space-xs) var(--space-sm);
  font-size: var(--text-xs);
  min-height: 28px;
}

/* Stats grid improvements */
/* Mobile optimizations */
@media (max-width: 768px) {
  .log-item {
    padding: var(--space-sm);
    gap: var(--space-sm);
  }
  
  .log-icon {
    width: 24px;
    height: 24px;
    font-size: 12px;
  }
  
  .log-meta {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: var(--space-sm);
  }
  
  .stat-card {
    padding: var(--space-sm);
  }
  
  .log-details {
    padding: var(--space-sm);
  }
}

/* TMA specific styles */
.tma-environment .log-feed-container {
  max-height: 50vh;
}

.tma-environment .log-item {
  padding: var(--space-sm);
}

.tma-environment .log-icon {
  width: 20px;
  height: 20px;
  font-size: 10px;
}

.tma-environment .log-message {
  font-size: 12px;
}

.tma-environment .log-meta {
  font-size: 10px;
}

/* КРИТИЧЕСКИЕ ИСПРАВЛЕНИЯ КОНТРАСТНОСТИ - МАКСИМАЛЬНЫЙ ПРИОРИТЕТ */
/* Исправление для светлой темы - белый текст на белом фоне */
.agent-log-tab .log-message,
.log-feed .log-message,
.log-item .log-message {
  color: #1a1a1a !important;
  background: transparent !important;
}

.agent-log-tab .log-item,
.log-feed .log-item {
  background: #ffffff !important;
  border: 1px solid #e0e0e0 !important;
  color: #1a1a1a !important;
}

.agent-log-tab .log-item:hover,
.log-feed .log-item:hover {
  background: #f8f9fa !important;
}

/* Для темной темы TMA */
.tma-environment.tma-dark-theme .log-message {
  color: #ffffff !important;
}

.tma-environment.tma-dark-theme .log-item {
  background: #2d2d2d !important;
  border: 1px solid #404040 !important;
  color: #ffffff !important;
}
</style>