<template>
  <div class="dashboard">
    <h2>{{ $t('dashboard') }}</h2>
    
    <!-- Three blocks in one row -->
    <div class="dashboard-info">
      <!-- Avatar block -->
      <div class="avatar-block">
        <img :src="userInfo?.avatar_url || '/avatars/default.png'" alt="User Avatar" class="user-avatar" />
      </div>
      
      <!-- User info block -->
      <div class="user-info-block">
        <div v-if="userInfo">
          <div class="username">{{ userInfo?.username }} (ID: {{ userInfo?.id }})</div>
          <div v-if="userInfo?.balance !== undefined" class="balance" :class="{ 'balance-updated': balanceUpdated }">
            {{ $t('balance') }}: 
            <PriceDisplay 
              :price="userInfo.balance" 
              :price-class="getBalanceColorClass(userInfo.balance)"
              :show-exchange-info="true"
              :decimals="1"
            />
          </div>
          <div v-if="userInfo" class="vip-level" :style="vipStyles.getVipStyle(userInfo.VIP_level || 0)">{{ $t('vip_level') }}: {{ userInfo?.VIP_level || 0 }}</div>
        </div>
      </div>
      
      <!-- Worker status block -->
      <div class="worker-block" id="worker-controls">
        <div v-if="loading" class="loading">{{ $t('loading') }}</div>
        <div v-else-if="error" class="error-message">
          <p>{{ $t('error') }}: {{ error }}</p>
        </div>
        <div v-else class="worker-status">
          <div class="worker-status-line">{{ $t('status_of_worker') }}{{ userInfo?.id }}: <span :class="statusClass">{{ workerStatusDisplay }}</span></div>
          <div class="controls">
            <div class="worker-control-button">
              <button 
                @click="toggleWorker" 
                :disabled="isButtonDisabled"
                :class="['control-button', isWorkerRunning ? 'button-stop' : 'button-start', { 'button-loading': isWorkerToggling || workerInTransitionalState }]"
                :title="getWorkerButtonTitle">
                <svg v-if="isWorkerToggling || workerInTransitionalState" class="icon spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M21 12a9 9 0 11-6.219-8.56"/>
                </svg>
                <svg v-else-if="isWorkerRunning" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <rect x="6" y="6" width="12" height="12"/>
                </svg>
                <svg v-else class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <polygon points="5,3 19,12 5,21 5,3"/>
                </svg>
                <span class="button-text">{{ getWorkerButtonText }}</span>
              </button>
            </div>
          </div>
          <div v-if="!hasChannelRules" class="warning-message">
            {{ $t('cannot_start_no_rules') }}
          </div>
          <div v-if="workerData?.status === 'auth_required'" class="auth-required-message">
            {{ $t('auth_required_message') }}
            <button @click="logout" class="logout-button">{{ $t('logout_and_reauth') }}</button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- Logs Section -->
    <div class="logs-section" id="logs">
      <h3>{{ $t('logs') }}</h3>
      <div class="logs-container">
        <ul class="unified-logs">
          <!-- Real-time logs (highest priority) -->
          <li v-for="log in realtimeLogs" :key="'realtime-' + log.id" class="log-entry" :class="log.level">
            <span class="log-icon" :class="{
              'success-icon': log.level === 'success',
              'error-icon': log.level === 'error',
              'warning-icon': log.level === 'warning',
              'info-icon': log.level === 'info'
            }">
              {{ log.level === 'success' ? '✓' : log.level === 'error' ? '✗' : log.level === 'warning' ? '⚠' : 'ℹ' }}
            </span>
            <span class="log-content">
              <strong>{{ formatSimpleDateTime(log.timestamp) }}</strong>: {{ isPostContentMessage(log.message) ? log.message : translateLogMessage(log.message) }}
            </span>
          </li>
          
          <!-- Scheduled posts from database -->
          <li v-for="post in scheduledPosts" :key="'post-' + post.id" class="log-entry" :class="post.status === 'insufficient_funds' ? 'error' : 'success'">
            <span v-if="post.status === 'insufficient_funds'" class="log-icon error-icon">✗</span>
            <span v-else class="log-icon success-icon">✓</span>
            <span class="log-content">
              <span v-if="post.status === 'insufficient_funds'">{{ formatSimpleDateTime(post.scheduled_at) }}: {{ post.content }}</span>
              <span v-else>{{ $t('log_scheduled') }}: {{ formatSimpleDateTime(post.scheduled_at) }}: {{ post.content || $t('no_content') }}</span>
            </span>
          </li>
          
          <!-- Worker errors from database -->
          <li v-for="error in workerErrors" :key="'error-' + error.id" class="log-entry error">
            <span class="log-icon error-icon">✗</span>
            <span class="log-content">
              {{ formatSimpleDateTime(error.timestamp) }} - 
              <span v-if="error.error_type === 'InsufficientFunds'" class="insufficient-funds-error">
                {{ $t('insufficient_funds_detected') }}: {{ error.error_message }}
              </span>
              <span v-else>
                {{ error.error_type }}: {{ error.error_message }}
              </span>
            </span>
          </li>
        </ul>
      </div>
    </div>
    
    <!-- Worker Log Section - Hidden to avoid UI confusion -->
    <!-- 
    <div class="worker-log-section" v-if="isWorkerRunning">
      <h3>📋 {{ $t('worker_log') }}</h3>
      
      <div class="log-container" ref="logContainer">
        <div 
          v-for="(log, index) in workerLogs" 
          :key="index"
          class="log-entry"
          :class="getLogClass(log.message)"
        >
          <span class="log-timestamp">{{ log.timestamp }}</span>
          <span class="log-message">{{ log.message }}</span>
        </div>
        
        <div v-if="workerLogs.length === 0" class="no-logs">
          {{ $t('log_empty') }}
        </div>
      </div>
      
      <div class="log-controls">
        <button @click="clearLogs" class="btn-secondary">{{ $t('clear_log') }}</button>
        <button @click="downloadLogs" class="btn-secondary">{{ $t('download_log') }}</button>
      </div>
    </div>
    -->

    <!-- Channel Pairs Management -->
    <div id="channel-rules">
      <ChannelPairs 
        ref="channelPairsRef"
        @rule-created-successfully="handleRuleCreated" 
        :preloaded-channels="{ subscribed: subscribedChannels, admin: adminChannels }"
        :channels-loaded="channelsLoaded"
      />
    </div>
    
    <!-- Auth Required Modal -->
    <div v-if="showAuthRequiredModal" class="modal-overlay" @click="closeAuthModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>🔐 {{ $t('auth_required_title') || 'Session Expired' }}</h3>
          <button @click="closeAuthModal" class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <p>{{ $t('auth_required_modal_message') || 'Your Telegram session has expired and is no longer valid.' }}</p>
          <p class="modal-instruction">{{ $t('auth_required_instruction') || 'To continue using the service, please log out and log back in to re-authenticate your Telegram account.' }}</p>
        </div>
        <div class="modal-footer">
          <button @click="logout" class="modal-button primary">{{ $t('logout_and_reauth') }}</button>
          <button @click="closeAuthModal" class="modal-button secondary">{{ $t('close') }}</button>
        </div>
      </div>
    </div>
    
    <!-- Notification Container -->
    <NotificationContainer />
    
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, defineExpose } from 'vue';
import axios from 'axios';
import ChannelPairs from './ChannelPairs.vue'; // Import the new component
import PriceDisplay from './PriceDisplay.vue'; // Import price display component
import NotificationContainer from './NotificationContainer.vue'; // Import notification container
import { useI18n } from 'vue-i18n';

import { useVipStyles } from '../composables/useVipStyles';

// Initialize i18n
const { t: $t, locale } = useI18n();

// Define a more specific type for workerData if possible
interface WorkerData {
  status: 'running' | 'stopped' | 'error' | 'not_configured' | 'auth_required' | 'pending' | string; // Add other possible statuses
  pid?: number | null;
  last_started?: string | null; // Changed from last_started_at to match API
  last_activity_at?: string | null; // Assuming this might also come from the API
  queue_position?: number; // Add queue_position property
  error_message?: string; // Add error_message property for auth_required status
  remaining_seconds?: number; // Add remaining_seconds property
}

interface UserInfo {
  id: number;
  username: string;
  balance?: number; // Add balance property
  avatar_url?: string; // Add avatar_url property
  VIP_level?: number; // Add VIP_level property
}

interface ScheduledPost {
  id: number;
  scheduled_at: string;
  content: string;
  status: string;
}

interface WorkerError {
  id: number;
  timestamp: string;
  error_type: string;
  error_message: string;
}

// Define emits
const emit = defineEmits<{
  'rule-created-successfully': [channelInfo: { sourceChannel: string, targetChannel: string }]
}>()

const workerData = ref<WorkerData | null>(null);
const userInfo = ref<UserInfo | null>(null); // Explicitly typed
const loading = ref(true);
const error = ref<string | null>(null);
const isStarting = ref(false);
const isStartLocked = ref(false);
const isStopping = ref(false);
const isWorkerToggling = computed(() => isStartLocked.value || isStopping.value);
const hasChannelRules = ref(false);
const autoStopTimer = ref<number | null>(null);
const scheduledPosts = ref<ScheduledPost[]>([]);
const workerErrors = ref<WorkerError[]>([]);
const balanceUpdated = ref(false);
const previousPostsCount = ref(0);
const realtimeLogs = ref<any[]>([]);
const websocket = ref<WebSocket | null>(null);
const showAuthRequiredModal = ref(false);
const websocketConnected = ref(false);
const fallbackLogTimer = ref<number | null>(null);
const workerLogs = ref<any[]>([]);
const channelPairsRef = ref<InstanceType<typeof ChannelPairs> | null>(null);

const lockWorkerStart = () => {
  isStartLocked.value = true;
  isStarting.value = true;
};

