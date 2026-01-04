<template>
  <div :class="{ 'app-redesigned': useRedesignedUI }">
    <!-- Environment Configuration Error Notification -->
    <div v-if="envConfigError" class="env-error-notification">
      <div class="env-error-content">
        <h2>🚨 CRITICAL ENVIRONMENT CONFIGURATION ERROR 🚨</h2>
        <p><strong>The application is not properly configured!</strong></p>
        <p>This is a severe system configuration issue that prevents normal operation.</p>
        <div class="error-details">
          <p><strong>Technical Details:</strong></p>
          <ul>
            <li v-for="error in envConfigErrorDetails" :key="error">{{ error }}</li>
          </ul>
        </div>
        <p><strong>Immediate Actions Required:</strong></p>
        <ol>
          <li>Check server environment variables</li>
          <li>Verify S3/Yandex Cloud credentials</li>
          <li>Ensure .env file is properly loaded</li>
          <li>Restart the application service</li>
        </ol>
        <p><strong>Contact system administrator immediately!</strong></p>
        <button @click="retryEnvCheck" class="retry-button">
          {{ $t('try_again') || 'Retry Configuration Check' }}
        </button>
      </div>
    </div>

    <!-- Debug indicator - removed in production -->
    <!-- Loading Screen -->
    <transition name="fade">
      <div v-if="isLoading && !envConfigError" class="loading-screen">
        <div class="loading-spinner"></div>
        <p>{{ $t('loading_app') }}</p>
        <div v-if="authError" class="auth-error">
          <p class="error-message">{{ authError }}</p>
          <button @click="retryAuth" class="retry-button">
            {{ $t('try_again') || 'Попробовать снова' }}
          </button>
        </div>
      </div>
    </transition>
    
    <!-- Login Form -->
    <transition name="slide-up">
      <LoginForm
        v-if="showLogin && !isLoading && !envConfigError"
        :skip-tma-auth="telegramSessionRequired"
        @login="onLogin"
      />
    </transition>
    
    <!-- Landing Page - показывается только НЕавторизованным -->
    <transition name="slide-up">
      <LandingPage v-if="showLanding && !isLoading && !envConfigError" @start-trial="onStartTrial" />
    </transition>
    
    <!-- Main App - Original UI -->
    <transition name="slide-up">
      <div v-if="!isLoading && !showLogin && !showLanding && !useRedesignedUI && !envConfigError" class="original-ui">
        <!-- Service Header -->
        <ServiceHeader 
          :currentPage="currentPage" 
          :currentUserId="currentUserId"
          @navigate="handleNavigation" />
        
        <!-- Page Content -->
        <Dashboard v-if="currentPage === 'dashboard'" ref="dashboardRef" @rule-created-successfully="handleRuleCreated" />
        <Info v-if="currentPage === 'info'" />
      </div>
    </transition>
    
    <!-- Main App - Redesigned UI -->
    <transition name="slide-up">
      <RedesignedApp 
        v-if="!isLoading && !showLogin && !showLanding && useRedesignedUI && !envConfigError"
        :user-info="dashboardData.userInfo"
        :worker-data="dashboardData.workerData"
        :loading="dashboardData.loading"
        :error="dashboardData.error"
        :is-worker-toggling="dashboardData.isWorkerToggling"
        :is-start-locked="dashboardData.isStartLocked"
        :has-channel-rules="dashboardData.hasChannelRules"
        :requested-tab="forcedTab"
        :scheduled-posts="dashboardData.scheduledPosts"
        :realtime-logs="dashboardData.realtimeLogs"
        :worker-errors="dashboardData.workerErrors"
        :rules="dashboardData.rules"
        :subscribed-channels="dashboardData.subscribedChannels"
        :admin-channels="dashboardData.adminChannels"
        :loading-channels="dashboardData.loadingChannels"
        :current-user-id="currentUserId"
        @show-info="showInfoPage"
        @logout="handleLogout"
        @toggle-ui-design="toggleUIDesign"
        @open-rule-wizard="handleOpenRuleWizard"
        @toggle-worker="toggleWorker"
        @start-worker="startWorker"
        @stop-worker="stopWorker"
        @fetch-scheduled-posts="fetchScheduledPosts"
        @fetch-worker-errors="fetchWorkerErrors"
        @refresh-account="handleAccountSwitch"
      >
        <template #channel-pairs>
          <ChannelPairs 
            ref="channelPairsRef"
            :preloaded-channels="{ subscribed: dashboardData.subscribedChannels, admin: dashboardData.adminChannels }"
            :channels-loaded="true"
            @rule-created-successfully="handleRuleCreated"
          />
        </template>
        <template #modals>
          <!-- Any modals from the original dashboard -->
        </template>
        <template #notifications>
          <!-- Any notifications from the original dashboard -->
        </template>
      </RedesignedApp>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, reactive, nextTick, watch, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import LoginForm from './components/LoginForm.vue'
import Dashboard from './components/Dashboard.vue'
import ChannelPairs from './components/ChannelPairs.vue'
import Info from './components/Info.vue'
import ServiceHeader from './components/ServiceHeader.vue'
import LandingPage from './components/LandingPage.vue'
import RedesignedApp from './components/RedesignedApp.vue'
import { isRedesignEnabled, setRedesignPreference, isBackdoorAutologinEnabled } from './utils/envUtils'
import { isTmaDebugEnabled, tmaLog as tmaDebug, maskToken } from './utils/tmaUtils'
import axios from 'axios'
import { tmaService } from './services/tma'

// Environment configuration error state
const envConfigError = ref(false)
const envConfigErrorDetails = ref<string[]>([])

// Обычная настройка - без изменений
console.log('🚀 Standard API configuration');

const { t: $t, locale } = useI18n()

// Debug: Log the current locale
console.log('🎯 App.vue: Current locale from i18n:', locale.value)
console.log('🎯 App.vue: Translation for loading_app:', $t('loading_app'))

// Additional debugging for language detection
if (window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code) {
  console.log('🎯 App.vue: Telegram user language:', window.Telegram.WebApp.initDataUnsafe.user.language_code);
}
if (navigator.language) {
  console.log('🎯 App.vue: Browser language:', navigator.language);
}

// Debug: Check if we're in TMA and what language is detected
if (window.Telegram?.WebApp) {
  console.log('🎯 App.vue: TMA detected, checking language sources...');
  if (window.Telegram.WebApp.initDataUnsafe?.user?.language_code) {
    console.log('🎯 App.vue: TMA user language:', window.Telegram.WebApp.initDataUnsafe.user.language_code);
  }
  if (window.Telegram.WebApp.initDataUnsafe?.language_code) {
    console.log('🎯 App.vue: TMA initData language:', window.Telegram.WebApp.initDataUnsafe.language_code);
  }
  if (window.Telegram.WebApp.initDataUnsafe) {
    console.log('🎯 App.vue: TMA initDataUnsafe keys:', Object.keys(window.Telegram.WebApp.initDataUnsafe));
  }
}

