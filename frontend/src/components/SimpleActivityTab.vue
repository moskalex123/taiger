<template>
  <div class="simple-activity-tab">
    <h2>Журнал активности (Простая версия)</h2>
    
    <div class="debug-section">
      <h3>Отладочная информация:</h3>
      <pre>{{ debugInfo }}</pre>
    </div>
    
    <div class="test-section">
      <button @click="addTestData" class="btn-test">Добавить тестовые данные</button>
      <button @click="clearData" class="btn-test">Очистить данные</button>
      <button @click="refreshData" class="btn-test">Обновить реальные данные</button>
      <button @click="testAPI" class="btn-test">Тест API</button>
    </div>
    
    <div class="logs-section">
      <h3>Логи ({{ localLogs.length }}):</h3>
      <div v-if="localLogs.length === 0" class="empty-state">
        <div class="empty-icon">📝</div>
        <div class="empty-title">Логи активности отсутствуют</div>
        <div class="empty-description">
          Логи активности агента появятся здесь в реальном времени.<br>
          Запустите агента для просмотра его работы и статуса.
        </div>
        <div class="empty-actions">
          <button @click="refreshData" class="btn-refresh">🔄 Обновить</button>
          <button @click="addDemoData" class="btn-demo">✨ Добавить демо-данные</button>
        </div>
      </div>
      <div v-else>
        <div v-for="log in localLogs" :key="log.id" class="log-item">
          <div class="log-time">{{ formatTime(log.timestamp) }}</div>
          <div class="log-level" :class="`level-${log.level}`">{{ log.level }}</div>
          <div class="log-message">{{ log.message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted, watch } from 'vue'

console.log('🎯 SimpleActivityTab: Script loading')

// Add immediate debug info
setTimeout(() => {
  console.log('🎯 SimpleActivityTab: Initial check after 1 second')
}, 1000)

// Inject data from parent
const userInfo = inject<any>('userInfo', ref(null))
const scheduledPosts = inject<any>('scheduledPosts', ref([]))
const realtimeLogs = inject<any>('realtimeLogs', ref([]))
const workerErrors = inject<any>('workerErrors', ref([]))
const fetchScheduledPosts = inject<any>('fetchScheduledPosts', async () => {})
const fetchWorkerErrors = inject<any>('fetchWorkerErrors', async () => {})

console.log('🎯 SimpleActivityTab: Injected data:', {
  userInfo: userInfo?.value,
  scheduledPosts: scheduledPosts?.value,
  realtimeLogs: realtimeLogs?.value,
  workerErrors: workerErrors?.value
})

// Local state
const localLogs = ref([])

// Debug info
const debugInfo = computed(() => ({
  userInfo: userInfo?.value?.id || 'no user',
  scheduledPosts: scheduledPosts?.value?.length || 0,
  realtimeLogs: realtimeLogs?.value?.length || 0,
  workerErrors: workerErrors?.value?.length || 0,
  localLogs: localLogs.value.length,
  token: localStorage.getItem('auth_token') ? 'EXISTS' : 'MISSING',
  isTMA: window.Telegram?.WebApp ? 'YES' : 'NO',
  environment: window.location.hostname
}))

// Methods
const addTestData = () => {
  console.log('🎯 SimpleActivityTab: Adding test data')
  localLogs.value.push(
    {
      id: Date.now() + 1,
      level: 'info',
      message: 'Тестовое сообщение: Агент готов',
      timestamp: new Date().toISOString()
    },
    {
      id: Date.now() + 2,
      level: 'success',
      message: 'Тестовое сообщение: Операция выполнена',
      timestamp: new Date(Date.now() - 60000).toISOString()
    },
    {
      id: Date.now() + 3,
      level: 'error',
      message: 'Тестовое сообщение: Произошла ошибка',
      timestamp: new Date(Date.now() - 120000).toISOString()
    }
  )
}

const clearData = () => {
  localLogs.value = []
}

const refreshData = async () => {
  console.log('🎯 SimpleActivityTab: Refreshing realtime logs only...')
  try {
    // Получаем только живые логи через HTTP API как fallback
    const response = await fetch('/api/logs/realtime', {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      }
    })
    if (response.ok) {
      const logs = await response.json()
      if (Array.isArray(logs)) {
        // Фильтруем пустые сообщения
        const validLogs = logs.filter(log => 
          log && log.message && log.message.trim() !== '' && log.message !== 'Пустое сообщение'
        )
        if (validLogs.length > 0 && realtimeLogs.value) {
          realtimeLogs.value.splice(0, realtimeLogs.value.length, ...validLogs)
        }
      }
    }
    console.log('🎯 SimpleActivityTab: Realtime logs refreshed')
  } catch (error) {
    console.error('🎯 SimpleActivityTab: Error refreshing realtime logs:', error)
  }
}

const addDemoData = () => {
  console.log('🎯 SimpleActivityTab: Adding demo data for better UX')
  
  // Добавляем демо-данные прямо в локальные логи
  const demoLogs = [
    {
      id: 'demo-1',
      level: 'success',
      message: '✅ Пост успешно опубликован в канале @demo_channel',
      timestamp: new Date().toISOString()
    },
    {
      id: 'demo-2', 
      level: 'info',
      message: '📝 Запланирован пост: "Анализ рынка криптовалют на сегодня"',
      timestamp: new Date(Date.now() - 300000).toISOString() // 5 минут назад
    },
    {
      id: 'demo-3',
      level: 'success', 
      message: '🎯 Агент обработал 3 новых сообщения',
      timestamp: new Date(Date.now() - 600000).toISOString() // 10 минут назад
    },
    {
      id: 'demo-4',
      level: 'error',
      message: '❌ Ошибка: Недостаточно средств для публикации поста',
      timestamp: new Date(Date.now() - 900000).toISOString() // 15 минут назад
    },
    {
      id: 'demo-5',
      level: 'info',
      message: '🔄 Агент запущен и готов к работе',
      timestamp: new Date(Date.now() - 1800000).toISOString() // 30 минут назад
    }
  ]
  
  localLogs.value = demoLogs
  console.log('🎯 SimpleActivityTab: Demo data added:', demoLogs.length, 'logs')
}