const releaseWorkerStartLock = () => {
  if (isStartLocked.value) {
    isStartLocked.value = false;
  }
  if (isStarting.value) {
    isStarting.value = false;
  }
};

// Channel state for dashboard display
interface ChannelInfo {
  id: number;
  title: string;
  username?: string;
  photo_url?: string;
  type: string;
  is_admin: boolean;
}

const subscribedChannels = ref<ChannelInfo[]>([]);
const adminChannels = ref<ChannelInfo[]>([]);
const channelsLoaded = ref(false);
const loadingChannels = ref(false);

// Use VIP styles composable
const vipStyles = useVipStyles();

// Function to determine balance color class
const getBalanceColorClass = (balance: number) => {
  if (balance >= 1) return 'balance-green';
  if (balance >= 0.1) return 'balance-yellow';
  return 'balance-red';
};

// Function to format date time in simple format (day/month hours/minutes)
const formatSimpleDateTime = (dateTimeString: string) => {
  const date = new Date(dateTimeString);
  const day = date.getDate().toString().padStart(2, '0');
  const month = (date.getMonth() + 1).toString().padStart(2, '0');
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return day + '/' + month + ' ' + hours + ':' + minutes;
};

// Function to check if message contains post content that should not be translated
const isPostContentMessage = (message: string) => {
  // Check if message is about scheduling with output text (contains post content)
  return message.includes('Выходной текст:') || 
         message.includes('Output text:') ||
         message.includes('Сообщение запланировано:') ||
         message.includes('Message scheduled:');
};

// Function to translate log messages to current language
const translateLogMessage = (message: string) => {
  // Return original message if English is selected
  if (locale.value !== 'ru') {
    return message;
  }

  // Comprehensive translation map for Russian
  const translations: { [key: string]: string } = {
    // Dashboard messages
    'Dashboard connected to real-time logs': 'Панель управления подключена к журналу в реальном времени',
    'Using fallback mode for real-time logs (WebSocket unavailable)': 'Использование резервного режима для логов (WebSocket недоступен)',
    
    // Worker status messages (with and without emojis)
    '⏳ Worker is now idle and waiting for new messages': '⏳ Агент готов и ожидает новые сообщения',
    'Worker is now idle and waiting for new messages': 'Агент готов и ожидает новые сообщения',
    '🔗 Connecting to Telegram...': '🔗 Подключение к Telegram...',
    'Connecting to Telegram...': 'Подключение к Telegram...',
    '🚀 Worker initialized successfully': '🚀 Агент успешно инициализирован',
    'Worker initialized successfully': 'Агент успешно инициализирован',
    '✅ Worker ready and waiting for new messages': '✅ Агент готов и ожидает новые сообщения',
    'Worker ready and waiting for new messages': 'Агент готов и ожидает новые сообщения',
    
    // Connection messages
    'Worker connected to Telegram and ready to process messages': 'Агент подключился к Telegram и готов обрабатывать сообщения',
    'Message handler registered for all message types': 'Обработчик сообщений зарегистрирован для всех типов сообщений',
    'Worker is ready and listening for messages': 'Агент готов и прослушивает сообщения',
    'Connection established': 'Соединение установлено',
    'Connection lost': 'Соединение потеряно',
    'Reconnecting...': 'Переподключение...',
    
    // Processing messages
    'Worker started successfully': 'Агент успешно запущен',
    'Worker stopped': 'Агент остановлен',
    'Processing message': 'Обработка сообщения',
    'Message sent successfully': 'Сообщение успешно отправлено',
    'Error processing message': 'Ошибка при обработке сообщения',
    
    // Batch processing messages
    '✅ Batch processing completed': '✅ Пакетная обработка завершена',
    'Batch processing completed': 'Пакетная обработка завершена',
    '🔄 Starting batch processing of accumulated posts': '🔄 Начинается пакетная обработка накопленных постов',
    'Starting batch processing of accumulated posts': 'Начинается пакетная обработка накопленных постов',
    
    // Rule processing messages  
    '✅ Rule 1: processed 1 posts': '✅ Правило 1: обработан 1 пост',
    '✅ Rule 2: processed 1 posts': '✅ Правило 2: обработан 1 пост', 
    '✅ Rule 3: processed 1 posts': '✅ Правило 3: обработан 1 пост',
    '✅ Rule 4: processed 1 posts': '✅ Правило 4: обработан 1 пост',
    
    // Error messages
    'Insufficient funds': 'Недостаточно средств',
    'Authentication failed': 'Ошибка аутентификации',
    'Rate limit exceeded': 'Превышен лимит запросов',
    'Network error': 'Ошибка сети'
  };

  // Check for exact match first
  if (translations[message]) {
    return translations[message];
  }

  // Handle messages that might have slight variations or extra characters
  // Remove emojis and extra spaces for matching
  const cleanMessage = message.replace(/[^\w\s]/g, '').trim().toLowerCase();
  const cleanTranslations: { [key: string]: string } = {};
  
  // Create clean versions of translation keys
  Object.keys(translations).forEach(key => {
    const cleanKey = key.replace(/[^\w\s]/g, '').trim().toLowerCase();
    cleanTranslations[cleanKey] = translations[key];
  });
  
  if (cleanTranslations[cleanMessage]) {
    return cleanTranslations[cleanMessage];
  }

  // Additional pattern matching for common messages
  if (message.toLowerCase().includes('worker is now idle') || message.toLowerCase().includes('waiting for new messages')) {
    return 'Агент готов и ожидает новые сообщения';
  }
  
  if (message.toLowerCase().includes('connecting to telegram')) {
    return 'Подключение к Telegram...';
  }
  
  if (message.toLowerCase().includes('worker initialized successfully')) {
    return 'Агент успешно инициализирован';
  }

  // Handle dynamic messages with patterns based on current locale
  if (message.startsWith('Processing: ')) {
    if (locale.value === 'ru') {
      return message.replace('Processing: True', 'Обработка: Включена').replace('Processing: False', 'Обработка: Отключена').replace('Rules:', 'Правил:');
    }
    return message;
  }

  if (message.startsWith('Authorized as ')) {
    if (locale.value === 'ru') {
      return message.replace('Authorized as', 'Авторизован как');
    }
    return message;
  }

  // Translations for successful processing messages
  if (message.includes('Post processed successfully:')) {
    if (locale.value === 'ru') {
      return message.replace('Post processed successfully:', 'Пост успешно обработан:');
    }
    return message;
  }

  if (message.includes('Message scheduled:')) {
    if (locale.value === 'ru') {
      return message.replace('Message scheduled:', 'Сообщение запланировано:');
    }
    return message;
  }

  if (message.includes('Media scheduled:')) {
    if (locale.value === 'ru') {
      return message.replace('Media scheduled:', 'Медиа запланировано:');
    }
    return message;
  }

  // Translations for message receiving and processing
  if (message.includes('New message') && message.includes('from')) {
    if (locale.value === 'ru') {
      return message.replace('New message', 'Новое сообщение').replace('from', 'из');
    }
    return message;
  }

  if (message.includes('Checking message') && message.includes('against') && message.includes('rules')) {
    if (locale.value === 'ru') {
      return message.replace('Checking message', 'Проверка сообщения').replace('against', 'по').replace('rules', 'правилам');
    }
    return message;
  }

  if (message.includes('matches rule')) {
    if (locale.value === 'ru') {
      return message.replace('matches rule', 'соответствует правилу');
    }
    return message;
  }

  if (message.includes('No rules matched')) {
    if (locale.value === 'ru') {
      return message.replace('No rules matched for message', 'Ни одно правило не подошло для сообщения');
    }
    return message;
  }

  // Translations for connection
  if (message.includes('Connected to Telegram as')) {
    if (locale.value === 'ru') {
      return message.replace('Connected to Telegram as', 'Подключен к Telegram как');
    }
    return message;
  }

  // Translations for errors
  if (message.includes('AI API Error')) {
    if (locale.value === 'ru') {
      return message.replace('AI API Error', 'Ошибка AI API');
    }
    return message;
  }

  if (message.includes('AI processing failed')) {
    if (locale.value === 'ru') {
      return message.replace('AI processing failed', 'Ошибка обработки AI');
    }
    return message;
  }

  if (message.includes('Content processing failed')) {
    if (locale.value === 'ru') {
      return message.replace('Content processing failed', 'Ошибка обработки контента');
    }
    return message;
  }

  if (message.includes('Error processing rule')) {
    if (locale.value === 'ru') {
      return message.replace('Error processing rule', 'Ошибка обработки правила');
    }
    return message;
  }

  if (message.includes('Schedule time calculation failed')) {
    if (locale.value === 'ru') {
      return message.replace('Schedule time calculation failed', 'Ошибка расчета времени планирования');
    }
    return message;
  }

  if (message.includes('Telegram Flood Limit')) {
    if (locale.value === 'ru') {
      return message.replace('Telegram Flood Limit', 'Лимит Telegram превышен');
    }
    return message;
  }

  if (message.includes('Cannot Schedule to Channel')) {
    if (locale.value === 'ru') {
      return message.replace('Cannot Schedule to Channel', 'Невозможно запланировать в канал');
    }
    return message;
  }

  // If no translation found, return original message (this preserves post content)
  return message;
};

// VIP timeout settings from .env (in minutes)
const VIP_TIMEOUTS = {
  0: 5,  // VIP_0_TIMEOUT=5
  1: 10, // VIP_1_TIMEOUT=10
  2: 20, // VIP_2_TIMEOUT=20
  3: 30  // VIP_3_TIMEOUT=30
} as const;