const isAuth = ref(false)
const showLogin = ref(false)
const isLoading = ref(true)
const authError = ref<string | null>(null)
// If true, we must force the user through phone-based Telegram auth to create a worker session file
const telegramSessionRequired = ref(false)
const currentPage = ref('dashboard')
const currentUserId = ref<number | undefined>(undefined)
const showLanding = ref(false) // Показываем после проверки, если пользователь не авторизован
const useRedesignedUI = ref(isRedesignEnabled())
const dashboardRef = ref<InstanceType<typeof Dashboard> | null>(null)
// Used to force RedesignedApp to switch tabs when we need to open RuleWizard
const forcedTab = ref<string | null>(null)
// Redesigned UI aggregated state used by RedesignedApp
const dashboardData = reactive({
  userInfo: null as any,
  workerData: null as any,
  loading: false as boolean,
  error: null as string | null,
  isWorkerToggling: false as boolean,
  isStartLocked: false as boolean,
  hasChannelRules: false as boolean,
  scheduledPosts: [] as any[],
  realtimeLogs: [] as any[],
  workerErrors: [] as any[],
  rules: [] as any[],
  subscribedChannels: [] as any[],
  adminChannels: [] as any[],
  loadingChannels: false as boolean,
  wizardChannelsLoading: false as boolean,
});

// WebSocket and timers for logs
const websocket = ref<WebSocket | null>(null)
const websocketConnected = ref(false)
const fallbackLogTimer = ref<number | null>(null)

// TMA debug utilities are now imported from utils/tmaUtils
console.log('🎨 UI Debug Info:', {
  'Environment VITE_ENABLE_REDESIGN': import.meta.env.VITE_ENABLE_REDESIGN,
  'localStorage enable_redesigned_ui': localStorage.getItem('enable_redesigned_ui'),
  'isRedesignEnabled()': isRedesignEnabled(),
  'useRedesignedUI.value': useRedesignedUI.value,
  'All import.meta.env': import.meta.env
})

// Add CSS for the environment error notification
const addEnvErrorStyles = () => {
  const style = document.createElement('style')
  style.textContent = `
    .env-error-notification {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.9);
      z-index: 10000;
      display: flex;
      justify-content: center;
      align-items: center;
      color: white;
      padding: 20px;
      box-sizing: border-box;
    }
    
    .env-error-content {
      background: #ff4444;
      border: 3px solid #ff0000;
      border-radius: 10px;
      padding: 30px;
      max-width: 800px;
      text-align: center;
      box-shadow: 0 0 30px rgba(255, 0, 0, 0.5);
    }
    
    .env-error-content h2 {
      color: #ffffff;
      margin-bottom: 20px;
      font-size: 24px;
    }
    
    .env-error-content p {
      margin: 10px 0;
      font-size: 16px;
      line-height: 1.5;
    }
    
    .env-error-content strong {
      color: #ffffff;
    }
    
    .error-details {
      background: rgba(0, 0, 0, 0.3);
      border-radius: 5px;
      padding: 15px;
      margin: 20px 0;
      text-align: left;
    }
    
    .error-details ul {
      margin: 10px 0;
      padding-left: 20px;
    }
    
    .error-details li {
      margin: 5px 0;
      font-family: monospace;
    }
    
    .retry-button {
      background: #ffffff;
      color: #ff4444;
      border: none;
      padding: 12px 24px;
      font-size: 16px;
      font-weight: bold;
      border-radius: 5px;
      cursor: pointer;
      margin-top: 20px;
    }
    
    .retry-button:hover {
      background: #ffdddd;
    }
  `
  document.head.appendChild(style)
}

