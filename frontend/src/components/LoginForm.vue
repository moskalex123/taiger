<template>
  <div class="login-form">
    <!-- Language Selector -->
    <div class="language-selector">
      <select id="language-select" v-model="selectedLanguage" @change="changeLanguage">
        <option value="en">🇺🇸 English</option>
        <option value="ru">🇷🇺 Русский</option>
      </select>
    </div>

    <!-- TMA Authentication Loading -->
    <div v-if="tryingTMAAuth" class="tma-auth-loading">
      <div class="loading-spinner"></div>
      <p>{{ $t('authenticating_with_telegram') || 'Authenticating with Telegram...' }}</p>
    </div>

    <!-- Main Form -->
    <div v-else>
      <h2>{{ $t('login_title') || 'Login to Telegram' }}</h2>

      <form @submit.prevent="handleSubmit">
        <!-- Phone Number Input -->
        <div>
          <label for="phone">{{ $t('phone_number') || 'Phone Number' }}</label>
          <input
            id="phone"
            v-model="phoneNumber"
            type="tel"
            :placeholder="$t('phone_placeholder') || '+XXXXXXXXXX'"
            required
            :disabled="loading || checkingSession"
          />
        </div>

        <!-- Verification Code Input (shown after phone submission) -->
        <div v-if="codeSent">
          <label for="code">{{ $t('verification_code') || 'Verification Code' }}</label>
          <input
            id="code"
            v-model="code"
            type="text"
            :placeholder="$t('code_placeholder') || '12345'"
            required
            :disabled="loading"
          />
        </div>

        <!-- 2FA Password Input (shown when required) -->
        <div v-if="needsPassword">
          <label for="password">{{ $t('two_factor_password') || '2FA Password' }}</label>
          <input
            id="password"
            v-model="password"
            type="password"
            :placeholder="$t('password_placeholder') || 'Enter 2FA password'"
            required
            :disabled="loading"
          />
        </div>

        <!-- Submit Button -->
        <button
          type="submit"
          :disabled="loading || checkingSession"
        >
          <span v-if="checkingSession">{{ $t('checking_session') || 'Checking...' }}</span>
          <span v-else-if="codeSent">{{ $t('submit_code') || 'Submit Code' }}</span>
          <span v-else>{{ $t('send_code') || 'Send Code' }}</span>
        </button>
      </form>

      <!-- Info Messages -->
      <div v-if="!codeSent && !tryingTMAAuth" class="info">
        <div v-html="formatTelegramInfo($t('telegram_login_info') || 'Enter your phone number to authenticate with Telegram and create your session.')"></div>
      </div>

      <!-- Error Messages -->
      <div v-if="error" class="error">
        <p>{{ error }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="loading && !checkingSession" class="loading">
        <p>{{ $t('processing') || 'Processing...' }}</p>
      </div>
    </div>

    <!-- Success Modal -->
    <div v-if="showSuccessModal" class="modal-overlay" @click="closeSuccessModal">
      <div class="modal-content success-modal" @click.stop>
        <div class="modal-header">
          <h3>{{ $t('welcome_newcomer') || 'Welcome!' }}</h3>
          <button class="modal-close" @click="closeSuccessModal">&times;</button>
        </div>
        <div class="modal-body">
          <p class="intro-text">{{ $t('successful_login_title') }}</p>
          <p class="explanation-text">{{ $t('telegram_notification_explanation') }}</p>

          <!-- Image removed - not essential for functionality -->

          <p class="action-text">{{ $t('telegram_notification_intro') }}</p>

          <ul class="purpose-list">
            <li>{{ $t('telegram_notification_purpose_1') }}</li>
            <li>{{ $t('telegram_notification_purpose_2') }}</li>
            <li>{{ $t('telegram_notification_purpose_3') }}</li>
          </ul>

          <p class="security-text">{{ $t('telegram_security_note') }}</p>
        </div>
        <div class="modal-footer">
          <button class="modal-button primary" @click="closeSuccessModal">
            {{ $t('continue_to_dashboard') || 'Continue to Dashboard' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios' // Make sure axios is installed (npm install axios)
import { useI18n } from 'vue-i18n'
import { tmaService } from '../services/tma'
import { tmaLog } from '../utils/tmaUtils'

// Initialize i18n
const { t: $t, locale } = useI18n()

// Language selection
const selectedLanguage = ref(locale.value || 'en')

// Initialize language from Telegram app language or localStorage
const initializeLanguage = () => {
  // First try to get language from Telegram app
  if (tmaService.isTMA && window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code) {
    const tgLang = window.Telegram.WebApp.initDataUnsafe.user.language_code
    // Map Telegram language codes to our supported languages
    if (tgLang.startsWith('ru')) {
      selectedLanguage.value = 'ru'
      locale.value = 'ru'
      return
    } else if (tgLang.startsWith('en')) {
      selectedLanguage.value = 'en'
      locale.value = 'en'
      return
    }
  }

  // Fallback to localStorage
  const savedLang = localStorage.getItem('preferred_language')
  if (savedLang && (savedLang === 'en' || savedLang === 'ru')) {
    selectedLanguage.value = savedLang
    locale.value = savedLang
  }
}

// Initialize language on component load
initializeLanguage()

const props = defineProps<{ skipTmaAuth?: boolean }>()

const phoneNumber = ref('')
const code = ref('')
const password = ref('') // For 2FA
const codeSent = ref(false)
const phoneCodeHash = ref<string | null>(null) // Для хранения phone_code_hash
const codeSentTime = ref<string | null>(null) // Для хранения времени отправки кода
const needsPassword = ref(false) // Track if 2FA is needed
const loading = ref(false)
const error = ref<string | null>(null)
const checkingSession = ref(false)
const showSuccessModal = ref(false)
const tryingTMAAuth = ref(false)

const emit = defineEmits(['login'])

const changeLanguage = () => {
  locale.value = selectedLanguage.value
  // Save language preference to localStorage
  localStorage.setItem('preferred_language', selectedLanguage.value)
}

// Try TMA authentication first if available
const tryTMAAuthentication = async () => {
  tmaLog('tryTMAAuthentication called');
  tmaLog('tmaService.isTMA:', tmaService.isTMA);
  
  if (!tmaService.isTMA) {
    tmaLog('Not in TMA environment, skipping TMA auth');
    return false
  }
  
  try {
    tryingTMAAuth.value = true
    error.value = null
    
    tmaLog('Attempting TMA authentication...');
    const authData = await tmaService.authenticateWithBackend();
    tmaLog('TMA auth response:', authData);
    
    if (authData && authData.access_token) {
      tmaLog('TMA authentication successful');
      // Store token in cookie for compatibility with existing auth system
      const expiryDate = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000); // 7 days
      document.cookie = `access_token=${authData.access_token}; expires=${expiryDate.toUTCString()}; path=/; SameSite=Lax`;
      
      emit('login');
      return true;
    } else {
      tmaLog('TMA auth response missing access_token:', authData);
    }
  } catch (err: any) {
    console.error('TMA authentication failed:', err);
    error.value = $t('tma_auth_failed') || 'Не удалось войти через Telegram. Попробуйте ввести номер телефона.';
  } finally {
    tryingTMAAuth.value = false;
  }
  
  return false;
}

// Component mounted - try TMA auth first
onMounted(async () => {
  tmaLog('LoginForm mounted');
  tmaLog('window.Telegram:', window.Telegram);
  tmaLog('Current URL:', window.location.href);
  tmaLog('User Agent:', navigator.userAgent);

  // If the parent explicitly requires phone-based Telegram auth (session file creation),
  // do NOT auto-auth via TMA, otherwise we loop back to dashboard without a session.
  if (props.skipTmaAuth) {
    tmaLog('skipTmaAuth=true -> skipping TMA auto authentication');
    return;
  }

  const tmaSuccess = await tryTMAAuthentication();
  if (!tmaSuccess) {
    console.log('TMA authentication not available or failed, showing phone input');
  }
})

const handleSubmit = async () => {
  loading.value = true
  error.value = null
  needsPassword.value = false // Reset 2FA flag on new submission

  if (!codeSent.value) {
    // --- Сначала проверяем существующую сессию ---
    console.log('Проверка существующей сессии для номера:', phoneNumber.value);
    try {
      checkingSession.value = true;
      // Изменен URL с /api/check_session на /api/sessions/check
      // Используем /auth/login для проверки сессии и инициации входа/регистрации
      const response = await axios.post('/auth/login', { phone: phoneNumber.value }, { withCredentials: true });
      console.log('Результат вызова /auth/login:', response.data);

      if (response.data.access_token) {
        // Пользователь существует и успешно вошел в систему
        console.log('Пользователь существует и успешно вошел в систему');
        // Store the access token in localStorage for API interceptor
        localStorage.setItem('auth_token', response.data.access_token);
        console.log('🔍 Stored access token in localStorage for API interceptor');
        emit('login');
        return;
      } else if (response.data.status === 'redirect_to_dashboard') {
        // Пользователь аутентифицирован через куки, перенаправляем на дашборд
        console.log('Пользователь аутентифицирован через куки, перенаправляем на дашборд');
        emit('login');
        return;
      } else if (response.data.status === 'new_user_telegram_auth_required') {
        // Пользователь не найден, требуется аутентификация через Telegram
        console.log('Пользователь не найден, требуется аутентификация через Telegram. Запрашиваем код.');
        // Переводим сообщение на выбранный язык
        if (response.data.message === "User not found. Please complete Telegram authentication to register.") {
          error.value = $t('new_user_telegram_auth_required');
        } else {
          error.value = response.data.message;
        }
        try {
          // Запрашиваем код у Telegram
          const requestCodeResponse = await axios.post('/auth/request_telegram_code', { phone: phoneNumber.value }, { withCredentials: true });
          console.log('Ответ от /auth/request_telegram_code:', requestCodeResponse.data);
          if (requestCodeResponse.data.phone_code_hash && requestCodeResponse.data.code_sent_time) {
            phoneCodeHash.value = requestCodeResponse.data.phone_code_hash;
            codeSentTime.value = requestCodeResponse.data.code_sent_time; // Сохраняем время отправки кода
            codeSent.value = true; // Показываем поле для ввода кода
            console.log('phone_code_hash получен и сохранен:', phoneCodeHash.value);
            console.log('code_sent_time получен и сохранен:', codeSentTime.value);
          } else {
            throw new Error('phone_code_hash not received from server');
          }
        } catch (requestCodeError: any) {
          console.error('Ошибка при запросе кода Telegram:', requestCodeError);
          error.value = requestCodeError.response?.data?.detail || $t('failed_to_request_telegram_code');
        }
      } else if (response.data.status === 'telegram_auth_required') {
        // Существующий пользователь, требуется аутентификация через Telegram
        console.log('Существующий пользователь, требуется аутентификация через Telegram. Запрашиваем код.');
        // Переводим сообщение на выбранный язык
        if (response.data.message === "Please complete Telegram authentication to access your account.") {
          error.value = $t('telegram_auth_required');
        } else {
          error.value = response.data.message;
        }
        try {
          const requestCodeResponse = await axios.post('/auth/request_telegram_code', { phone: phoneNumber.value }, { withCredentials: true });
          if (requestCodeResponse.data.phone_code_hash && requestCodeResponse.data.code_sent_time) {
            phoneCodeHash.value = requestCodeResponse.data.phone_code_hash;
            codeSentTime.value = requestCodeResponse.data.code_sent_time;
            codeSent.value = true;
          }
        } catch (requestCodeError: any) {
          error.value = requestCodeError.response?.data?.detail || $t('failed_to_request_telegram_code');
        }
      } else {
        // Другой непредвиденный ответ от /auth/login
        console.log('Непредвиденный ответ от /auth/login, запрашиваем код (старая логика)');
        // Эта ветка может быть удалена или изменена в зависимости от того, как /auth/login обрабатывает другие случаи
        const codeResponse = await axios.post('/auth/login', { phone: phoneNumber.value }, { withCredentials: true });
        console.log('Ответ на запрос кода (старая логика):', codeResponse.data);
        codeSent.value = true;
      }
    } catch (err: any) {
      console.error('Ошибка при проверке сессии:', err);
      
      // Обработка ошибок от /auth/login
      // Если /auth/login возвращает ошибку (например, 400, 500), она будет поймана здесь
      // Статус 401 от /auth/check больше не должен возникать, так как мы его не вызываем напрямую для этой логики
      if (err.response?.data?.status === 'new_user_telegram_auth_required') {
        // Этот случай уже должен обрабатываться в блоке try выше, но на всякий случай
        console.log('Пользователь не найден (обработка ошибки), требуется аутентификация через Telegram');
        // Переводим сообщение на выбранный язык
        if (err.response.data.message === "User not found. Please complete Telegram authentication to register.") {
          error.value = $t('new_user_telegram_auth_required');
        } else if (err.response.data.message === "Please complete Telegram authentication to access your account.") {
          error.value = $t('telegram_auth_required');
        } else {
          error.value = err.response.data.message;
        }
        codeSent.value = true; 
      } else {
        error.value = err.response?.data?.detail || $t('error_occurred_during_login');
      }
      console.error('Ошибка при вызове /auth/login:', err);
    } finally {
      loading.value = false;
      checkingSession.value = false;
    }
  } else {
    // --- Submit Code (and potentially password) ---
    console.log('Attempting to submit code:', code.value, 'Password provided:', !!password.value);
    try {
      // Более строгая проверка на null или undefined
      if (phoneCodeHash.value === null || phoneCodeHash.value === undefined || codeSentTime.value === null || codeSentTime.value === undefined) {
        console.error('Critical error: phoneCodeHash or codeSentTime is null/undefined before submitting code.');
        error.value = $t('session_error_critical_data_missing');
        loading.value = false;
        codeSent.value = false; // Сбросить, чтобы пользователь мог запросить код заново
        phoneNumber.value = ''; // Очистить номер телефона для нового ввода
        return;
      }
      
      // Проверка истечения кода
      if (isCodeExpired()) {
        console.error('Code has expired');
        error.value = $t('verification_code_expired');
        loading.value = false;
        codeSent.value = false; // Сбросить, чтобы пользователь мог запросить код заново
        phoneNumber.value = ''; // Очистить номер телефона для нового ввода
        return;
      }
      const payload: { phone: string; code: string; phone_code_hash: string; code_sent_time: string; password?: string } = {
         phone: phoneNumber.value,
         code: code.value,
         phone_code_hash: phoneCodeHash.value,
         code_sent_time: codeSentTime.value // Добавляем время отправки кода
      }
      if (password.value) { // Include password only if provided
         payload.password = password.value;
      }
      console.log('Submitting code with payload:', payload);
      const response = await axios.post('/auth/submit_code', payload, { withCredentials: true })
      console.log('Submit code response:', response.data);
      
      // Check if response indicates 2FA is required
      if (response.data?.status === 'password_required' || 
          (response.data?.message && typeof response.data.message === 'string' && 
           (response.data.message.toLowerCase().includes('two-factor') ||
            response.data.message.toLowerCase().includes('2fa') ||
            response.data.message.toLowerCase().includes('password required')))) {
        console.log('2FA password required, showing password field.');
        needsPassword.value = true;
        error.value = $t('two_factor_auth_password_required');
        loading.value = false;
        return;
      }
      
      // Check if response indicates client is already connected (successful login after 2FA)
      if (response.data?.message && typeof response.data.message === 'string' && 
          response.data.message.toLowerCase().includes('client is already connected')) {
        if (password.value) {
          console.log('Client already connected after 2FA - login successful!');
          await checkAndShowSuccessModal(); // Check newcomer status before showing modal
          return;
        } else {
          console.log('Client already connected, showing 2FA password field.');
          needsPassword.value = true;
          error.value = $t('two_factor_auth_password_required');
          loading.value = false;
          return;
        }
      }
      
      // If we get here and have a password, it means 2FA was successful
      if (password.value) {
        console.log('2FA successful, proceeding to dashboard');
        await checkAndShowSuccessModal();
        return;
      }
      
      // Store the access token in localStorage for API interceptor
      if (response.data.access_token) {
        localStorage.setItem('auth_token', response.data.access_token);
        console.log('🔍 Stored access token in localStorage for API interceptor');
      }

      // Check if user is a newcomer before showing success modal
      await checkAndShowSuccessModal();
    } catch (err: any) {
      console.error('Error submitting code:', err);
      console.log('Error response status:', err.response?.status);
      console.log('Error response data:', err.response?.data);
      
      // Enhanced 2FA detection - check multiple possible error formats
      const checkFor2FA = (data: any): boolean => {
        if (!data) return false;
        
        // Check direct message property
        if (typeof data === 'string' && 
            (data.includes('Two-factor authentication password required') ||
             data.includes('2FA') ||
             data.includes('password required') ||
             data.includes('provide your 2FA password'))) {
          return true;
        }
        
        // Check detail property
        if (data.detail && typeof data.detail === 'string' && 
            (data.detail.includes('Two-factor authentication password required') ||
             data.detail.includes('2FA') ||
             data.detail.includes('password required') ||
             data.detail.includes('provide your 2FA password'))) {
          return true;
        }
        
        // Check message property
        if (data.message && typeof data.message === 'string' && 
            (data.message.includes('Two-factor authentication password required') ||
             data.message.includes('2FA') ||
             data.message.includes('password required') ||
             data.message.includes('provide your 2FA password'))) {
          return true;
        }
        
        return false;
      };
      
      // Check if this is a 2FA requirement error
      const is2FARequired = checkFor2FA(err.response?.data?.detail) || 
                           checkFor2FA(err.response?.data?.message) || 
                           checkFor2FA(err.response?.data) ||
                           (err.response?.status === 401 && err.response?.data?.detail === 'Two-factor authentication password required. Please provide your 2FA password.');
      
      if (is2FARequired) {
        console.log('2FA password required, showing password field.');
        needsPassword.value = true;
        error.value = $t('two_factor_auth_password_required');
        loading.value = false;
        return;
      }
      
      // Handle "Client is already connected" error
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.response?.data || '';
      if (err.response?.status === 503 && 
          (typeof errorMessage === 'string' && errorMessage.includes('Client is already connected'))) {
        // If we already provided a password and got "Client is already connected", it means successful login
        if (password.value) {
          console.log('Client already connected after 2FA - login successful!');
          await checkAndShowSuccessModal(); // Check newcomer status before showing modal
          return;
        } else {
          console.log('Client already connected (503 error), showing 2FA password field.');
          needsPassword.value = true;
          error.value = $t('two_factor_auth_password_required');
          loading.value = false;
          return;
        }
      }
      
      // Handle other errors
      const displayError = typeof errorMessage === 'string' ? errorMessage : 
                         (errorMessage.detail || errorMessage.message || JSON.stringify(errorMessage));
      error.value = displayError || $t('failed_to_submit_code');
    } finally {
      loading.value = false;
    }
  }
};

const isCodeExpired = () => {
  if (!codeSentTime.value) return false;
  const now = new Date().getTime();
  const sentTime = new Date(codeSentTime.value).getTime();
  // Telegram code typically expires in 2-5 minutes. Let's use 5 minutes (300 seconds).
  return (now - sentTime) / 1000 > 300; 
};

const checkAndShowSuccessModal = async () => {
  try {
    // Check if user is a newcomer
    const response = await axios.get('/auth/newcomer-status', { withCredentials: true });
    const { is_newcomer } = response.data;
    
    console.log('Newcomer status:', is_newcomer);
    
    if (is_newcomer) {
      // Show success modal only for newcomers
      showSuccessModal.value = true;
    } else {
      // For experienced users, go directly to dashboard
      emit('login');
    }
  } catch (error) {
    console.error('Error checking newcomer status:', error);
    // In case of error, don't show modal and go to dashboard
    emit('login');
  }
};

const closeSuccessModal = () => {
  showSuccessModal.value = false;
  emit('login'); // Proceed to dashboard after closing modal
};

const handleImageError = (event: Event) => {
  // Hide the image container if image fails to load
  const img = event.target as HTMLImageElement;
  if (img.parentElement) {
    img.parentElement.style.display = 'none';
  }
};

const formatTelegramInfo = (text: string): string => {
  // Convert \n to <br> tags and preserve formatting
  return text.replace(/\n/g, '<br>');
};
</script>

<style scoped>
.login-form {
  max-width: 400px;
  margin: 50px auto;
  padding: 30px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
}

/* Dark theme background with gradient */
.tma-environment .login-form {
  background: linear-gradient(135deg,
    #2a2a2a 0%,
    #3a2a4a 25%,
    #4a3a2a 50%,
    #3a2a4a 75%,
    #2a2a2a 100%);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.tma-auth-loading {
  text-align: center;
  padding: 40px 20px;
}

.tma-auth-loading .loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(0, 136, 204, 0.3);
  border-top: 3px solid #0088cc;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.tma-auth-loading p {
  color: #0088cc;
  font-size: 16px;
  margin: 0;
}

.language-selector {
  margin-bottom: 20px;
  text-align: center;
}

.language-selector label {
  display: block;
  margin-bottom: 5px;
  font-weight: 600;
  color: #333;
}

.language-selector select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

h2 {
  text-align: center;
  color: #333;
  margin-bottom: 25px;
  font-size: 24px;
}

form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

label {
  font-weight: 600;
  color: #333;
  margin-bottom: 5px;
}

input {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.2s;
}

input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

button {
  padding: 12px 20px;
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: white;
  border: 3px solid #ffffff;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  min-height: 48px;
  box-shadow: 0 0 30px rgba(34, 197, 94, 0.6), 0 0 60px rgba(34, 197, 94, 0.3);
  position: relative;
}

button:hover:not(:disabled) {
  background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
  box-shadow: 0 0 40px rgba(34, 197, 94, 0.8), 0 0 80px rgba(34, 197, 94, 0.4);
  transform: translateY(-2px);
}

button:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.info {
  color: #666;
  font-size: 14px;
  margin: 5px 0 15px 0;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #007bff;
  text-align: left;
}

.error {
  color: #dc3545;
  background: #f8d7da;
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #f5c6cb;
  margin: 10px 0;
  font-size: 14px;
  line-height: 1.4;
}

/* TMA specific styles */
.tma-environment .language-selector {
  display: block !important;
  visibility: visible !important;
  opacity: 1 !important;
}

/* Mobile optimizations */
@media (max-width: 768px) {
  .login-form {
    margin: 20px;
    padding: 20px;
    max-width: calc(100vw - 40px);
    border-radius: 8px;
  }

  h2 {
    font-size: 20px;
    margin-bottom: 20px;
  }

  input, button {
    font-size: 16px; /* Prevent zoom on iOS */
    padding: 14px;
    min-height: 48px; /* Touch-friendly */
  }

  .language-selector select {
    font-size: 16px;
    padding: 10px 12px;
    min-height: 44px;
  }

  form {
    gap: 12px;
  }

  .error {
    font-size: 13px;
    padding: 8px;
    word-break: break-word;
  }
}

/* Small mobile devices */
@media (max-width: 480px) {
  .login-form {
    margin: 10px;
    padding: 15px;
    max-width: calc(100vw - 20px);
  }
  
  h2 {
    font-size: 18px;
  }
  
  input, button {
    padding: 12px;
    font-size: 16px;
  }
}

/* Loading state */
.loading {
  text-align: center;
  color: #666;
  font-style: italic;
}

/* Form transitions */
form > div {
  animation: fadeIn 0.3s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Success Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  z-index: 1000;
  animation: fadeIn 0.3s ease-out;
  overflow-y: auto;
  padding: 20px 0;
  box-sizing: border-box;
}

.modal-content {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 90vw;
  max-height: calc(100vh - 40px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease-out;
  margin: auto 0;
}

.success-modal {
  width: 600px;
  max-width: 90vw;
}

.modal-header {
  padding: 15px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.modal-header h3 {
  margin: 0;
  color: #28a745;
  font-size: 20px;
}

.modal-close {
  background: none;
  border: none;
  font-size: 28px;
  cursor: pointer;
  color: #999;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #f5f5f5;
  color: #333;
}

.modal-body {
  padding: 20px;
  line-height: 1.5;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.intro-text {
  font-size: 16px;
  margin-bottom: 20px;
  color: #333;
}

.telegram-image-container {
  text-align: center;
  margin: 20px 0;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px dashed #dee2e6;
}

.telegram-notification-image {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.explanation-text {
  font-size: 16px;
  margin: 20px 0;
  color: #333;
}

.purpose-list {
  margin: 15px 0;
  padding-left: 20px;
}

.purpose-list li {
  margin: 8px 0;
  color: #555;
}

.action-text {
  font-size: 16px;
  margin: 20px 0;
  color: #28a745;
  background: #d4edda;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #28a745;
}

.security-text {
  font-size: 14px;
  margin: 20px 0;
  color: #6c757d;
  background: #f8f9fa;
  padding: 15px;
  border-radius: 6px;
  border-left: 4px solid #6c757d;
}

.modal-footer {
  padding: 15px 20px;
  border-top: 1px solid #eee;
  text-align: center;
  flex-shrink: 0;
}

.modal-button {
  padding: 12px 30px;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  min-width: 120px;
}

.modal-button.primary {
  background: #28a745;
  color: white;
}

.modal-button.primary:hover {
  background: #218838;
  transform: translateY(-1px);
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-50px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Mobile optimizations for modal */
@media (max-width: 768px) {
  .modal-overlay {
    padding: 10px;
    align-items: flex-start;
    padding-top: 10px;
    overflow-y: auto;
  }
  
  .success-modal {
    width: 95vw;
    max-height: calc(100vh - 20px);
    margin: 0;
    display: flex;
    flex-direction: column;
  }
  
  .modal-header {
    padding: 12px 15px;
    flex-shrink: 0;
  }
  
  .modal-header h3 {
    font-size: 18px;
  }
  
  .modal-body {
    padding: 15px;
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }
  
  .intro-text, .explanation-text {
    font-size: 14px;
    margin: 10px 0;
  }
  
  .action-text {
    font-size: 14px;
    padding: 10px;
    margin: 10px 0;
  }
  
  .security-text {
    font-size: 13px;
    padding: 10px;
    margin: 10px 0;
  }
  
  .modal-footer {
    padding: 15px 20px;
    flex-shrink: 0;
  }
  
  .modal-button {
    padding: 12px 20px;
    font-size: 14px;
    width: 100%;
  }
  
  .telegram-image-container {
    margin: 15px 0;
    padding: 10px;
  }
  
  .purpose-list {
    margin: 10px 0;
    padding-left: 15px;
  }
  
  .purpose-list li {
    margin: 6px 0;
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .modal-overlay {
    padding: 5px;
    padding-top: 5px;
    overflow-y: auto;
  }
  
  .success-modal {
    width: calc(100vw - 10px);
    max-height: calc(100vh - 10px);
    display: flex;
    flex-direction: column;
  }
  
  .modal-header {
    padding: 10px 12px;
    flex-shrink: 0;
  }
  
  .modal-header h3 {
    font-size: 16px;
  }
  
  .modal-body {
    padding: 12px;
    flex: 1;
    overflow-y: auto;
    min-height: 0;
  }
  
  .telegram-image-container {
    padding: 8px;
    margin: 10px 0;
  }
  
  .intro-text, .explanation-text {
    font-size: 13px;
    margin: 8px 0;
  }
  
  .action-text {
    font-size: 13px;
    padding: 8px;
    margin: 8px 0;
  }
  
  .security-text {
    font-size: 12px;
    padding: 8px;
    margin: 8px 0;
  }
  
  .modal-footer {
    padding: 12px 15px;
    flex-shrink: 0;
  }
  
  .modal-button {
    padding: 14px 20px;
    font-size: 16px;
    min-height: 48px;
  }
}

/* Extra small screens */
@media (max-width: 360px) {
  .modal-overlay {
    padding: 2px;
    padding-top: 2px;
    overflow-y: auto;
  }
  
  .success-modal {
    width: calc(100vw - 4px);
    max-height: calc(100vh - 4px);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
  }
  
  .modal-header {
    padding: 10px 12px;
  }
  
  .modal-header h3 {
    font-size: 16px;
  }
  
  .modal-body {
    padding: 12px;
    max-height: calc(100vh - 120px);
  }
  
  .telegram-image-container {
    padding: 6px;
    margin: 8px 0;
  }
  
  .intro-text, .explanation-text {
    font-size: 12px;
    margin: 12px 0;
  }
  
  .action-text {
    font-size: 12px;
    padding: 8px;
    margin: 12px 0;
  }
  
  .security-text {
    font-size: 11px;
    padding: 8px;
    margin: 12px 0;
  }
  
  .purpose-list {
    margin: 8px 0;
    padding-left: 12px;
  }
  
  .purpose-list li {
    margin: 4px 0;
    font-size: 12px;
  }
  
  .modal-footer {
    padding: 10px 12px;
  }
}
</style>

<style scoped>
/* Telegram Success Modal (new styles matching template classes) */
.telegram-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.telegram-modal {
  width: 560px;
  max-width: 92vw;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.25s ease-out;
}

.telegram-modal-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid #f0f0f0;
}

.telegram-modal-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #e8f4fd;
  display: grid;
  place-items: center;
  flex: 0 0 auto;
}

.telegram-modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #1f2d3d;
}

.telegram-modal-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: #9aa5b1;
  font-size: 28px;
  line-height: 1;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, transform 0.1s ease;
}

.telegram-modal-close:hover {
  background: #f3f4f6;
  color: #111827;
  transform: translateY(-1px);
}

.telegram-modal-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.telegram-status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #059669; /* emerald-600 */
  background: #ecfdf5; /* emerald-50 */
  border: 1px solid #a7f3d0; /* emerald-200 */
  padding: 8px 10px;
  border-radius: 9999px;
  width: fit-content;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af; /* default gray */
}

.status-dot.connected {
  background: #10b981; /* emerald-500 */
}

.telegram-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.telegram-description {
  margin: 6px 0 4px;
  color: #374151;
  line-height: 1.5;
}

.telegram-features {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.telegram-features .feature-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  color: #1f2937;
}

.feature-check {
  color: #10b981;
  font-weight: 700;
}

.telegram-modal-footer {
  padding: 14px 16px;
  border-top: 1px solid #f0f0f0;
  display: flex;
  justify-content: flex-end;
}

.telegram-btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  border: none;
  padding: 12px 18px;
  border-radius: 10px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.1s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  box-shadow: 0 8px 20px rgba(118, 75, 162, 0.25);
}

.telegram-btn-primary:hover {
  opacity: 0.95;
  transform: translateY(-1px);
}

/* Mobile adjustments */
@media (max-width: 768px) {
  .telegram-modal {
    width: 96vw;
  }

  .telegram-modal-header h3 {
    font-size: 16px;
  }

  .telegram-modal-body {
    padding: 14px;
    gap: 12px;
  }

  .telegram-features .feature-item {
    padding: 10px;
  }
}

@media (max-width: 480px) {
  .telegram-modal-header {
    padding: 12px 14px;
    gap: 10px;
  }
  .telegram-modal-icon {
    width: 40px;
    height: 40px;
    border-radius: 10px;
  }
  .telegram-modal-header h3 {
    font-size: 15px;
  }
  .telegram-modal-body {
    padding: 12px;
  }
  .telegram-btn-primary {
    width: 100%;
  }
}
</style>