// Auto-stop functionality
const startAutoStopTimer = () => {
  if (autoStopTimer.value) {
    clearTimeout(autoStopTimer.value);
  }
  
  const vipLevel = userInfo.value?.VIP_level ?? 0;
  const timeoutMinutes = VIP_TIMEOUTS[vipLevel as keyof typeof VIP_TIMEOUTS] || VIP_TIMEOUTS[0];
  const timeoutMs = timeoutMinutes * 60 * 1000;
  
  autoStopTimer.value = setTimeout(async () => {
    if (workerData.value?.status === 'running' || workerData.value?.status === 'active') {
      console.log(`Auto-stopping worker after ${timeoutMinutes} minutes (VIP level ${vipLevel})`);
      await stopWorker();
    }
  }, timeoutMs);
};

const clearAutoStopTimer = () => {
  if (autoStopTimer.value) {
    clearTimeout(autoStopTimer.value);
    autoStopTimer.value = null;
  }
};

const fetchUserInfo = async () => {
  try {
    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const response = await axios.get('/api/users/me', { 
      withCredentials: true,
      headers
    });
    const previousBalance = userInfo.value?.balance;
    userInfo.value = response.data;
    
    // Log balance changes for debugging and trigger animation
    if (previousBalance !== undefined && userInfo.value && previousBalance !== userInfo.value.balance) {
      console.log(`Balance updated: ${previousBalance} -> ${userInfo.value.balance}`);
      balanceUpdated.value = true;
      setTimeout(() => {
        balanceUpdated.value = false;
      }, 2000); // Animation duration
    }
    
    // Auto-stop worker if balance becomes negative
    if (userInfo.value && userInfo.value.balance !== undefined && userInfo.value.balance < 0) {
      if (workerData.value?.status === 'running' || workerData.value?.status === 'active') {
        console.log('Auto-stopping worker due to negative balance');
        await stopWorker();
      }
    }
    
    // Clear error message if balance becomes positive (to unblock start button)
    if (userInfo.value && userInfo.value.balance !== undefined && userInfo.value.balance >= 0) {
      if (error.value === $t('negative_balance_error')) {
        error.value = null;
        console.log('Balance is now positive, clearing negative balance error');
      }
    }
  } catch (err) {
    console.error('Failed to fetch user info:', err);
    // error.value = 'Не удалось загрузить информацию о пользователе.';
    // Перенаправление на главную страницу или страницу логина, если информация о пользователе критична
    // window.location.href = '/'; 
  }
};

const fetchScheduledPosts = async () => {
  try {
    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const response = await axios.get('/api/workers/logs/scheduled_posts', { 
      withCredentials: true,
      headers
    });
    const newPosts = response.data;
    
    // Check if there are new posts and play sound
    if (newPosts.length > previousPostsCount.value && previousPostsCount.value > 0) {
      await playSound('work');
    }
    
    previousPostsCount.value = newPosts.length;
    scheduledPosts.value = newPosts;
  } catch (err) {
    console.error('Failed to fetch scheduled posts:', err);
  }
};

const fetchWorkerErrors = async () => {
  try {
    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const response = await axios.get('/api/workers/logs/errors', { 
      withCredentials: true,
      headers
    });
    workerErrors.value = response.data;
  } catch (err) {
    console.error('Failed to fetch worker errors:', err);
  }
};

const connectWebSocket = () => {
  if (!userInfo.value?.id) return;
  
  // Определяем правильный WebSocket URL
  // В production (включая TMA) используем nginx proxy без порта
  // В режиме разработки используем API сервер на порту 8000
  let host = window.location.host;
  let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // Для TMA и production используем nginx proxy (без порта 8000)
  if (window.Telegram && window.Telegram.WebApp || !host.includes(':5173')) {
    // Убираем порт из хоста если он есть (используем nginx proxy)
    if (host.includes(':')) {
      host = host.split(':')[0];
    }
    // Используем стандартный порт (через nginx)
    // protocol остается как есть (wss: для https, ws: для http)
  } else {
    // Режим разработки - подключаемся напрямую к бэкенду
    if (host.includes(':5173')) {
      host = host.replace(':5173', ':8000');
    }
  }
  
  const wsUrl = protocol + '//' + host + '/api/ws/' + userInfo.value.id;
  
  console.log('Connecting to WebSocket:', wsUrl);
  websocket.value = new WebSocket(wsUrl);
  
  // Запустить fallback через 5 секунд, если WebSocket не подключился
  setTimeout(() => {
    if (!websocketConnected.value) {
      console.log('WebSocket failed to connect within 5 seconds, starting fallback');
      startFallbackLogUpdates();
    }
  }, 5000);
  
  websocket.value.onopen = () => {
    console.log('WebSocket connected for real-time logs');
    console.log('WebSocket readyState:', websocket.value?.readyState);
    websocketConnected.value = true;
    
    // Остановить fallback таймер, если WebSocket подключен
    if (fallbackLogTimer.value) {
      clearInterval(fallbackLogTimer.value);
      fallbackLogTimer.value = null;
    }
  };
  
  websocket.value.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      if (data.type === 'worker_log') {
        // Handle worker log messages for hybrid processing
        handleWorkerLog(data);
      } else if (data.type === 'log') {
        // Handle new format with localization keys
        let message = data.message;
        if (data.message_key) {
          // Use localization key with parameters
          message = $t(data.message_key, data.message_params || {});
        } else {
          // Fallback: translate message using translateLogMessage for messages without key
          // BUT do not translate post content in scheduling messages
          if (!isPostContentMessage(message)) {
            message = translateLogMessage(message);
          }
        }
        
        // Check for duplicates before adding (more precise check)
        const isDuplicate = realtimeLogs.value.some(log => 
          log.message === message && 
          log.log_type === data.log_type &&
          Math.abs(new Date(log.timestamp).getTime() - new Date(data.timestamp).getTime()) < 1000 // Within 1 second
        );
        
        // Only add if not duplicate
        if (!isDuplicate) {
          // Add new log to the beginning of the array
          realtimeLogs.value.unshift({
            id: Date.now(),
            timestamp: data.timestamp,
            log_type: data.log_type,
            level: data.level,
            message: message
          });
          
          // Keep only last 50 logs
          if (realtimeLogs.value.length > 50) {
            realtimeLogs.value = realtimeLogs.value.slice(0, 50);
          }
        }
        
        // Check for Telegram session errors and show modal
        if (data.log_type === 'auth_required' || 
            (data.message_key && (data.message_key === 'log_session_expired' || data.message_key === 'log_telegram_session_expired')) ||
            (data.message && (data.message.includes('Session expired') || data.message.includes('Telegram session expired')))) {
          console.log('🔐 Telegram session error detected, showing auth modal');
          showAuthRequiredModal.value = true;
        }
        
        // Play sound for important events
        if (data.level === 'success' || data.log_type === 'worker_ready') {
          playSound('work');
        } else if (data.level === 'error') {
          playSound('stop');
        }
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  };
  
  websocket.value.onclose = (event) => {
    console.log('WebSocket disconnected, attempting to reconnect...');
    console.log('Close event:', event.code, event.reason);
    websocketConnected.value = false;
    
    // Запустить fallback механизм для мобильных устройств
    startFallbackLogUpdates();
    
    // Reconnect after 3 seconds
    setTimeout(connectWebSocket, 3000);
  };
  
  websocket.value.onerror = (error) => {
    console.error('WebSocket error:', error);
    console.log('WebSocket URL was:', wsUrl);
    console.log('WebSocket readyState:', websocket.value?.readyState);
    websocketConnected.value = false;
    
    // Запустить fallback механизм
    startFallbackLogUpdates();
  };
};

const disconnectWebSocket = () => {
  if (websocket.value) {
    websocket.value.close();
    websocket.value = null;
  }
  websocketConnected.value = false;
  
  // Остановить fallback таймер
  if (fallbackLogTimer.value) {
    clearInterval(fallbackLogTimer.value);
    fallbackLogTimer.value = null;
  }
};

const startFallbackLogUpdates = () => {
  // Не запускать fallback, если WebSocket подключен или таймер уже работает
  if (websocketConnected.value || fallbackLogTimer.value) {
    return;
  }
  
  console.log('Starting fallback log updates for mobile compatibility');
  
  // Добавить системное сообщение о fallback режиме
  realtimeLogs.value.unshift({
    id: Date.now(),
    timestamp: new Date().toISOString(),
    log_type: 'system',
    level: 'info',
    message: 'Using fallback mode for real-time logs (WebSocket unavailable)'
  });
  
  // Обновлять логи каждые 3 секунды через HTTP API
  fallbackLogTimer.value = setInterval(async () => {
    if (websocketConnected.value) {
      // WebSocket восстановился, остановить fallback
      clearInterval(fallbackLogTimer.value!);
      fallbackLogTimer.value = null;
      return;
    }
    
    try {
      // В fallback режиме получаем логи через HTTP API
      await fetchScheduledPosts();
      await fetchWorkerErrors();
      
      // Не вызываем fetchWorkerStatus здесь, чтобы избежать дублирования
    } catch (error) {
      console.error('Fallback log update failed:', error);
    }
  }, 3000);
};

// Remove duplicate simple playSound function - using the async version below