// Function to check environment configuration
const checkEnvironmentConfig = async () => {
  try {
    // Reset error state
    envConfigError.value = false
    envConfigErrorDetails.value = []
    
    // Check if required environment variables are present
    const requiredEnvVars = [
      'VITE_API_BASE_URL',
      'VITE_TELEGRAM_BOT_USERNAME'
    ]
    
    const missingEnvVars = requiredEnvVars.filter(varName => !import.meta.env[varName])
    
    if (missingEnvVars.length > 0) {
      envConfigError.value = true
      envConfigErrorDetails.value.push(
        `Missing required environment variables: ${missingEnvVars.join(', ')}`
      )
    }
    
    // Check API connectivity
    try {
      const response = await fetch('/api/health')
      if (!response.ok) {
        envConfigError.value = true
        envConfigErrorDetails.value.push(
          `API health check failed: ${response.status} ${response.statusText}`
        )
      }
    } catch (error) {
      envConfigError.value = true
      envConfigErrorDetails.value.push(
        `API connectivity error: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    }
    
    // Check authentication system health
    try {
      const authResponse = await fetch('/api/users/me', {
        method: 'GET',
        credentials: 'include'
      })
      
      // If we get a 401, that's expected for unauthenticated users
      // But if we get a 500 or other server error, there's a configuration issue
      if (authResponse.status >= 500) {
        envConfigError.value = true
        envConfigErrorDetails.value.push(
          `Authentication system error: ${authResponse.status} ${authResponse.statusText}`
        )
        
        // Add specific S3 configuration error message
        envConfigErrorDetails.value.push(
          '🚨 S3 SESSION STORAGE CONFIGURATION ERROR DETECTED 🚨'
        )
        envConfigErrorDetails.value.push(
          'This typically indicates missing or invalid S3/Yandex Cloud credentials'
        )
        envConfigErrorDetails.value.push(
          'Check that YC_ACCESS_KEY_ID, YC_SECRET_ACCESS_KEY, and BUCKET_NAME are properly set'
        )
      }
    } catch (error) {
      envConfigError.value = true
      envConfigErrorDetails.value.push(
        `Authentication system connectivity error: ${error instanceof Error ? error.message : 'Unknown error'}`
      )
    }
    
    // If we're in TMA, check TMA-specific configuration
    if (window.Telegram?.WebApp) {
      try {
        const response = await fetch('/api/telegram/bot-info')
        const data = await response.json()

        // Check if bot is properly configured
        if (!response.ok || data.status === 'error' || data.status === 'not_initialized' || data.status === 'initialization_failed') {
          envConfigError.value = true
          let errorMessage = `Telegram bot configuration error: ${response.status} ${response.statusText}`
          if (data.message) {
            errorMessage += ` - ${data.message}`
          }
          envConfigErrorDetails.value.push(errorMessage)
        }
      } catch (error) {
        envConfigError.value = true
        envConfigErrorDetails.value.push(
          `Telegram connectivity error: ${error instanceof Error ? error.message : 'Unknown error'}`
        )
      }
    }
    
  } catch (error) {
    envConfigError.value = true
    envConfigErrorDetails.value.push(
      `Environment configuration check failed: ${error instanceof Error ? error.message : 'Unknown error'}`
    )
  }
}

// Retry function for environment check
const retryEnvCheck = () => {
  checkEnvironmentConfig()
}

// Check environment configuration on mount
onMounted(async () => {
  addEnvErrorStyles()
  await checkEnvironmentConfig()
  // Initialize auth state to end loading when possible
  await initializeAuthState()
  
  // Setup TMA event listeners but DON'T start monitoring immediately
  if (tmaService.isTMA) {
    setupTMAEventListeners();
    
    // Start monitoring only after everything is stable (5 seconds delay)
    setTimeout(() => {
      if (isAuth.value && currentUserId.value) {
        console.log('🔍 Starting delayed account monitoring after stabilization...');
        startAccountMonitoring();
      }
    }, 5000);
  }
});

onUnmounted(() => {
  stopAccountMonitoring();
  
  // Clean up TMA refresh interval
  if ((window as any).tmaRefreshInterval) {
    clearInterval((window as any).tmaRefreshInterval);
    (window as any).tmaRefreshInterval = null;
  }
});


const onLogin = async () => {
  // Login means we have backend auth, but worker still requires Telegram session file
  isAuth.value = true
  showLogin.value = false
  showLanding.value = false
  currentPage.value = 'dashboard'

  await fetchCurrentUser()

  // After login, ensure Telegram session file exists
  const token = localStorage.getItem('auth_token')
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = 'Bearer ' + token

  const hasSession = await checkTelegramSessionExists(headers)
  if (!hasSession) {
    console.warn('Telegram session missing after login; forcing phone auth')
    telegramSessionRequired.value = true
    isAuth.value = false
    showLogin.value = true
    showLanding.value = false
    return
  }

  telegramSessionRequired.value = false
  await initializeRedesignedUIData()
}

const checkTelegramSessionExists = async (headers: Record<string, string>): Promise<boolean> => {
  try {
    const resp = await axios.get('/api/channel_pairs/session-exists', {
      withCredentials: true,
      headers
    })
    return !!resp.data?.session_exists
  } catch (e) {
    console.warn('Failed to check telegram session existence:', e)
    return false
  }
}

// Initialize authentication state and finish loading
const initializeAuthState = async () => {
  try {
    // Prefer token from localStorage (TMA) but also allow cookie session
    const token = localStorage.getItem('auth_token');
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = 'Bearer ' + token;
    const resp = await axios.get('/api/users/me', { withCredentials: true, headers });
    // Authenticated
    isAuth.value = true;
    currentUserId.value = resp.data.id;
    dashboardData.userInfo = resp.data;

    // Gate dashboard by Telegram session file availability
    const hasSession = await checkTelegramSessionExists(headers)
    if (!hasSession) {
      console.log('Authenticated, but Telegram session file missing; showing LoginForm for phone auth')
      telegramSessionRequired.value = true
      isAuth.value = false
      showLogin.value = true
      showLanding.value = false
      return
    }

    telegramSessionRequired.value = false
    showLogin.value = false;
    showLanding.value = false;
  } catch (e) {
    // Not authenticated: show landing or login depending on environment
    isAuth.value = false;
    if (tmaService.isTMA) {
      // In TMA, try automatic authentication once
      try {
        await tmaService.authenticateWithBackend();
        const token = localStorage.getItem('auth_token');
        if (token) {
          const headers: Record<string, string> = { Authorization: 'Bearer ' + token };
          const resp = await axios.get('/api/users/me', { withCredentials: true, headers });
          isAuth.value = true;
          currentUserId.value = resp.data.id;
          dashboardData.userInfo = resp.data;

           // Gate dashboard by Telegram session file existence
           const hasSession = await checkTelegramSessionExists(headers)
           if (!hasSession) {
             console.log('TMA auth ok, but Telegram session file missing; forcing phone auth')
             telegramSessionRequired.value = true
             isAuth.value = false
             showLogin.value = true
             showLanding.value = false
             return
           }

           telegramSessionRequired.value = false
           showLogin.value = false;
           showLanding.value = false;
        }
      } catch (err) {
        // Fall back to login form inside TMA if auto auth fails
        telegramSessionRequired.value = true
        showLogin.value = true;
      }
    } else {
      // Regular web: optionally perform backdoor autologin
      if (isBackdoorAutologinEnabled()) {
        try {
          // Получаем токен через бэкдор
          const bdResp = await axios.get('/api/backdoor/login/user/2', { withCredentials: true });
          const backdoorToken = bdResp.data?.backdoor_token || bdResp.data?.access_token || bdResp.data?.token;
          if (backdoorToken) {
            localStorage.setItem('auth_token', backdoorToken);
            const headers: Record<string, string> = { Authorization: 'Bearer ' + backdoorToken };
            const meResp = await axios.get('/api/users/me', { withCredentials: true, headers });
            isAuth.value = true;
            currentUserId.value = meResp.data.id;
            dashboardData.userInfo = meResp.data;
            showLogin.value = false;
            showLanding.value = false;
          } else {
            // Если токен не вернулся, показываем лендинг
            showLanding.value = true;
          }
        } catch (err) {
          console.error('Backdoor autologin failed:', err);
          showLanding.value = true;
        }
      } else {
        // Regular web: show landing for non-auth users
        showLanding.value = true;
      }
    }
  } finally {
    // Finish loading regardless of outcome
    isLoading.value = false;

    // Initialize language service after authentication check
    try {
      const languageService = (await import('./services/language')).LanguageService.getInstance();
      const apiLanguage = await languageService.getUserLanguage();
      console.log('🎯 App.vue: Language service initialized with language:', apiLanguage);

      // Update i18n if API returned a different language
      if (apiLanguage && apiLanguage !== locale.value) {
        console.log('🎯 App.vue: Updating i18n locale to:', apiLanguage);
        locale.value = apiLanguage as 'en' | 'ru';
        const localizationService = (await import('./services/localization')).LocalizationService.getInstance();
        localizationService.setLanguage(apiLanguage);
      }
    } catch (error) {
      console.error('🎯 App.vue: Error initializing language service:', error);
    }

    // Initialize redesigned UI data when authenticated
    if (isAuth.value) {
      await initializeRedesignedUIData();
    }
  }
}

// Prevent reference error; wire essential TMA listeners
const setupTMAEventListeners = () => {
  if (!tmaService.isTMA || !window.Telegram?.WebApp) return;
  const webApp = window.Telegram.WebApp;
  try {
    // Ready/expand handled in tmaService.initialize, here we manage buttons
    webApp.BackButton.onClick(() => {
      // Close mini app or navigate to dashboard
      currentPage.value = 'dashboard';
    });
    // Main button for worker controls removed - functionality duplicated in dashboard
    // if (dashboardData.workerData?.status) {
    //   tmaService.setupWorkerControls(String(dashboardData.workerData.status));
    // }
  } catch (err) {
    console.error('setupTMAEventListeners: failed', err);
  }
}

// Account monitoring for TMA (detect account switch)
let accountMonitorInterval: number | null = null;
const startAccountMonitoring = () => {
  if (!tmaService.isTMA) return;
  if (accountMonitorInterval) return;
  const lastInitData = tmaService.getInitData();
  accountMonitorInterval = window.setInterval(async () => {
    try {
      // Skip monitoring if token refresh is already in progress
      if (tmaService.isRefreshingToken) {
        console.log('Account monitoring: Skipping - token refresh already in progress');
        return;
      }
      
      // If initData changed, refresh auth
      if (tmaService.hasInitDataChanged(lastInitData)) {
        console.log('Account monitoring: initData changed, refreshing user data');
        await tmaService.refreshUserData();
        const token = localStorage.getItem('auth_token');
        if (token) {
          const headers: Record<string, string> = { Authorization: 'Bearer ' + token };
          const resp = await axios.get('/api/users/me', { withCredentials: true, headers });
          currentUserId.value = resp.data.id;
          dashboardData.userInfo = resp.data;
        }
      } else if (currentUserId.value) {
        // Only validate periodically if worker is not actively running
        // This prevents unnecessary validation during worker operations
        const workerStatus = dashboardData.workerData?.status;
        const isWorkerActive = ['running', 'active', 'starting', 'pending', 'processing'].includes(workerStatus);
        
        if (!isWorkerActive) {
          // Validate current user id periodically
          const isValid = await tmaService.validateCurrentUser(currentUserId.value);
          if (!isValid) {
            console.log('Account monitoring: User validation failed, refreshing');
            await tmaService.refreshUserData();
            await fetchUserInfo();
          }
        }
      }
    } catch (err) {
      console.error('Account monitoring error:', err);
    }
  }, 5000);
}

const stopAccountMonitoring = () => {
  if (accountMonitorInterval) {
    clearInterval(accountMonitorInterval);
    accountMonitorInterval = null;
  }
}

// Helpers for worker start lock used in startWorker
const lockWorkerStart = () => {
  dashboardData.isStartLocked = true;
}
const releaseWorkerStartLock = () => {
  if (dashboardData.isStartLocked) dashboardData.isStartLocked = false;
}

// Reset aggregated dashboard data on logout
const resetDashboardData = () => {
  dashboardData.userInfo = null;
  dashboardData.workerData = null;
  dashboardData.loading = false;
  dashboardData.error = null;
  dashboardData.isWorkerToggling = false;
  dashboardData.isStartLocked = false;
  dashboardData.hasChannelRules = false;
  dashboardData.scheduledPosts = [];
  dashboardData.realtimeLogs = [];
  dashboardData.workerErrors = [];
  dashboardData.rules = [];
  dashboardData.subscribedChannels = [];
  dashboardData.adminChannels = [];
  dashboardData.loadingChannels = false;
}

// Handle account refresh request from RedesignedApp
const handleAccountSwitch = async () => {
  try {
    await tmaService.refreshUserData();
    await fetchUserInfo();
    await initializeRedesignedUIData();
  } catch (err) {
    console.error('handleAccountSwitch: failed to refresh account', err);
  }
}

const onStartTrial = () => {
  // Пользователь захотел начать — открываем форму логина/регистрации
  console.log('LandingPage: startTrial clicked -> showing LoginForm')
  showLanding.value = false
  showLogin.value = true
  telegramSessionRequired.value = true
  // Guard: never show global loader here
  isLoading.value = false
  authError.value = null
}

const handleNavigation = (page: string) => {
  currentPage.value = page
}

const fetchCurrentUser = async () => {
  // fetchCurrentUser: Starting to fetch current user
  try {
    const token = localStorage.getItem('auth_token')
    const headers: Record<string, string> = {}
    if (token) {
      headers['Authorization'] = 'Bearer ' + token
    }
    const response = await axios.get('/api/users/me', { withCredentials: true, headers })
    // fetchCurrentUser: Response received
    currentUserId.value = response.data.id
    
    // Populate dashboardData for RedesignedApp
    dashboardData.userInfo = response.data
    
    // fetchCurrentUser: User ID set
  } catch (error) {
    console.error('fetchCurrentUser: Failed to fetch current user:', error)
    // Even if failed, show dashboard for authenticated users
  }
}

// Fetch user info method from Dashboard
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
    
    // Update dashboardData for RedesignedApp
    dashboardData.userInfo = response.data;
    currentUserId.value = response.data.id;
  } catch (error) {
    console.error('fetchUserInfo: Failed to fetch user info:', error);
  }
};

// Fetch worker status method from Dashboard
const fetchWorkerStatus = async (showLoading = false) => {
  try {
    if (showLoading) {
      dashboardData.loading = true;
    }
    
    // Skip fetch if token refresh is in progress to avoid 401 errors
    if (tmaService.isRefreshingToken) {
      console.log('fetchWorkerStatus: Skipping - token refresh in progress');
      if (showLoading) {
        dashboardData.loading = false;
      }
      return;
    }
    
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    const response = await axios.get('/api/workers/status', {
      withCredentials: true,
      headers
    });
    
    dashboardData.workerData = response.data;
    
    if (showLoading) {
      dashboardData.loading = false;
    }
  } catch (error: any) {
    // Handle 401 errors gracefully - likely a race condition with token refresh
    if (error.response?.status === 401) {
      console.log('fetchWorkerStatus: Got 401, likely token refresh in progress - will retry');
      // Don't set error state for 401 during refresh, just skip this update
      if (showLoading) {
        dashboardData.loading = false;
      }
      return;
    }
    console.error('fetchWorkerStatus: Failed to fetch worker status:', error);
    if (showLoading) {
      dashboardData.loading = false;
    }
    dashboardData.error = 'Failed to fetch worker status';
  }
};

// Worker control methods (copied from Dashboard.vue logic)
const startWorker = async () => {
  console.log('🚀 App.vue startWorker: Called with state:', {
    isStartLocked: dashboardData.isStartLocked,
    isWorkerToggling: dashboardData.isWorkerToggling,
    workerStatus: dashboardData.workerData?.status,
    hasChannelRules: dashboardData.hasChannelRules,
    userBalance: dashboardData.userInfo?.balance
  });
  
  if (dashboardData.isStartLocked || dashboardData.isWorkerToggling || dashboardData.workerData?.status === 'running' || dashboardData.workerData?.status === 'active' ||
      dashboardData.workerData?.status === 'starting' || dashboardData.workerData?.status === 'pending' || dashboardData.workerData?.status === 'processing') {
    console.log('🚀 App.vue startWorker: Blocked by worker status or lock');
    return;
  }

  lockWorkerStart();
  let startRequestInitiated = false;
  const startTime = Date.now();

  try {
    // Check balance - only block if negative
    if (dashboardData.userInfo && dashboardData.userInfo.balance !== undefined && dashboardData.userInfo.balance < 0) {
      console.log('🚀 App.vue startWorker: Blocked by negative balance');
      dashboardData.error = 'Insufficient balance';
      releaseWorkerStartLock();
      return;
    }

    // Refresh channel rules before checking to ensure we have the latest state
    console.log('🚀 App.vue startWorker: Refreshing channel rules before start...');
    await fetchChannelRules();

    if (!dashboardData.hasChannelRules) {
      console.log('🚀 App.vue startWorker: Blocked by no channel rules after refresh');
      dashboardData.error = 'Cannot start: no rules configured';
      releaseWorkerStartLock();
      return;
    }

    console.log('🚀 App.vue startWorker: All checks passed, starting worker...');
    dashboardData.error = null;

    console.log('Sending worker start request...');

    const token = localStorage.getItem('auth_token');
    const headers: any = {};

    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    startRequestInitiated = true;
    const response = await axios.post('/api/workers/start', {}, { 
      withCredentials: true,
      headers
    });

    console.log(`✅ App.vue startWorker: Worker start response received in ${Date.now() - startTime}ms`, response.data);

    // Update worker data
    dashboardData.workerData = response.data;
    console.log('✅ App.vue startWorker: Worker data updated, new status:', dashboardData.workerData?.status);

    // Более частое обновление статуса после запуска для быстрого отклика
    const quickRefreshInterval = setInterval(async () => {
      await fetchWorkerStatus();
      const status = dashboardData.workerData?.status;
      if (status === 'running' || status === 'active') {
        clearInterval(quickRefreshInterval);
        releaseWorkerStartLock();
        console.log('App.vue startWorker: Worker is now running, releasing start lock');
      } else if (status === 'error' || status === 'auth_required') {
        clearInterval(quickRefreshInterval);
        releaseWorkerStartLock();
        console.log('App.vue startWorker: Worker reached error/auth state, releasing start lock');
      }
    }, 500);

    await fetchWorkerStatus();

  } catch (error: unknown) {
    console.error('Failed to start worker:', error);
    dashboardData.error = (error as any).response?.data?.detail || 'Failed to start worker';
    await fetchWorkerStatus();
    releaseWorkerStartLock();
  } finally {
    if (!startRequestInitiated) {
      releaseWorkerStartLock();
    }
  }
};

const stopWorker = async () => {
  console.log('🛑 App.vue stopWorker: Called');
  
  if (dashboardData.isWorkerToggling) {
    console.log('🛑 App.vue stopWorker: Blocked by isWorkerToggling');
    return;
  }
  
  dashboardData.isWorkerToggling = true;
  dashboardData.error = null;
  
  try {
    console.log('Sending worker stop request...');
    
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    
    const response = await axios.post('/api/workers/stop', {}, { 
      withCredentials: true,
      headers
    });
    
    console.log('Worker stop response:', response.data);
    
    // Update worker data
    dashboardData.workerData = response.data;
    
    // Refresh status after a short delay
    setTimeout(async () => {
      await fetchWorkerStatus(); // Background update, no loading
    }, 1000);
    
  } catch (error: unknown) {
    console.error('Failed to stop worker:', error);
    dashboardData.error = (error as any).response?.data?.detail || 'Failed to stop worker';
  } finally {
    dashboardData.isWorkerToggling = false;
  }
};

const toggleWorker = async () => {
  if (dashboardData.isWorkerToggling || dashboardData.isStartLocked) return;
  
  const isRunning = dashboardData.workerData?.status === 'running' || dashboardData.workerData?.status === 'active';
  
  if (isRunning) {
    await stopWorker();
  } else {
    await startWorker();
  }
};

// Fetch scheduled posts logs
const fetchScheduledPosts = async () => {
  try {
    console.log('🎯 App.vue: fetchScheduledPosts called');
    const token = localStorage.getItem('auth_token');
    console.log('🎯 App.vue: Token exists:', !!token, token ? '(' + token.substring(0, 20) + '...)' : 'no token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    console.log('🎯 App.vue: Making request to /api/workers/logs/scheduled_posts with headers:', Object.keys(headers));
    const response = await axios.get('/api/workers/logs/scheduled_posts', { 
      withCredentials: true,
      headers
    });
    console.log('🎯 App.vue: fetchScheduledPosts response:', response.data?.length || 0, 'items');
    dashboardData.scheduledPosts = response.data;
  } catch (err: unknown) {
    console.error('🎯 App.vue: fetchScheduledPosts error:', (err as any).response?.status, (err as any).response?.data || (err as any).message);
  }
};

// Fetch worker errors logs
const fetchWorkerErrors = async () => {
  try {
    console.log('🎯 App.vue: fetchWorkerErrors called');
    const token = localStorage.getItem('auth_token');
    console.log('🎯 App.vue: Token exists:', !!token, token ? '(' + token.substring(0, 20) + '...)' : 'no token');
    const headers: any = {};
    
    if (token) {
      headers['Authorization'] = 'Bearer ' + token;
    }
    
    console.log('🎯 App.vue: Making request to /api/workers/logs/errors with headers:', Object.keys(headers));
    const response = await axios.get('/api/workers/logs/errors', { 
      withCredentials: true,
      headers
    });
    console.log('🎯 App.vue: fetchWorkerErrors response:', response.data?.length || 0, 'items');
    dashboardData.workerErrors = response.data;
  } catch (err: unknown) {
    console.error('🎯 App.vue: fetchWorkerErrors error:', (err as any).response?.status, (err as any).response?.data || (err as any).message);
  }
};

// Fetch realtime logs (fallback for when WebSocket is not available)
const fetchRealtimeLogs = async () => {
  console.log('🎯 App.vue: fetchRealtimeLogs НЕ ИСПОЛЬЗУЕТСЯ - только WebSocket');
  // НЕ ДЕЛАЕМ HTTP ЗАПРОСЫ - ТОЛЬКО WEBSOCKET!
};

// Function to check if message contains post content that should not be translated
const isPostContentMessage = (message: string | null | undefined): boolean => {
  if (!message || typeof message !== 'string') {
    return false;
  }
  return message.includes('Выходной текст:') ||
         message.includes('Output text:') ||
         message.includes('Сообщение запланировано:') ||
         message.includes('Message scheduled:');
};

// Function to translate log messages (same as Dashboard)
const translateLogMessage = (message: string | null | undefined): string => {
  if (!message || typeof message !== 'string') {
    return message || '';
  }
  
  try {
    // Use the locale extracted at setup time, not inside the function
    if (locale.value !== 'ru') {
      return message;
    }

  const translations: { [key: string]: string } = {
    'Dashboard connected to real-time logs': 'Панель управления подключена к журналу в реальном времени',
    '⏳ Worker is now idle and waiting for new messages': '⏳ Агент готов и ожидает новые сообщения',
    'Worker is now idle and waiting for new messages': 'Агент готов и ожидает новые сообщения',
    '🔗 Connecting to Telegram...': '🔗 Подключение к Telegram...',
    'Connecting to Telegram...': 'Подключение к Telegram...',
    '🚀 Worker initialized successfully': '🚀 Агент успешно инициализирован',
    'Worker initialized successfully': 'Агент успешно инициализирован',
    '✅ Worker ready and waiting for new messages': '✅ Агент готов и ожидает новые сообщения',
    'Worker ready and waiting for new messages': 'Агент готов и ожидает новые сообщения',
    'Worker connected to Telegram and ready to process messages': 'Агент подключился к Telegram и готов обрабатывать сообщения',
    '✅ Batch processing completed': '✅ Пакетная обработка завершена',
    'Batch processing completed': 'Пакетная обработка завершена',
    '🔄 Starting batch processing of accumulated posts': '🔄 Начинается пакетная обработка накопленных постов',
    'Starting batch processing of accumulated posts': 'Начинается пакетная обработка накопленных постов'
  };

  if (translations[message]) {
    return translations[message];
  }

  // Pattern matching for common messages
  if (message.toLowerCase().includes('worker is now idle') || message.toLowerCase().includes('waiting for new messages')) {
    return 'Агент готов и ожидает новые сообщения';
  }
  
  if (message.toLowerCase().includes('connecting to telegram')) {
    return 'Подключение к Telegram...';
  }
  
  if (message.includes('Connected to Telegram as')) {
    return message.replace('Connected to Telegram as', 'Подключен к Telegram как');
  }

  if (message.includes('New message') && message.includes('from')) {
    return message.replace('New message', 'Новое сообщение').replace('from', 'из');
  }

  if (message.includes('Message scheduled:')) {
    return message.replace('Message scheduled:', 'Сообщение запланировано:');
  }

  return message;
  } catch (e) {
    // If translation fails for any reason, return original message
    console.warn('🎯 App.vue: translateLogMessage error:', e);
    return message || '';
  }
};

// WebSocket connection for real-time logs
const connectWebSocket = () => {
  if (!currentUserId.value) return;
  
  // Определяем правильный WebSocket URL
  // В production (включая TMA) используем nginx proxy без порта
  // В режиме разработки используем API сервер на порту 8000
  let host = window.location.host;
  let protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // Для TMA и production используем nginx proxy (без порта 8000)
  // Исправленная логика: если мы в TMA или в production (не на порту разработки)
  const isDevelopment = window.location.hostname === 'localhost' && 
                       (window.location.port === '5173' || window.location.port === '5174');
  
  if (!isDevelopment) {
    // В production и TMA используем nginx proxy (без порта 8000)
    // Убираем порт из хоста если он есть (используем nginx proxy)
    if (host.includes(':')) {
      host = host.split(':')[0];
    }
    // protocol остается как есть (wss: для https, ws: для http)
  } else {
    // Режим разработки - подключаемся напрямую к бэкенду
    if (host.includes(':5173')) {
      host = host.replace(':5173', ':8000');
    } else if (host.includes(':5174')) {
      host = host.replace(':5174', ':8000');
    }
  }
  
  const wsUrl = protocol + '//' + host + '/api/ws/' + currentUserId.value;
  console.log('App.vue: Connecting to WebSocket:', wsUrl);
  websocket.value = new WebSocket(wsUrl);
  
  setTimeout(() => {
    if (!websocketConnected.value) {
      console.log('App.vue: WebSocket failed to connect, starting fallback');
      startFallbackLogUpdates();
    }
  }, 5000);
  
  websocket.value.onopen = () => {
    console.log('App.vue: WebSocket connected for real-time logs');
    websocketConnected.value = true;
    
    if (fallbackLogTimer.value) {
      clearInterval(fallbackLogTimer.value);
      fallbackLogTimer.value = null;
    }
  };
  
  websocket.value.onmessage = (event) => {
    let data;
    try {
      if (event.data === 'ping' || event.data === 'pong') {
        // Handle raw ping/pong strings if they occur
        return;
      }
      data = JSON.parse(event.data);
    } catch (e) {
      // Log the raw message for debugging purposes, but don't treat it as a critical error
      console.log('🎯 App.vue: Received non-JSON WebSocket message:', event.data);
      return;
    }

    try {
      console.log('🎯 App.vue: WebSocket message received:', data.type, data.message?.substring(0, 50));

      // Handle different message types
      if (data.type === 'log') {
        let message = data.message || '';
        
        // Try to translate the message
        try {
          if (data.message_key && typeof data.message_key === 'string') {
            // Wrap $t call in try-catch as it can throw SyntaxError for invalid message keys
            try {
              message = $t(data.message_key, data.message_params || {});
            } catch (i18nError) {
              console.warn('🎯 App.vue: i18n translation error for key:', data.message_key, i18nError);
              // Fall back to original message or key itself
              message = data.message || data.message_key;
            }
          } else if (message && typeof message === 'string') {
            if (!isPostContentMessage(message)) {
              message = translateLogMessage(message);
            }
          }
        } catch (translationError) {
          // If translation fails, use the original message
          console.warn('🎯 App.vue: Translation error, using original message:', translationError);
          message = data.message || data.message_key || 'Unknown message';
        }

        // Ensure message is a valid string
        if (!message || typeof message !== 'string') {
          message = data.message_key || data.message || 'Unknown message';
        }

        // Safely compare timestamps with null checks
        let currentTimestamp: number;
        try {
          currentTimestamp = data.timestamp ? new Date(data.timestamp).getTime() : Date.now();
        } catch {
          currentTimestamp = Date.now();
        }

        const isDuplicate = dashboardData.realtimeLogs.some(log => {
          try {
            const logTimestamp = log.timestamp ? new Date(log.timestamp).getTime() : 0;
            return log.message === message &&
              log.log_type === data.log_type &&
              Math.abs(logTimestamp - currentTimestamp) < 1000;
          } catch {
            return false;
          }
        });

        if (!isDuplicate) {
          dashboardData.realtimeLogs.unshift({
            id: Date.now(),
            timestamp: data.timestamp,
            log_type: data.log_type,
            level: data.level,
            message: message
          });
          console.log('🎯 App.vue: Added realtime log, total:', (dashboardData.realtimeLogs || []).length);

          if ((dashboardData.realtimeLogs || []).length > 50) {
            dashboardData.realtimeLogs = dashboardData.realtimeLogs.slice(0, 50);
          }
        } else {
          console.log('🎯 App.vue: Duplicate log ignored');
        }
      }
      // Handle ping/pong messages for connection keep-alive
      else if (data.type === 'ping' || data.type === 'pong') {
        console.log('🎯 App.vue: WebSocket keep-alive message:', data.type);
        // No action needed for ping/pong messages
      }
      // Handle other message types if needed
      else {
        console.log('🎯 App.vue: Unknown WebSocket message type:', data.type);
      }
    } catch (error) {
      console.error('App.vue: Error processing WebSocket message:', error);
    }
  };
  
  websocket.value.onclose = () => {
    console.log('App.vue: WebSocket disconnected, attempting to reconnect...');
    websocketConnected.value = false;
    // Only start fallback if we're not in TMA (Telegram WebApp has different requirements)
    if (!window.Telegram || !window.Telegram.WebApp) {
      startFallbackLogUpdates();
    }
    setTimeout(connectWebSocket, 3000);
  };
  
  websocket.value.onerror = (error) => {
    console.error('App.vue: WebSocket error:', error);
    websocketConnected.value = false;
    // Only start fallback if we're not in TMA (Telegram WebApp has different requirements)
    if (!window.Telegram || !window.Telegram.WebApp) {
      startFallbackLogUpdates();
    }
  };
};

const disconnectWebSocket = () => {
  if (websocket.value) {
    websocket.value.close();
    websocket.value = null;
  }
  websocketConnected.value = false;
  
  if (fallbackLogTimer.value) {
    clearInterval(fallbackLogTimer.value);
    fallbackLogTimer.value = null;
  }
};

const startFallbackLogUpdates = () => {
  if (websocketConnected.value || fallbackLogTimer.value) return;
  
  console.log('App.vue: Starting HTTP fallback for logs');
  
  // Функция для получения логов через HTTP
  const fetchLogsViaHTTP = async () => {
    try {
      const token = localStorage.getItem('auth_token');
      const headers: any = {};
      
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }
      
      // Получаем логи через HTTP endpoint
      const response = await axios.get('/api/logs/realtime', {
        withCredentials: true,
        headers,
        params: { limit: 20 }
      });
      
      // Обрабатываем полученные логи
      if (response.data && Array.isArray(response.data)) {
        response.data.forEach((log: any) => {
          const isDuplicate = dashboardData.realtimeLogs.some(existingLog => 
            existingLog.message === log.message && 
            existingLog.log_type === log.log_type &&
            Math.abs(new Date(existingLog.timestamp).getTime() - new Date(log.timestamp).getTime()) < 1000
          );
          
          if (!isDuplicate) {
            dashboardData.realtimeLogs.unshift({
              id: Date.now() + Math.random(),
              timestamp: log.timestamp,
              log_type: log.log_type,
              level: log.level || 'info',
              message: log.message
            });
            
            if ((dashboardData.realtimeLogs || []).length > 50) {
              dashboardData.realtimeLogs = dashboardData.realtimeLogs.slice(0, 50);
            }
          }
        });
      }
    } catch (error) {
      console.error('App.vue: Error fetching logs via HTTP:', error);
    }
  };
  
  // Начинаем опрос логов через HTTP
  fallbackLogTimer.value = setInterval(async () => {
    if (websocketConnected.value) {
      clearInterval(fallbackLogTimer.value!);
      fallbackLogTimer.value = null;
      return;
    }
    
    // Получаем логи через HTTP
    await fetchLogsViaHTTP();
  }, 5000); // Опрос каждые 5 секунд
};



// Initialize data for redesigned UI
const initializeRedesignedUIData = async () => {
  if (useRedesignedUI.value) {
    console.log('🎯 TMA: Initializing redesigned UI data...');
    
    // ОЧИЩАЕМ ВСЕ ЛОГИ СРАЗУ
    dashboardData.realtimeLogs.splice(0);
    dashboardData.scheduledPosts.splice(0);
    dashboardData.workerErrors.splice(0);
    console.log('🎯 TMA: All logs cleared at start');
    
    // Check token before making API calls
    const token = localStorage.getItem('auth_token');
    console.log('🎯 TMA: Token check before API calls:', token ? token.substring(0, 20) + '...' : 'NO TOKEN');
    
    dashboardData.loading = true;
    await fetchUserInfo();
    await fetchWorkerStatus(true);
    await fetchChannelRules();

    // Auto-open RuleWizard for first-time users with no rules.
    // RuleWizard is inside ChannelPairs tab; handleOpenRuleWizard will switch tabs.
    if (!dashboardData.hasChannelRules) {
      console.log('🎯 TMA: No channel rules found -> auto-opening RuleWizard')
      // Defer until UI is mounted/stable
      setTimeout(() => {
        handleOpenRuleWizard().catch(err => {
          console.error('🎯 TMA: Failed to auto-open RuleWizard:', err)
        })
      }, 500)
    }
    
    // НЕ загружаем старые логи - только живые через WebSocket
    console.log('🎯 TMA: Skipping old logs loading - only live WebSocket logs');
    
    // НЕ ЗАГРУЖАЕМ НИКАКИХ СТАРЫХ ДАННЫХ - ТОЛЬКО WEBSOCKET
    console.log('🎯 TMA: Starting with completely empty logs - only WebSocket');
    
    console.log('🎯 TMA: Initialization complete, data:', {
      hasChannelRules: dashboardData.hasChannelRules,
      scheduledPosts: (dashboardData.scheduledPosts || []).length,
      realtimeLogs: (dashboardData.realtimeLogs || []).length,
      workerErrors: (dashboardData.workerErrors || []).length
    });
    dashboardData.loading = false;
    
    // Connect to WebSocket for real-time logs
    connectWebSocket();
    
    // Добавляем периодическое обновление статуса воркера
    console.log('🎯 TMA: Starting worker status monitoring');
    const statusInterval = setInterval(async () => {
      if (dashboardData.userInfo?.id) {
        await fetchWorkerStatus(false); // Без показа загрузки
      }
    }, 5000); // Каждые 5 секунд
    
    // Сохраняем интервал для очистки
    (window as any).tmaStatusInterval = statusInterval;
  }
};

// Fetch only channel rules (lightweight operation)
const fetchChannelRules = async () => {
  try {
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    
    const rulesResponse = await axios.get('/api/channel_pairs', {
      withCredentials: true,
      headers
    });
    
    const hasRules = rulesResponse.data && Array.isArray(rulesResponse.data) && rulesResponse.data.length > 0;
    dashboardData.hasChannelRules = hasRules;
    console.log('🎉 App.vue fetchChannelRules: hasChannelRules updated to:', hasRules);
    console.log('🎉 App.vue fetchChannelRules: Rules data:', rulesResponse.data);

  } catch (error) {
    console.error('Failed to fetch channel rules:', error);
    dashboardData.hasChannelRules = false;
  }
};

// Fetch channels data (heavy operation - only when needed for wizard)
const fetchChannels = async () => {
  try {
    console.log('🔄 App.vue: Loading channels for wizard...');
    const token = localStorage.getItem('auth_token');
    const headers: any = {};
    
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    
    const response = await axios.get('/api/channel_pairs/channels', {
      withCredentials: true,
      headers
    });
    
    dashboardData.subscribedChannels = response.data.subscribed_channels || [];
    dashboardData.adminChannels = response.data.admin_channels || [];
    console.log('✅ App.vue: Channels loaded for wizard - subscribed:', dashboardData.subscribedChannels.length, 'admin:', dashboardData.adminChannels.length);
  } catch (error) {
    console.error('Failed to fetch channels:', error);
  }
};

// New methods for redesigned UI
const showInfoPage = () => {
  currentPage.value = 'info'
}

const handleLogout = () => {
  // Clear authentication
  isAuth.value = false
  showLogin.value = false
  showLanding.value = true
  currentPage.value = 'dashboard'
  currentUserId.value = undefined
  resetDashboardData()
  
  // Clear stored tokens
  localStorage.removeItem('auth_token')
  document.cookie = 'access_token=; Max-Age=0; path=/'
}

const handleRuleCreated = async (channelInfo: any) => {
  console.log('🎉 App.vue: Rule created successfully:', channelInfo)
  
  // Update dashboard data to reflect that rules now exist
  await fetchChannelRules()
  console.log('🎉 App.vue: hasChannelRules updated to:', dashboardData.hasChannelRules)
}

const channelPairsRef = ref(null)

const handleOpenRuleWizard = async () => {
  console.log('🎯 TMA: Request to open rule wizard')

  // RuleWizard lives inside ChannelPairs, which is only mounted on the Channels tab.
  // Force tab switch first.
  forcedTab.value = 'channels'
  await nextTick()

  // Wait briefly for ChannelPairs to mount after tab switch
  const start = Date.now()
  while (!channelPairsRef.value && Date.now() - start < 4000) {
    await new Promise(resolve => setTimeout(resolve, 100))
  }

  // Load channels only when wizard is opened (heavy operation)
  if ((dashboardData.subscribedChannels || []).length === 0 && (dashboardData.adminChannels || []).length === 0) {
    console.log('🔄 TMA: Loading channels for wizard...')
    await fetchChannels()
  }

  // Try to use the injected openRuleWizard method first (rare; normally provider is not an ancestor)
  const openRuleWizard = inject('openRuleWizard', null)
  if (openRuleWizard && typeof openRuleWizard === 'function') {
    console.log('🎯 TMA: Calling injected openRuleWizard method')
    openRuleWizard()
    forcedTab.value = null
    return
  }

  console.log('🔗 ChannelPairs ref:', channelPairsRef.value)
  if (channelPairsRef.value) {
    console.log('✅ Calling openRuleWizard method on ChannelPairs component')
    await (channelPairsRef.value as any).openRuleWizard()
    console.log('🚀 Rule wizard opened successfully')
    forcedTab.value = null
  } else {
    console.error('❌ ChannelPairs ref is null - component not mounted (Channels tab)')
  }
}

const toggleUIDesign = (enabled: boolean) => {
  useRedesignedUI.value = enabled
  setRedesignPreference(enabled)
  
  // Force page refresh to apply new UI
  window.location.reload()
}

// Cleanup on unmount
onUnmounted(() => {
  if ((window as any).tmaRefreshInterval) {
    clearInterval((window as any).tmaRefreshInterval)
    ;(window as any).tmaRefreshInterval = null
  }
  if ((window as any).tmaStatusInterval) {
    clearInterval((window as any).tmaStatusInterval)
    ;(window as any).tmaStatusInterval = null
  }
  disconnectWebSocket()
})
</script>

<style>
/* Глобальные стили */
body {
  margin: 0;
  padding: 0;
  font-family: Arial, sans-serif;
}

#app {
  margin: 0;
  padding: 0;
  min-height: 100vh;
}

.loading-screen {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid rgba(255, 255, 255, 0.3);
  border-top: 4px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-screen p {
  font-size: 18px;
  font-weight: 500;
  margin: 0;
}

.auth-error {
  margin-top: 30px;
  text-align: center;
}

.error-message {
  color: #ffcccb;
  background: rgba(255, 255, 255, 0.1);
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 15px;
  font-size: 16px;
}

.retry-button {
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 2px solid rgba(255, 255, 255, 0.3);
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.retry-button:hover {
  background: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

/* Анимации переходов */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active, .slide-up-leave-active {
  transition: all 0.4s ease;
}

.slide-up-enter-from {
  opacity: 0;
  transform: translateY(30px);
}

.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-30px);
}

/* TMA специальные стили */
.tma-environment {
  background: var(--tg-theme-bg-color, #1a2c33) !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Убираем все фоны в TMA */
.tma-environment * {
  background: transparent !important;
}

.tma-environment .app-redesigned {
  background: transparent !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Убираем зеленый прямоугольник */
.tma-environment .redesigned-header {
  background: transparent !important;
}

/* Для светлой темы оставляем градиент */
body:not(.tma-environment) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
}

/* Убираем отступы и поля в TMA */
.tma-environment body,
.tma-environment html {
  margin: 0 !important;
  padding: 0 !important;
  overflow-x: hidden !important;
}
</style>

<style scoped>
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}
</style>