const testAPI = async () => {
  console.log('🎯 SimpleActivityTab: Testing API directly...')
  
  // Check token
  const token = localStorage.getItem('auth_token')
  console.log('🎯 SimpleActivityTab: Token:', token ? `${token.substring(0, 20)}...` : 'NO TOKEN')
  
  // Test API calls directly
  try {
    const headers = token ? { Authorization: `Bearer ${token}` } : {}
    
    console.log('🎯 SimpleActivityTab: Testing /api/workers/logs/scheduled_posts')
    const response1 = await fetch('/api/workers/logs/scheduled_posts', {
      headers,
      credentials: 'include'
    })
    console.log('🎯 SimpleActivityTab: scheduled_posts response:', response1.status, await response1.text())
    
    console.log('🎯 SimpleActivityTab: Testing /api/workers/logs/errors')
    const response2 = await fetch('/api/workers/logs/errors', {
      headers,
      credentials: 'include'
    })
    console.log('🎯 SimpleActivityTab: errors response:', response2.status, await response2.text())
    
  } catch (error) {
    console.error('🎯 SimpleActivityTab: API test error:', error)
  }
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString()
}

// Watch injected data - ТОЛЬКО живые логи
watch([realtimeLogs], ([logs]) => {
  console.log('🎯 SimpleActivityTab: Realtime logs changed:', {
    logs: logs?.length || 0
  })
  
  // Sync ТОЛЬКО живые логи, фильтруем пустые сообщения
  const allData = []
  
  if (logs && Array.isArray(logs)) {
    const validLogs = logs.filter(log => 
      log && log.message && log.message.trim() !== '' && log.message !== 'Пустое сообщение'
    )
    
    allData.push(...validLogs.map(log => ({
      id: `realtime-${log.id}`,
      level: log.level || 'info',
      message: log.message,
      timestamp: log.timestamp
    })))
  }
  
  // НЕ добавляем posts и errors из базы - только живые логи!
  
  localLogs.value = allData.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
}, { deep: true, immediate: true })

onMounted(() => {
  console.log('🎯 SimpleActivityTab: Component mounted')
})
</script>

<style scoped>
.simple-activity-tab {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.debug-section {
  background: #f5f5f5;
  padding: 10px;
  border-radius: 5px;
  margin-bottom: 20px;
}

.debug-section pre {
  margin: 0;
  font-size: 12px;
}

.test-section {
  margin-bottom: 20px;
}

.btn-test {
  background: #007bff;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  margin-right: 10px;
  cursor: pointer;
}

.btn-test:hover {
  background: #0056b3;
}

.logs-section {
  border: 1px solid #ddd;
  border-radius: 5px;
  padding: 15px;
}

.log-item {
  display: flex;
  gap: 10px;
  padding: 8px;
  border-bottom: 1px solid #eee;
  align-items: flex-start;
}

.log-time {
  font-size: 12px;
  color: #666;
  min-width: 120px;
}

.log-level {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
  min-width: 60px;
  text-align: center;
}

.level-info {
  background: #d1ecf1;
  color: #0c5460;
}

.level-success {
  background: #d4edda;
  color: #155724;
}

.level-error {
  background: #f8d7da;
  color: #721c24;
}

.log-message {
  flex: 1;
  font-size: 14px;
  color: #1a1a1a;
}

.empty-state {
  text-align: center;
  color: #666;
  padding: 40px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #333;
}

.empty-description {
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: 20px;
}

.empty-actions {
  margin-top: 20px;
}

.btn-refresh {
  background: #28a745;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
}

.btn-refresh:hover {
  background: #218838;
}

.btn-demo {
  background: #6f42c1;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  margin-left: 10px;
}

.btn-demo:hover {
  background: #5a32a3;
}

/* TMA Environment Fixes */
.tma-environment .log-message {
  color: #1a1a1a !important;
  font-weight: 500 !important;
}

.tma-environment.tma-dark-theme .log-message {
  color: #ffffff !important;
}

.tma-environment .log-time {
  color: #666666 !important;
}

.tma-environment.tma-dark-theme .log-time {
  color: #b0b0b0 !important;
}

.tma-environment .empty-title {
  color: #1a1a1a !important;
}

.tma-environment.tma-dark-theme .empty-title {
  color: #ffffff !important;
}

.tma-environment .empty-description {
  color: #666666 !important;
}

.tma-environment.tma-dark-theme .empty-description {
  color: #b0b0b0 !important;
}

/* Исправление для светлой темы - белый текст на белом фоне */
.log-message {
  color: #1a1a1a !important; /* Темный текст для светлого фона */
}

.log-time {
  color: #666666 !important; /* Серый текст для времени */
}

.empty-title {
  color: #1a1a1a !important; /* Темный текст для заголовка */
}

.empty-description {
  color: #666666 !important; /* Серый текст для описания */
}

/* Для обычного режима (не TMA) тоже исправляем */
.log-item {
  background-color: #ffffff; /* Белый фон для элементов лога */
  border: 1px solid #e0e0e0; /* Легкая граница */
  margin-bottom: 4px;
  border-radius: 4px;
}

.logs-section {
  background-color: #f8f9fa; /* Светло-серый фон для секции логов */
}
</style>