const fetchWorkerStatus = async () => {
  // loading.value = true; // Already set in onMounted or if called standalone
  // error.value = null; 
  try {
    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    // DEBUG: fetchWorkerStatus token check
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
      // DEBUG: Added Authorization header
    } else {
      console.log('DEBUG: No token, relying on cookies');
      // If no token, wait a bit and try once more (for TMA timing issues)
      await new Promise(resolve => setTimeout(resolve, 200));
      const retryToken = localStorage.getItem('auth_token');
      if (retryToken) {
        headers['Authorization'] = 'Bearer ' + retryToken;
        console.log('DEBUG: Found token on retry, added Authorization header');
      } else {
        console.log('DEBUG: Still no token after retry, using cookies only');
      }
    }
    
    // DEBUG: Making request to /api/workers/status with headers
    
    const response = await axios.get<WorkerData>('/api/workers/status', { 
      withCredentials: true,
      headers
    });
    const newStatus = response.data.status;
    const oldStatus = workerData.value?.status;
    
    workerData.value = response.data;
    console.log('Статус воркера получен:', response.data);
    
    // Force check for auth_required status
    if (response.data.status === 'auth_required') {
      console.log('🔐 FORCE CHECK: Status is auth_required, showing modal');
      console.log('Modal state before:', showAuthRequiredModal.value);
      showAuthRequiredModal.value = true;
      console.log('Modal state after:', showAuthRequiredModal.value);
      
      // Also check if modal element exists in DOM
      setTimeout(() => {
        const modalElement = document.querySelector('.modal-overlay');
        console.log('Modal element in DOM:', modalElement ? 'found' : 'not found');
        if (modalElement) {
          console.log('Modal element style:', (modalElement as HTMLElement).style.display);
        }
      }, 100);
    } else {
      console.log('Status is not auth_required:', response.data.status);
    }
    
    // Play sound when worker becomes active
    if (oldStatus && oldStatus !== newStatus) {
      if ((newStatus === 'running' || newStatus === 'active') && 
          oldStatus !== 'running' && oldStatus !== 'active') {
        console.log('Worker became active, playing work sound');
        await playSound('work');
      }
    }
    
    // Reset button loading states when status changes
    if (oldStatus !== newStatus) {
      if (newStatus === 'running' || newStatus === 'active') {
        if (isStartLocked.value || isStarting.value) {
          console.log('Worker became active, releasing start lock');
          releaseWorkerStartLock();
        }
      } else if (newStatus === 'error') {
        if (isStopping.value) {
          console.log('Worker became inactive, clearing isStopping state');
          isStopping.value = false;
        }
        // Также сбрасываем isStarting если воркер остановился с ошибкой
        if (isStartLocked.value || isStarting.value) {
          console.log('Worker stopped with error, releasing start lock');
          releaseWorkerStartLock();
        }
      }
      
      // Show auth required modal when status changes to auth_required
      if (newStatus === 'auth_required' && oldStatus !== 'auth_required') {
        showAuthRequiredModal.value = true;
        console.log('Showing auth required modal due to status change');
        // Сбрасываем isStarting при auth_required
        if (isStartLocked.value || isStarting.value) {
          console.log('Worker requires auth, releasing start lock');
          releaseWorkerStartLock();
        }
      }
    }
    
    // Also check for auth_required status on every status fetch
    if (newStatus === 'auth_required') {
      console.log('DEBUG: Worker status is auth_required, modal should be visible:', showAuthRequiredModal.value);
      console.log('DEBUG: Full worker data:', workerData.value);
      if (!showAuthRequiredModal.value) {
        showAuthRequiredModal.value = true;
        console.log('DEBUG: Showing auth required modal');
      }
    }
    
    // Debug all status changes
    
    
    // Debug all status changes
    
    
    // Debug all status changes
    
    
    // Если воркер остановлен, но кнопка все еще в состоянии остановки
    if ((newStatus === 'stopped' || newStatus === 'error' || newStatus === 'not_configured') && isStopping.value) {
      console.log('DEBUG: Worker is stopped but isStopping is still true, fixing...');
      isStopping.value = false;
    }
  } catch (err: any) {
    console.error('Ошибка при получении статуса воркера:', err);
    if (err.response && err.response.data && err.response.data.detail) {
      error.value = err.response.data.detail;
      // Ensure workerData is set to a state that reflects the error or not_configured status
      if (err.response.status === 404 && err.response.data.detail.includes("Worker not found")) {
        workerData.value = { status: 'not_configured' }; 
      } else {
        workerData.value = { status: 'error' }; 
      }
    } else {
      error.value = 'Couldn\'t get worker status.';
      workerData.value = { status: 'error' };
    }
    // Reset loading states on error
    isStarting.value = false;
    isStopping.value = false;
  } finally {
    loading.value = false; // Ensure loading is set to false in all paths
  }
};

const playSound = async (soundName: string) => {
  try {
    const audio = new Audio(`/sounds/${soundName}.mp3`);
    audio.volume = 0.5;
    
    // Preload the audio
    audio.load();
    
    // Wait for audio to be ready and play
    await new Promise((resolve, reject) => {
      audio.addEventListener('canplaythrough', resolve, { once: true });
      audio.addEventListener('error', reject, { once: true });
    });
    
    const playPromise = audio.play();
    if (playPromise !== undefined) {
      await playPromise;
      console.log(`Sound ${soundName} played successfully`);
    }
  } catch (e) {
    console.log(`Sound playback error for ${soundName}:`, e);
    // Fallback: try to play without waiting
    try {
      const fallbackAudio = new Audio(`/sounds/${soundName}.mp3`);
      fallbackAudio.volume = 0.3;
      fallbackAudio.play();
    } catch (fallbackError) {
      console.log('Fallback sound also failed:', fallbackError);
    }
  }
};

const startWorker = async () => {
  console.log('🚀 startWorker: Called with state:', {
    isStartLocked: isStartLocked.value,
    isStarting: isStarting.value,
    workerStatus: workerData.value?.status,
    hasChannelRules: hasChannelRules.value,
    userBalance: userInfo.value?.balance
  });
  
  if (isStartLocked.value || workerData.value?.status === 'running' || workerData.value?.status === 'active' || 
      workerData.value?.status === 'starting' || workerData.value?.status === 'pending' || workerData.value?.status === 'processing') {
    console.log('🚀 startWorker: Blocked by worker status or lock');
    return;
  }
  
  lockWorkerStart();
  let startRequestInitiated = false;
  const startTime = Date.now();
  
  try {
    // Check balance - only block if negative
    if (userInfo.value && userInfo.value.balance !== undefined && userInfo.value.balance < 0) {
      console.log('🚀 startWorker: Blocked by negative balance');
      error.value = $t('negative_balance_error');
      releaseWorkerStartLock();
      return;
    }

    // Refresh channel rules before checking to ensure we have the latest state
    console.log('🚀 startWorker: Refreshing channel rules before start...');
    await fetchChannelRules();

    if (!hasChannelRules.value) {
      console.log('🚀 startWorker: Blocked by no channel rules after refresh');
      error.value = $t('cannot_start_no_rules');
      releaseWorkerStartLock();
      return;
    }

    console.log('🚀 startWorker: All checks passed, starting worker...');
    error.value = null;

    console.log('Sending worker start request...');

    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    const headers: any = {};

    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }

    startRequestInitiated = true;
    const response = await axios.post('/api/workers/start', {}, { 
      withCredentials: true,
      headers
    });
    console.log(`Worker start request completed in ${Date.now() - startTime}ms`);

    // Play start sound
    await playSound('start');

    // Check if worker was queued or started immediately
    if (response.data.status === 'added_to_queue') {
      // Worker was added to queue
      console.log('Worker added to queue at position:', response.data.position);
      // Show notification that worker is starting
      // This would typically be handled by a notification system
    } else {
      // Worker started immediately
      console.log('Worker started immediately');
      // Start auto-stop timer
      startAutoStopTimer();
    }

    // Более частое обновление статуса после запуска для быстрого отклика
    const quickRefreshInterval = setInterval(async () => {
      await fetchWorkerStatus();
      const status = workerData.value?.status;
      if (status === 'running' || status === 'active') {
        clearInterval(quickRefreshInterval);
        console.log('Worker is now running, releasing start lock');
        releaseWorkerStartLock();
      } else if (status === 'error' || status === 'auth_required') {
        clearInterval(quickRefreshInterval);
        console.log('Worker reached error/auth state, releasing start lock');
        releaseWorkerStartLock();
      }
    }, 500); // Проверяем каждые 500мс

    await fetchWorkerStatus();
  } catch (err: any) {
    console.error('Could not start the worker:', err);
    if (err.response && err.response.data && err.response.data.detail) {
      error.value = err.response.data.detail;
    } else {
      error.value = $t('could_not_start_worker');
    }
    await fetchWorkerStatus(); // Refresh status even on error
    releaseWorkerStartLock(); // Сбрасываем при ошибке
  } finally {
    if (!startRequestInitiated) {
      releaseWorkerStartLock();
    }
  }
};

const stopWorker = async () => {
  if (isStopping.value || !workerData.value || ['stopped', 'error', 'not_configured'].includes(workerData.value.status)) return;
  isStopping.value = true;
  error.value = null;
  try {
    console.log('Sending worker stop request...');
    
    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const response = await axios.post('/api/workers/stop', {}, { 
      withCredentials: true,
      headers
    });
    console.log('Worker stop response:', response.data);
    
    // Play stop sound
    await playSound('stop');
    
    // Clear auto-stop timer
    clearAutoStopTimer();
    
    await fetchWorkerStatus(); 
  } catch (err: any) {
    console.error('Error stopping worker:', err);
     if (err.response && err.response.data && err.response.data.detail) {
      error.value = err.response.data.detail;
    } else {
      error.value = $t('could_not_stop_worker');
    }
    await fetchWorkerStatus(); // Refresh status even on error
  } finally {
    isStopping.value = false;
  }
};

const toggleWorker = async () => {
  if (isWorkerToggling.value) return;
  
  if (isWorkerRunning.value) {
    await stopWorker();
  } else {
    await startWorker();
  }
};

const workerStatusDisplay = computed(() => {
  if (!workerData.value) return $t('unknown') || 'Unknown';

  if (isLaunchInProgress.value) {
    const status = workerData.value.status;
    if (status === 'pending') {
      const position = workerData.value.queue_position;
      return position ? `${$t('queue')} (${position})` : $t('queue');
    }
    if (status === 'processing') {
      return $t('processing_worker');
    }
    if (status === 'added_to_queue') {
      const position = workerData.value.queue_position;
      return position ? `${$t('queue')} (${position})` : $t('starting_worker');
    }
    const activeLabel = $t('active') || 'Active';
    const startingSuffix = $t('starting_worker') || 'Starting';
    return `${activeLabel} (${startingSuffix})`;
  }

  switch (workerData.value.status) {
    case 'running':
    case 'active':
      const remainingSeconds = workerData.value.remaining_seconds;
      if (remainingSeconds !== undefined && remainingSeconds > 0) {
        return `${$t('active')} (${remainingSeconds}${$t('seconds_short')})`;
      }
      return $t('active');
    case 'processing':
      return $t('processing_worker');
    case 'pending':
      const position = workerData.value.queue_position;
      return position ? `${$t('queue')} (${position})` : $t('queue');
    case 'stopped': return $t('stopped');
    case 'error': return $t('error');
    case 'auth_required': return $t('auth_required');
    case 'not_configured': return $t('not_configured');
    default: return String(workerData.value.status);
  }
});

const statusClass = computed(() => {
  if (!workerData.value || !workerData.value.status) return 'status-unknown';
  let status = String(workerData.value.status);
  if (isLaunchInProgress.value) {
    status = 'running';
  } else if (status === 'active') {
    status = 'running'; // Отображаем 'active' как 'running' для консистентности стилей
  } else if (status === 'starting' || status === 'pending' || status === 'processing' || status === 'added_to_queue') {
    status = 'starting'; // Используем стили starting для pending и processing тоже
  } else if (status === 'auth_required') {
    status = 'auth-required'; // Специальный стиль для auth_required
  }
  return `status-${status.replace('_', '-')}`;
});

// Computed properties for unified worker button
const isWorkerRunning = computed(() => {
  if (isLaunchInProgress.value) {
    return true;
  }
  return workerData.value?.status === 'running' || workerData.value?.status === 'active';
});

const getWorkerButtonText = computed(() => {
  const toggling = isWorkerToggling.value;
  const running = isWorkerRunning.value;
  
  if (toggling) {
    return (isStartLocked.value || isLaunchInProgress.value) ? $t('starting_worker') : $t('stopping_worker');
  }

  // Also show "starting" text if worker is launching or in queue
  if (isLaunchInProgress.value) {
    return $t('starting_worker');
  }
  
  return running ? $t('stop') : $t('start');
});

const getWorkerButtonTitle = computed(() => {
  if (isWorkerToggling.value) {
    return (isStartLocked.value || isLaunchInProgress.value) ? $t('starting_worker') : $t('stopping_worker');
  }
  
  // Also show "starting" title if worker is launching or in queue
  if (isLaunchInProgress.value) {
    return $t('starting_worker');
  }
  
  return isWorkerRunning.value ? $t('stop_worker') : $t('start_worker');
});

// Computed для отладки состояния кнопки
const isButtonDisabled = computed(() => {
  const disabled = isWorkerToggling.value || 
                  workerData.value?.status === 'auth_required' || 
                  (!hasChannelRules.value && !isWorkerRunning.value) || 
                  (userInfo.value?.balance !== undefined && userInfo.value.balance < 0) ||
                  isLaunchInProgress.value;
  
  // Enhanced debug logging
  console.log('🎛️ isButtonDisabled computed:', {
    isWorkerToggling: isWorkerToggling.value,
    authRequired: workerData.value?.status === 'auth_required',
    hasChannelRules: hasChannelRules.value,
    isWorkerRunning: isWorkerRunning.value,
    noRulesAndNotRunning: (!hasChannelRules.value && !isWorkerRunning.value),
    negativeBalance: (userInfo.value?.balance !== undefined && userInfo.value.balance < 0),
    workerStarting: workerData.value?.status === 'starting',
    workerPending: workerData.value?.status === 'pending',
    workerProcessing: workerData.value?.status === 'processing',
    startLocked: isStartLocked.value,
    addedToQueue: workerData.value?.status === 'added_to_queue',
    launchInProgress: isLaunchInProgress.value,
    finalDisabled: disabled
  });
  
  return disabled;
});

const transitionalStatuses: string[] = ['starting', 'pending', 'processing', 'added_to_queue'];

// Computed property to check if worker is in transitional state (pending/starting/processing)
const workerInTransitionalState = computed(() => {
  const status = (workerData.value?.status || '') as string;
  return isStartLocked.value || transitionalStatuses.includes(status);
});

const isLaunchInProgress = computed(() => workerInTransitionalState.value);

// formatDateTime function removed as it's not currently used

const fetchChannelRules = async () => {
  try {
    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    console.log('🔧 fetchChannelRules: Starting, token exists:', !!token);
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const response = await axios.get('/api/channel_pairs', {
      withCredentials: true,
      headers
    });
    console.log('🔧 fetchChannelRules: Response received:', {
      status: response.status,
      dataType: typeof response.data,
      isArray: Array.isArray(response.data),
      length: Array.isArray(response.data) ? response.data.length : 'N/A',
      data: response.data
    });
    
    const hasRules = response.data && Array.isArray(response.data) && response.data.length > 0;
    hasChannelRules.value = hasRules;
    console.log('🔧 fetchChannelRules: hasChannelRules set to:', hasRules);
  } catch (error) {
    console.error('🔧 fetchChannelRules: Error fetching channel rules:', error);
    hasChannelRules.value = false;
    console.log('🔧 fetchChannelRules: hasChannelRules set to false due to error');
  }
};

// Session status checking function (currently unused but may be needed for future features)
// const checkSessionStatus = async () => {
//   try {
//     const token = localStorage.getItem('token');
//     const response = await axios.get('/api/channel_pairs/session-info', {
//       headers: { Authorization: `Bearer ${token}` },
//       withCredentials: true
//     });
//     
//     console.log('Dashboard: Session status check:', response.data);
//     
//     if (!response.data.session_valid) {
//       console.warn(`Dashboard: Telegram session is ${response.data.session_status}`);
//       
//       if (response.data.session_status === 'expired' || response.data.session_status === 'revoked') {
//         showAuthRequiredModal.value = true;
//       }
//     }
//     
//     return response.data;
//   } catch (error) {
//     console.error('Dashboard: Error checking session status:', error);
//     return null;
//   }
// };

const fetchChannels = async () => {
  if (channelsLoaded.value || loadingChannels.value) return;
  
  loadingChannels.value = true;
  try {
    // Support both cookie-based auth and token-based auth (for TMA)
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const response = await axios.get('/api/channel_pairs/channels', {
      withCredentials: true,
      headers
    });
    
    subscribedChannels.value = response.data.subscribed_channels;
    adminChannels.value = response.data.admin_channels;
    channelsLoaded.value = true;
    
    // Dashboard: Channels loaded
    // Dashboard: Subscribed channels loaded
    // Dashboard: Admin channels loaded
    
    // Check session validity
    if (!response.data.session_valid) {
      console.warn(`Dashboard: Telegram session is ${response.data.session_status}`);
      
      // Show session expired modal
      if (response.data.session_status === 'expired' || response.data.session_status === 'revoked') {
        showAuthRequiredModal.value = true;
      }
    } else if (response.data.user_info) {
      // Dashboard: Telegram user info loaded
      
      // Update user info if we got fresh data from Telegram
      if (response.data.user_info.username && userInfo.value) {
        // userInfo.value.telegram_username = response.data.user_info.username;
      }
    }
  } catch (error) {
    console.error('Dashboard: Error fetching channels:', error);
    // Don't show error to user, channels are optional for dashboard display
  } finally {
    loadingChannels.value = false;
  }
};

// Worker log methods
const handleWorkerLog = (data: any) => {
  workerLogs.value.push({
    message: data.message,
    timestamp: data.timestamp
  });
  
  // Ограничиваем количество записей в журнале
  if (workerLogs.value.length > 1000) {
    workerLogs.value = workerLogs.value.slice(-500);
  }
  
  // Автоскролл к последней записи
  nextTick(() => {
    const container = document.querySelector('.log-container');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  });
};

// Worker log utility functions (used in template)
const getLogClass = (message: string) => {
  if (message.includes('❌') || message.includes('Ошибка')) return 'log-error';
  if (message.includes('✅') || message.includes('обработан')) return 'log-success';
  if (message.includes('🔄') || message.includes('Обрабатываем')) return 'log-processing';
  if (message.includes('🔍') || message.includes('Сканируем')) return 'log-scanning';
  if (message.includes('🎧') || message.includes('прослушивание')) return 'log-listening';
  if (message.includes('🎉') || message.includes('завершена')) return 'log-complete';
  return 'log-info';
};

const clearLogs = () => {
  workerLogs.value = [];
};

const downloadLogs = () => {
  const logText = workerLogs.value
    .map(log => `${log.timestamp} ${log.message}`)
    .join('\n');
  
  const blob = new Blob([logText], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `worker-log-${new Date().toISOString().split('T')[0]}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};

// Explicitly mark these functions as template functions to avoid unused warnings
// @ts-ignore
getLogClass, clearLogs, downloadLogs;

// Function to auto-open wizard if user has no rules
const checkAndAutoOpenWizard = async () => {
  // Wait a bit to ensure the page is fully loaded
  setTimeout(() => {
    if (!hasChannelRules.value) {
      console.log('No rules found, auto-opening wizard');
      // Find the ChannelPairs component and trigger wizard
      const channelPairsElement = document.querySelector('#channel-rules');
      if (channelPairsElement) {
        // Scroll to the channel rules section
        channelPairsElement.scrollIntoView({ behavior: 'smooth' });
        
        // Trigger wizard opening after scroll
        setTimeout(() => {
          const wizardButton = document.querySelector('.wizard-btn');
          if (wizardButton) {
            (wizardButton as HTMLButtonElement).click();
          }
        }, 500);
      }
    }
  }, 1000);
};

const closeAuthModal = () => {
  showAuthRequiredModal.value = false;
};

const logout = async () => {
  try {
    // Close modal first
    showAuthRequiredModal.value = false;
    
    // Clear local storage
    localStorage.removeItem('auth_token');
    
    // Clear cookies by making a request to logout endpoint (if exists)
    try {
      await axios.post('/auth/logout', {}, { withCredentials: true });
    } catch (e) {
      // Logout endpoint might not exist, that's ok
      console.log('Logout endpoint not available, clearing cookies manually');
    }
    
    // Clear cookies manually
    document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=localhost;';
    
    // Redirect to login page
    window.location.href = '/';
  } catch (error) {
    console.error('Error during logout:', error);
    // Force redirect even if logout fails
    window.location.href = '/';
  }
};

const openRuleWizardFromParent = async (): Promise<boolean> => {
  const wizardComponent = channelPairsRef.value as any;
  if (wizardComponent && typeof wizardComponent.openRuleWizard === 'function') {
    await wizardComponent.openRuleWizard();
    return true;
  }

  const wizardButton = document.querySelector('.wizard-btn') as HTMLButtonElement | null;
  if (wizardButton) {
    wizardButton.click();
    return true;
  }

  console.warn('Dashboard: ChannelPairs wizard is not ready yet');
  return false;
};

defineExpose({
  openRuleWizard: openRuleWizardFromParent
});

// Handle rule creation success - update hasChannelRules state
const handleRuleCreated = async (channelInfo?: { sourceChannel: string, targetChannel: string }) => {
  console.log('🎉 handleRuleCreated: Rule created successfully, updating channel rules state');
  
  // Refresh channel rules to update hasChannelRules
  await fetchChannelRules();
  
  // Clear any error messages related to no rules
  if (error.value === $t('cannot_start_no_rules')) {
    error.value = null;
    console.log('🎉 handleRuleCreated: Cleared "no rules" error message');
  }
  
  // Refresh worker status to get the latest state
  await fetchWorkerStatus();
  
  // Emit event to parent App.vue
  if (channelInfo) {
    console.log('🎉 handleRuleCreated: Emitting rule-created-successfully to App.vue');
    emit('rule-created-successfully', channelInfo);
  }
  
  console.log('🎉 handleRuleCreated: hasChannelRules updated to:', hasChannelRules.value);
  console.log('🎉 handleRuleCreated: Current button disabled state:', isButtonDisabled.value);
};

onMounted(async () => {
  loading.value = true; 
  error.value = null;
  
  // Small delay to ensure authentication tokens are properly set
  await new Promise(resolve => setTimeout(resolve, 100));
  
  // Dashboard onMounted: Starting data fetch...
  await fetchUserInfo(); // Fetch user info first
  await fetchWorkerStatus(); // Then fetch worker status
  await fetchChannelRules(); // Check if channel rules exist
  await fetchScheduledPosts(); // Fetch scheduled posts logs
  await fetchWorkerErrors(); // Fetch worker errors logs
  
  // Load channels for better UI display (non-blocking)
  fetchChannels(); // Don't await - load in background
  
  // loading.value will be set to false inside fetchWorkerStatus
  
  // Connect to WebSocket for real-time logs
  connectWebSocket();
  
  // Auto-open wizard if no rules exist
  await checkAndAutoOpenWizard();
  
  // Set up periodic refresh
  const refreshInterval = setInterval(async () => {
    await fetchWorkerStatus();
    await fetchUserInfo(); // Update balance dynamically
    
    // Only fetch logs via HTTP if WebSocket is not connected (fallback mode)
    if (!websocketConnected.value) {
      await fetchScheduledPosts(); // Update scheduled posts logs
      await fetchWorkerErrors(); // Update worker errors logs
    }
  }, 1000); // Refresh every 1 second
  
  // Clean up interval on component unmount
  onUnmounted(() => {
    clearInterval(refreshInterval);
    clearAutoStopTimer();
    disconnectWebSocket();
  });
});
</script>

<style scoped>
.dashboard {
  background: linear-gradient(to bottom, hwb(194 80% 8%), hsl(127, 63%, 80%));
  padding: 20px;
  font-family: sans-serif;
  margin: 10px;
  width: calc(100% - 20px);
  min-height: calc(100vh - 220px);
  background-color: #f9f9f9;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  box-sizing: border-box;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .dashboard {
    margin: 5px;
    padding: 10px;
    width: calc(100% - 10px);
    border-radius: 8px;
    min-height: calc(100vh - 120px);
  }
  
  /* Center the main title on mobile */
  .dashboard h2 {
    text-align: center !important;
  }
}

.dashboard h2 {
  text-shadow: 0 0 8px rgba(240, 255, 240, 0.8), 0 0 16px rgba(224, 255, 224, 0.6), 1px 1px 2px rgba(0, 0, 0, 0.4);
}

/* Three blocks layout */
.dashboard-info {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 20px;
  padding: 15px;
  background: linear-gradient(45deg, rgba(224, 242, 247, 0.4), rgba(213, 166, 115, 0.3), rgba(138, 43, 226, 0.2), rgba(255, 140, 0, 0.2));
  background-size: 400% 400%;
  animation: dashboardGradientShift 10s ease-in-out infinite;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(2px);
}

/* Mobile layout for dashboard info */
@media (max-width: 768px) {
  .dashboard-info {
    flex-direction: column;
    gap: 15px;
    padding: 10px;
    margin-bottom: 15px;
  }
  
  .avatar-block {
    align-self: center !important;
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
  }
  
  .user-info-block {
    text-align: center !important;
    align-items: center !important;
    width: 100% !important;
  }
  
  .worker-block {
    width: 100% !important;
    text-align: center !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
  }
  
  .worker-status {
    text-align: center !important;
    width: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
  }
  
  .worker-status-line {
    text-align: center !important;
    width: 100% !important;
  }
  
  .loading,
  .error-message {
    text-align: center !important;
    width: 100% !important;
  }
  
  .warning-message,
  .auth-required-message {
    text-align: center !important;
    width: 100% !important;
    margin: 10px auto !important;
  }
}

@keyframes dashboardGradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.avatar-block {
  flex: 0 0 auto;
  align-self: flex-start;
  display: flex;
  justify-content: flex-start;
}

.user-avatar {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  border: 3px solid #007bff;
}

.user-info-block {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
}

.username {
  font-size: 1.2em;
  font-weight: bold;
  margin-bottom: 5px;
  color: #333;
  text-shadow: 0 0 8px rgba(240, 255, 240, 0.8), 0 0 16px rgba(224, 255, 224, 0.6), 1px 1px 2px rgba(0, 0, 0, 0.4);
}

.balance {
  font-size: 1em;
  color: #666;
  text-shadow: 0 0 8px rgba(240, 255, 240, 0.8), 0 0 16px rgba(224, 255, 224, 0.6), 1px 1px 2px rgba(0, 0, 0, 0.4);
  transition: all 0.3s ease;
  padding: 4px 8px;
  border-radius: 4px;
}

.balance-green {
  color: #076b0b !important;
  background-color: rgba(76, 175, 80, 0.1);
  text-shadow: 1px 1px 1px rgba(0, 0, 0, 0.9);
}

.balance-yellow {
  color: #e9d30a !important;
  background-color: rgba(55, 50, 6, 0.1);
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.9);
}

.balance-red {
  color: #f71606 !important;
  background-color: rgba(244, 67, 54, 0.1);
  text-shadow: 1px 1px 1px rgba(0, 0, 0, 0.9);
}

.balance-updated {
  color: #28a745 !important;
  font-weight: bold;
  transform: scale(1.05);
  text-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
  animation: balanceGlow 2s ease-in-out;
}

@keyframes balanceGlow {
  0% { 
    color: #28a745;
    text-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
  }
  50% { 
    color: #20c997;
    text-shadow: 0 0 12px rgba(32, 201, 151, 0.8);
  }
  100% { 
    color: #28a745;
    text-shadow: 0 0 8px rgba(40, 167, 69, 0.6);
  }
}

.vip-level {
  font-size: 0.9em;
  color: #ff8a65;
  font-weight: bold;
  margin-top: 5px;
  text-shadow: 0 0 8px rgba(240, 255, 240, 0.8), 0 0 16px rgba(224, 255, 224, 0.6), 1px 1px 2px rgba(0, 0, 0, 0.4);
}

.worker-block {
  flex: 0 0 auto;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: flex-end;
}

.worker-status {
  text-align: center;
}

.worker-status-line {
  text-align: center;
  margin-bottom: 10px;
  font-size: 1em;
  text-shadow: 0 0 8px rgba(240, 255, 240, 0.8), 0 0 16px rgba(224, 255, 224, 0.6), 1px 1px 2px rgba(0, 0, 0, 0.2);
}

.loading, .error-message {
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 15px;
}
.loading {
  background-color: #e0e0e0;
}
.error-message {
  background-color: #ffdddd;
  color: #d8000c;
  border: 1px solid #d8000c;
}

.warning-message {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
  font-size: 0.9em;
  text-align: center;
}

.auth-required-message {
  background-color: #ffe6e6;
  color: #d8000c;
  border: 1px solid #ff6b35;
  padding: 10px;
  border-radius: 4px;
  margin-top: 10px;
  font-size: 0.9em;
  text-align: center;
}

.logout-button {
  background-color: #ff6b35;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 10px;
  font-size: 0.9em;
}

.logout-button:hover {
  background-color: #e55a2b;
}

/* Modal styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #eee;
}

.modal-header h3 {
  margin: 0;
  color: #ff6b35;
  font-size: 1.2em;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close:hover {
  color: #333;
}

.modal-body {
  padding: 20px;
}

.modal-body p {
  margin: 0 0 15px 0;
  line-height: 1.5;
}

.modal-instruction {
  background-color: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  border-left: 4px solid #ff6b35;
  font-weight: 500;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 20px;
  border-top: 1px solid #eee;
}

.modal-button {
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.2s;
}

.modal-button.primary {
  background-color: #ff6b35;
  color: white;
}

.modal-button.primary:hover {
  background-color: #e55a2b;
}

.modal-button.secondary {
  background-color: #6c757d;
  color: white;
}

.modal-button.secondary:hover {
  background-color: #5a6268;
}



.status-running { 
  color: #4CAF50; 
  font-weight: bold; 
  text-shadow: 0 0 8px rgba(76, 175, 80, 0.6), 0 0 16px rgba(144, 238, 144, 0.4), 1px 1px 2px rgba(0, 0, 0, 0.4); 
}
.status-starting { 
  color: #66BB6A; 
  font-weight: bold; 
  text-shadow: 0 0 8px rgba(102, 187, 106, 0.6), 0 0 16px rgba(144, 238, 144, 0.4), 1px 1px 2px rgba(0, 0, 0, 0.4); 
}
.status-stopped { 
  color: #8BC34A; 
  font-weight: bold; 
  text-shadow: 0 0 8px rgba(139, 195, 74, 0.6), 0 0 16px rgba(144, 238, 144, 0.4), 1px 1px 2px rgba(0, 0, 0, 0.4); 
}
.status-error { 
  color: #689F38; 
  font-weight: bold; 
  text-shadow: 0 0 8px rgba(104, 159, 56, 0.6), 0 0 16px rgba(144, 238, 144, 0.4), 1px 1px 2px rgba(0, 0, 0, 0.4); 
}
.status-auth-required { 
  color: #558B2F; 
  font-weight: bold; 
  text-shadow: 0 0 8px rgba(85, 139, 47, 0.6), 0 0 16px rgba(144, 238, 144, 0.4), 1px 1px 2px rgba(0, 0, 0, 0.4); 
}
.status-not-configured { 
  color: #33691E; 
  font-weight: bold; 
  text-shadow: 0 0 8px rgba(51, 105, 30, 0.6), 0 0 16px rgba(144, 238, 144, 0.4), 1px 1px 2px rgba(0, 0, 0, 0.4); 
}
.status-unknown { 
  color: #2E7D32; 
  text-shadow: 0 0 8px rgba(46, 125, 50, 0.6), 0 0 16px rgba(144, 238, 144, 0.4), 1px 1px 2px rgba(0, 0, 0, 0.4); 
}

.controls {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  justify-content: center;
}

.worker-control-button {
  display: flex;
  justify-content: center;
  width: 100%;
}

.button-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.control-button {
  margin: 0;
  padding: 12px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 1em;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-width: 140px;
  min-height: 48px;
  font-weight: 600;
  transition: all 0.2s ease;
  box-shadow: 
    0 0 20px rgba(255, 255, 255, 0.6), 
    0 0 30px rgba(255, 255, 255, 0.4), 
    0 0 40px rgba(255, 255, 255, 0.3), 
    0 0 50px rgba(255, 255, 255, 0.2),
    inset 0 0 10px rgba(255, 255, 255, 0.2);
  animation: buttonGlow 2s ease-in-out infinite alternate;
  backdrop-filter: blur(1px);
}

.button-label {
  font-size: 12px;
  color: #666;
  text-align: center;
  font-weight: 500;
}

/* Hide mobile labels on desktop */
.mobile-only {
  display: none;
}

/* Show button text on desktop */
.button-text {
  display: inline;
}

.controls button {
  margin-right: 10px;
  padding: 8px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
  min-height: 40px;
}

.icon {
  width: 16px;
  height: 16px;
  stroke-width: 2;
}

.spin {
  animation: spin 1s linear infinite;
}

/* Special glow for loading state */
.button-loading {
  box-shadow: 0 0 30px rgba(255, 193, 7, 0.8), 0 0 40px rgba(255, 255, 255, 0.6), 0 0 50px rgba(255, 255, 255, 0.5), 0 0 60px rgba(255, 193, 7, 0.4) !important;
  animation: buttonGlow 1s ease-in-out infinite alternate !important;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes buttonGlow {
  0% {
    box-shadow: 
      0 0 20px rgba(255, 255, 255, 0.6), 
      0 0 30px rgba(255, 255, 255, 0.4), 
      0 0 40px rgba(255, 255, 255, 0.3), 
      0 0 50px rgba(255, 255, 255, 0.2),
      inset 0 0 10px rgba(255, 255, 255, 0.2);
  }
  100% {
    box-shadow: 
      0 0 30px rgba(255, 255, 255, 0.8), 
      0 0 40px rgba(255, 255, 255, 0.6), 
      0 0 50px rgba(255, 255, 255, 0.4), 
      0 0 60px rgba(255, 255, 255, 0.3),
      inset 0 0 15px rgba(255, 255, 255, 0.3);
  }
}

@keyframes startButtonPulse {
  0% {
    box-shadow: 
      0 0 35px rgba(76, 175, 80, 1), 
      0 0 45px rgba(144, 238, 144, 0.8), 
      0 0 55px rgba(152, 251, 152, 0.6), 
      0 0 65px rgba(34, 139, 34, 0.5),
      0 0 75px rgba(0, 128, 0, 0.4),
      0 0 85px rgba(50, 205, 50, 0.3),
      inset 0 0 18px rgba(76, 175, 80, 0.5);
    background-position: 0% 50%;
    transform: scale(1.05);
  }
  100% {
    box-shadow: 
      0 0 50px rgba(76, 175, 80, 1.2), 
      0 0 65px rgba(144, 238, 144, 1), 
      0 0 80px rgba(152, 251, 152, 0.8), 
      0 0 95px rgba(34, 139, 34, 0.7),
      0 0 110px rgba(0, 128, 0, 0.6),
      0 0 125px rgba(50, 205, 50, 0.5),
      inset 0 0 25px rgba(76, 175, 80, 0.7);
    background-position: 100% 50%;
    transform: scale(1.08);
  }
}

@keyframes startButtonHover {
  0% {
    background-position: 0% 50%;
    transform: scale(1.08);
  }
  100% {
    background-position: 100% 50%;
    transform: scale(1.1);
  }
}

@keyframes startButtonRotateGlow {
  0% {
    filter: hue-rotate(0deg) brightness(1);
  }
  25% {
    filter: hue-rotate(90deg) brightness(1.2);
  }
  50% {
    filter: hue-rotate(180deg) brightness(1.4);
  }
  75% {
    filter: hue-rotate(270deg) brightness(1.2);
  }
  100% {
    filter: hue-rotate(360deg) brightness(1);
  }
}

@keyframes startButtonBounce {
  0%, 100% {
    transform: scale(1.05) translateY(0px);
  }
  25% {
    transform: scale(1.08) translateY(-2px);
  }
  50% {
    transform: scale(1.1) translateY(-4px);
  }
  75% {
    transform: scale(1.08) translateY(-2px);
  }
}

@keyframes startButtonExplosion {
  0% {
    box-shadow: 
      0 0 40px rgba(76, 175, 80, 1), 
      0 0 50px rgba(255, 255, 255, 0.8), 
      0 0 60px rgba(255, 255, 255, 0.6), 
      0 0 70px rgba(76, 175, 80, 0.5),
      0 0 80px rgba(76, 175, 80, 0.4),
      inset 0 0 20px rgba(76, 175, 80, 0.5);
  }
  50% {
    box-shadow: 
      0 0 60px rgba(76, 175, 80, 1.2), 
      0 0 80px rgba(255, 255, 255, 1), 
      0 0 100px rgba(255, 255, 255, 0.8), 
      0 0 120px rgba(76, 175, 80, 0.7),
      0 0 140px rgba(76, 175, 80, 0.6),
      0 0 160px rgba(76, 175, 80, 0.5),
      inset 0 0 30px rgba(76, 175, 80, 0.7);
  }
  100% {
    box-shadow: 
      0 0 40px rgba(76, 175, 80, 1), 
      0 0 50px rgba(255, 255, 255, 0.8), 
      0 0 60px rgba(255, 255, 255, 0.6), 
      0 0 70px rgba(76, 175, 80, 0.5),
      0 0 80px rgba(76, 175, 80, 0.4),
      inset 0 0 20px rgba(76, 175, 80, 0.5);
  }
}

@keyframes startButtonShake {
  0%, 100% {
    transform: scale(1.08) translateX(0px);
  }
  25% {
    transform: scale(1.09) translateX(-1px);
  }
  50% {
    transform: scale(1.1) translateX(1px);
  }
  75% {
    transform: scale(1.09) translateX(-1px);
  }
}

@keyframes stopButtonPulse {
  0% {
    box-shadow: 
      0 0 30px rgba(244, 67, 54, 0.8), 
      0 0 40px rgba(255, 255, 255, 0.6), 
      0 0 50px rgba(255, 255, 255, 0.4), 
      0 0 60px rgba(244, 67, 54, 0.4),
      0 0 70px rgba(244, 67, 54, 0.3),
      inset 0 0 15px rgba(244, 67, 54, 0.4);
    background-position: 0% 50%;
  }
  100% {
    box-shadow: 
      0 0 35px rgba(244, 67, 54, 0.9), 
      0 0 45px rgba(255, 255, 255, 0.7), 
      0 0 55px rgba(255, 255, 255, 0.5), 
      0 0 65px rgba(244, 67, 54, 0.5),
      0 0 75px rgba(244, 67, 54, 0.4),
      inset 0 0 18px rgba(244, 67, 54, 0.5);
    background-position: 100% 50%;
  }
}

@keyframes stopButtonHover {
  0% {
    background-position: 0% 50%;
    transform: scale(1.05);
  }
  100% {
    background-position: 100% 50%;
    transform: scale(1.07);
  }
}

@keyframes activeWorkerGlow {
  0% {
    box-shadow: 
      0 0 25px rgba(244, 67, 54, 0.7), 
      0 0 35px rgba(255, 255, 255, 0.5), 
      0 0 45px rgba(255, 255, 255, 0.4), 
      0 0 55px rgba(244, 67, 54, 0.3),
      inset 0 0 10px rgba(244, 67, 54, 0.3);
  }
  50% {
    box-shadow: 
      0 0 35px rgba(244, 67, 54, 0.9), 
      0 0 45px rgba(255, 255, 255, 0.7), 
      0 0 55px rgba(255, 255, 255, 0.5), 
      0 0 65px rgba(244, 67, 54, 0.4),
      inset 0 0 15px rgba(244, 67, 54, 0.4);
  }
  100% {
    box-shadow: 
      0 0 25px rgba(244, 67, 54, 0.7), 
      0 0 35px rgba(255, 255, 255, 0.5), 
      0 0 45px rgba(255, 255, 255, 0.4), 
      0 0 55px rgba(244, 67, 54, 0.3),
      inset 0 0 10px rgba(244, 67, 54, 0.3);
  }
}
.controls button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
  box-shadow: 0 0 25px rgba(255, 255, 255, 0.4), 0 0 35px rgba(255, 255, 255, 0.3), 0 0 45px rgba(255, 255, 255, 0.2);
  animation: buttonGlow 1.5s ease-in-out infinite alternate;
}
.button-start {
  position: relative;
  background: linear-gradient(45deg, #4CAF50, #66BB6A, #4CAF50);
  background-size: 200% 200%;
  color: white;
  font-weight: 700;
  font-size: 1.1em;
  border: 2px solid rgba(76, 175, 80, 0.8);
  box-shadow: 
    0 0 30px rgba(76, 175, 80, 0.9), 
    0 0 40px rgba(144, 238, 144, 0.7), 
    0 0 50px rgba(152, 251, 152, 0.5), 
    0 0 60px rgba(34, 139, 34, 0.4),
    0 0 70px rgba(0, 128, 0, 0.3),
    inset 0 0 15px rgba(76, 175, 80, 0.4);
  animation: startButtonPulse 3s ease-in-out infinite alternate;
  transform: scale(1.05);
  text-shadow: 0 0 10px rgba(144, 238, 144, 0.8);
  overflow: visible;
}

.button-start::before {
  content: '';
  position: absolute;
  top: -10px;
  left: -10px;
  right: -10px;
  bottom: -10px;
  background: radial-gradient(circle, rgba(76, 175, 80, 0.3) 0%, transparent 70%);
  border-radius: 12px;
  animation: startButtonEnergyField 2s ease-in-out infinite alternate;
  z-index: -1;
}

.button-start::after {
  content: '';
  position: absolute;
  top: -5px;
  left: -5px;
  right: -5px;
  bottom: -5px;
  background: linear-gradient(45deg, 
    rgba(76, 175, 80, 0.4), 
    rgba(255, 255, 255, 0.2), 
    rgba(76, 175, 80, 0.4));
  border-radius: 10px;
  animation: startButtonInnerGlow 1s ease-in-out infinite alternate;
  z-index: -1;
}
.button-start:hover:not(:disabled) {
  background: linear-gradient(45deg, #45a049, #5cb85c, #45a049);
  background-size: 200% 200%;
  animation: startButtonHover 1s ease-in-out infinite alternate;
  transform: scale(1.08);
  box-shadow: 
    0 0 40px rgba(76, 175, 80, 1), 
    0 0 50px rgba(144, 238, 144, 0.8), 
    0 0 60px rgba(152, 251, 152, 0.6), 
    0 0 70px rgba(34, 139, 34, 0.5),
    0 0 80px rgba(0, 128, 0, 0.4),
    inset 0 0 20px rgba(76, 175, 80, 0.5);
}
.button-stop {
  background: linear-gradient(45deg, #f44336, #e57373, #f44336);
  background-size: 200% 200%;
  color: white;
  font-weight: 700;
  font-size: 1.1em;
  border: 2px solid rgba(244, 67, 54, 0.8);
  box-shadow: 
    0 0 30px rgba(244, 67, 54, 0.8), 
    0 0 40px rgba(255, 255, 255, 0.6), 
    0 0 50px rgba(255, 255, 255, 0.4), 
    0 0 60px rgba(244, 67, 54, 0.4),
    0 0 70px rgba(244, 67, 54, 0.3),
    inset 0 0 15px rgba(244, 67, 54, 0.4);
  animation: stopButtonPulse 3s ease-in-out infinite;
  transform: scale(1.02);
  text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
}
.button-stop:hover:not(:disabled) {
  background: linear-gradient(45deg, #da190b, #f44336, #da190b);
  background-size: 200% 200%;
  animation: stopButtonHover 0.8s ease-in-out infinite alternate;
  transform: scale(1.05);
  box-shadow: 
    0 0 40px rgba(244, 67, 54, 1), 
    0 0 50px rgba(255, 255, 255, 0.8), 
    0 0 60px rgba(255, 255, 255, 0.6), 
    0 0 70px rgba(244, 67, 54, 0.5),
    0 0 80px rgba(244, 67, 54, 0.4),
    inset 0 0 20px rgba(244, 67, 54, 0.5);
}


.logs-section {
  margin: 20px 0;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  overflow: hidden;
}

.logs-section h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: #333;
  font-weight: bold;
  text-shadow: 0 0 8px rgba(240, 255, 240, 0.8), 0 0 16px rgba(224, 255, 224, 0.6), 1px 1px 2px rgba(0, 0, 0, 0.4);
}

.logs-container {
  width: 100%;
  overflow: hidden;
  box-sizing: border-box;
}

.unified-logs {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 300px;
  overflow-y: auto;
  overflow-x: hidden;
  box-sizing: border-box;
}

.log-entry {
  display: flex;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 8px;
  background: #f8f9fa;
  border-radius: 4px;
  font-size: 11px;
  line-height: 1.3;
  border-left: 3px solid transparent;
  text-align: left;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.log-entry.success {
  border-left-color: #135021;
}

.log-entry.error {
  border-left-color: #dc3545;
}

.log-entry.warning {
  border-left-color: #ffc107;
}

.log-entry.info {
  border-left-color: #2196f3;
}

.log-icon {
  margin-right: 8px;
  font-weight: bold;
  font-size: 12px;
  flex-shrink: 0;
}

.success-icon {
  color: #28a745;
}

.error-icon {
  color: #dc3545;
}

.log-content {
  flex: 1;
  font-size: 11px;
  text-align: left;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  min-width: 0;
}

/* Mobile button optimizations */
@media (max-width: 768px) {
  .controls {
    display: flex !important;
    flex-direction: column !important;
    gap: 10px !important;
    width: 100% !important;
    align-items: center !important;
    text-align: center !important;
  }
  
  .worker-control-button {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
  }
  
  .button-container {
    flex: 1;
    gap: 8px;
    flex-direction: column;
    align-items: center;
  }
  
  .control-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 16px 24px;
    font-size: 18px;
    min-height: 56px;
    max-width: 200px;
    border-radius: 12px;
    font-weight: 600;
    min-width: auto;
    box-shadow: 0 0 25px rgba(255, 255, 255, 0.7), 0 0 35px rgba(255, 255, 255, 0.5), 0 0 45px rgba(255, 255, 255, 0.4), 0 0 55px rgba(255, 255, 255, 0.3);
    animation: buttonGlow 2s ease-in-out infinite alternate;
  }
  
  /* Show mobile labels on mobile */
  .mobile-only {
    display: none;
  }
  
  .button-text {
    display: inline;
  }
  
  .icon {
    width: 20px;
    height: 20px;
  }
  
  .worker-status-line {
    font-size: 16px;
    margin-bottom: 15px;
    text-align: center;
  }
  
  .username {
    font-size: 18px;
  }
  
  .balance {
    font-size: 16px;
    margin: 8px 0;
  }
  
  .user-avatar {
    width: 60px;
    height: 60px;
  }
  
  /* Logs section mobile optimization */
  .logs-section {
    margin-top: 20px;
    margin-left: 5px;
    margin-right: 5px;
    padding: 10px;
  }
  
  .logs-container {
    max-height: 300px;
    overflow-y: auto;
    overflow-x: hidden;
    -webkit-overflow-scrolling: touch;
  }
  
  .log-entry {
    padding: 8px;
    font-size: 12px;
    line-height: 1.4;
    margin-bottom: 6px;
    overflow: hidden;
  }
  
  .log-content {
    word-break: break-word;
    overflow-wrap: break-word;
    hyphens: auto;
  }
  
  /* Modal optimizations */
  .modal-content {
    margin: 20px;
    max-width: calc(100vw - 40px);
    max-height: calc(100vh - 40px);
    overflow-y: auto;
  }
  
  .modal-button {
    padding: 12px 20px;
    font-size: 16px;
    min-height: 48px;
  }
  
  /* Warning and error messages */
  .warning-message,
  .auth-required-message {
    font-size: 14px;
    padding: 10px;
    margin: 10px 0;
    border-radius: 6px;
    text-align: center;
  }
  
  .logout-button {
    margin-top: 10px;
    padding: 10px 16px;
    font-size: 14px;
  }
}

/* Small mobile devices - extra compact logs */
@media (max-width: 480px) {
  .logs-section {
    margin: 10px 2px;
    padding: 8px;
  }
  
  .logs-container {
    max-height: 250px;
  }
  
  .log-entry {
    padding: 6px;
    font-size: 11px;
    margin-bottom: 4px;
  }
  
  .log-content {
    font-size: 11px;
    line-height: 1.3;
  }
  
  .log-icon {
    margin-right: 6px;
    font-size: 10px;
  }
}

/* Desktop button text shown */
@media (min-width: 769px) {
  .button-text {
    display: inline;
  }
  
  .mobile-only {
    display: none;
  }
}
</style>