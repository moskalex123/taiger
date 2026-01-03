<template>
  <div class="redesigned-header">
    <!-- Background banner image -->
    <img src="/taiger-banner.png" alt="Taiger Banner" class="header-background" />
    
    <!-- Первая строка: Статус сервиса (слева) + Название сервиса (центр) + Язык (справа) -->
    <div class="header-first-row">
      <!-- Статус сервиса - слева -->
      <div class="service-status-left">
        <div class="status-icon" :class="serviceStatusClass">{{ statusIcon }}</div>
        <span class="status-value" :class="serviceStatusClass">{{ serviceStatusDisplay }}</span>
      </div>
      
      <!-- Название сервиса - центр -->
      <div class="service-name-center">
        <span class="service-title">taiger<span class="version-tag">v{{ appVersion }}</span></span>
      </div>
      
      <!-- Селектор языка - справа -->
      <div class="language-selector-right">
        <div class="custom-language-select" @click="toggleLanguageDropdown">
          <div class="selected-language">
            <span v-if="currentLanguage === 'ru'">🇷🇺 RU</span>
            <span v-else>🇺🇸 EN</span>
            <svg class="dropdown-arrow" :class="{ 'open': showLanguageDropdown }" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <polyline points="6,9 12,15 18,9"></polyline>
            </svg>
          </div>
          <div v-if="showLanguageDropdown" class="language-dropdown">
            <div 
              class="language-option" 
              :class="{ active: currentLanguage === 'ru' }"
              @click.stop="selectLanguage('ru')"
            >
              🇷🇺 RU
            </div>
            <div 
              class="language-option" 
              :class="{ active: currentLanguage === 'en' }"
              @click.stop="selectLanguage('en')"
            >
              🇺🇸 EN
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Вторая строка: Активные воркеры + В очереди (все слева) -->
    <div class="header-second-row">
      <div class="workers-and-queue-line">
        <span class="active-label">{{ $t('active_agents_label') }}</span>:
        <span v-if="activeWorkers.length === 0" class="no-workers">0</span>
        <span v-else class="worker-list">
          <span 
            v-for="worker in activeWorkers" 
            :key="worker"
            :class="['worker-badge', 'active', { 'current-user': worker === currentUserId }]"
            :style="getWorkerStyle(worker)">
            {{ worker }}
          </span>
        </span>
        
        <span class="queue-separator">•</span>
        
        <span class="queue-label">{{ $t('in_queue_label') }}</span>:
        <span v-if="queuedWorkers.length === 0" class="no-workers">0</span>
        <span v-else class="worker-list">
          <span 
            v-for="worker in queuedWorkers" 
            :key="worker"
            :class="['worker-badge', 'queue', { 'current-user': worker === currentUserId }]"
            :style="getWorkerStyle(worker)">
            {{ worker }}
          </span>
        </span>
      </div>
    </div>
    

  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Cookies from 'js-cookie'
import axios from 'axios'
import { useVipStyles } from '../composables/useVipStyles'
import { LanguageService } from '../services/language'
const appVersion = (import.meta.env as any).VITE_APP_VERSION || '5'

// Импортируем изображение для надежности
const bannerImage = '/taiger-banner.png'

const { t: $t, locale } = useI18n()
const vipStyles = useVipStyles()

// Real service status data (like in ServiceHeader.vue)
interface ServiceStatusData {
  service_state: string
  active_workers: number[]
  starting_workers: number[]
  queue: number[]
  worker_vips: { [key: number]: number }
  usernames: { [key: number]: string }
  worker_newcomers: { [key: number]: boolean }
}

const serviceState = ref('offline')
const activeWorkers = ref<number[]>([])
const startingWorkers = ref<number[]>([])
const queuedWorkers = ref<number[]>([])
const workerVips = ref<{ [key: number]: number }>({})
const usernames = ref<{ [key: number]: string }>({})
const workerNewcomers = ref<{ [key: number]: boolean }>({})

// Get current user ID for highlighting
const currentUserId = inject<number>('currentUserId', 0)

// Worker functions (copied from ServiceHeader.vue)
const getWorkerVip = (workerId: number): number => {
  return workerVips.value[workerId] || 0
}

const isWorkerNewcomer = (workerId: number): boolean => {
  return workerNewcomers.value[workerId] || false
}

const getWorkerStyle = (workerId: number) => {
  const isNewcomer = isWorkerNewcomer(workerId)
  if (isNewcomer) {
    return {
      background: 'linear-gradient(135deg, #FFD700, #FFA500)',
      color: '#000',
      fontWeight: 'bold',
      border: '2px solid #FFD700',
      boxShadow: '0 0 10px rgba(255, 215, 0, 0.5)'
    }
  }
  return vipStyles.getVipStyle(getWorkerVip(workerId))
}

const fetchServiceStatus = async () => {
  try {
    const response = await axios.get<ServiceStatusData>('/api/queue/service-status', { withCredentials: true })
    const data = response.data
    
    serviceState.value = data.service_state || 'offline'
    activeWorkers.value = data.active_workers || []
    startingWorkers.value = data.starting_workers || []
    queuedWorkers.value = data.queue || []
    workerVips.value = data.worker_vips || {}
    usernames.value = data.usernames || {}
    workerNewcomers.value = data.worker_newcomers || {}
  } catch (error) {
    console.error('Failed to fetch service status:', error)
    serviceState.value = 'offline'
    activeWorkers.value = []
    startingWorkers.value = []
    queuedWorkers.value = []
    workerVips.value = {}
    usernames.value = {}
    workerNewcomers.value = {}
  }
}

// Language functionality
const languageService = LanguageService.getInstance()
const showLanguageDropdown = ref(false)
const currentLanguage = ref(locale.value)

const toggleLanguageDropdown = () => {
  showLanguageDropdown.value = !showLanguageDropdown.value
}

const selectLanguage = async (lang: string) => {
  try {
    await languageService.setUserLanguage(lang)
    currentLanguage.value = lang
    locale.value = lang
    Cookies.set('language', lang, { expires: 365 })
    showLanguageDropdown.value = false
  } catch (error) {
    console.error('Failed to change language:', error)
  }
}

// Close dropdown when clicking outside
const handleClickOutside = (event: Event) => {
  const target = event.target as Element
  if (!target.closest('.custom-language-select')) {
    showLanguageDropdown.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  // Get language from backend
  try {
    const userLanguage = await languageService.getUserLanguage()
    currentLanguage.value = userLanguage
    locale.value = userLanguage
    Cookies.set('language', userLanguage, { expires: 365 })
  } catch (error) {
    console.error('Failed to get user language:', error)
    // Fallback to cookie or default
    const savedLanguage = Cookies.get('language') || 'en'
    currentLanguage.value = savedLanguage
    locale.value = savedLanguage
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

// Service status computed properties
const serviceStatusClass = computed(() => {
  const status = serviceState.value
  switch (status) {
    case 'online': return 'status-online'
    case 'maintenance': return 'status-maintenance'
    case 'offline': return 'status-offline'
    default: return 'status-unknown'
  }
})

const serviceStatusDisplay = computed(() => {
  const status = serviceState.value
  switch (status) {
    case 'online': return $t('online') || 'Online'
    case 'maintenance': return $t('maintenance') || 'Maintenance'
    case 'offline': return $t('offline') || 'Offline'
    default: return $t('unknown') || 'Unknown'
  }
})

const statusIcon = computed(() => {
  const status = serviceState.value
  switch (status) {
    case 'online': return '🟢'
    case 'maintenance': return '🟡'
    case 'offline': return '🔴'
    default: return '⚪'
  }
})

// Lifecycle hooks
let refreshInterval: number | null = null

onMounted(() => {
  fetchServiceStatus()
  // Refresh every 2 seconds
  refreshInterval = setInterval(fetchServiceStatus, 2000)
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.redesigned-header {
  background-image: url('/taiger-banner.png');
  background-size: cover; /* Покрывает всю ширину */
  background-repeat: no-repeat;
  background-position: center center; /* По центру */
  background-color: var(--bg-primary, #f8f9fa);
  border-bottom: 1px solid var(--bg-secondary);
  padding: 8px 12px; /* Убираем отступ слева */
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: var(--shadow-sm);
  min-height: 60px;
  /* Добавляем полупрозрачный оверлей для читаемости текста */
  position: relative;
}

/* Полупрозрачный оверлей поверх фонового изображения */
.redesigned-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3); /* Темный оверлей для читаемости */
  z-index: 1;
}

.header-background {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 0;
}

.header-first-row,
.header-second-row {
  position: relative;
  z-index: 2;
}

/* Первая строка: Статус + Название + Язык */
.header-first-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 24px;
  margin-bottom: 4px;
  width: 100%;
}

.service-status-left {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  justify-self: flex-start;
}

.service-name-center {
  flex: 1;
  text-align: center;
  display: flex;
  justify-content: center;
}

.service-title {
  font-size: 16px;
  font-weight: bold;
  color: #ffffff; /* Белый текст для контраста с фоном */
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8); /* Тень для читаемости */
}

.version-tag {
  font-size: 12px;
  background-color: #ff6b35;
  color: white;
  padding: 2px 6px;
  border-radius: 12px;
  margin-left: 8px;
  vertical-align: middle;
  font-weight: bold;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.language-selector-right {
  flex: 0 0 auto;
  justify-self: flex-end;
}

/* Вторая строка: Воркеры и очередь */
.header-second-row {
  display: flex;
  justify-content: flex-start;
  font-size: 12px;
}

.workers-and-queue-line {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #ffffff !important; /* Белый текст с !important */
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important; /* Усиленная тень для читаемости */
  font-weight: 700 !important; /* Жирный шрифт для лучшей видимости */
}
.redesigned-header .workers-and-queue-line,
.redesigned-header .workers-and-queue-line * {
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important;
  font-weight: 700 !important;
}

.workers-and-queue-line .worker-list {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 2px;
}

.workers-and-queue-line .worker-badge {
  display: inline-block;
  padding: 1px 4px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  border: 1px solid transparent;
  white-space: nowrap;
  min-width: 16px;
  text-align: center;
  color: #000 !important; /* Черный текст для контраста */
  text-shadow: none !important; /* Убираем тень */
}

.workers-and-queue-line .worker-badge.current-user {
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.9);
}

.queue-separator {
  margin: 0 8px;
  color: var(--text-hint);
}

.active-label,
.queue-label {
  font-weight: 800 !important; /* Максимальная жирность */
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important; /* Максимальная тень */
}

/* Дополнительные селекторы для максимального приоритета */
.redesigned-header .active-label,
.redesigned-header .queue-label,
.header-second-row .active-label,
.header-second-row .queue-label {
  font-weight: 800 !important;
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important;
}

.worker-count,
.queue-count {
  font-weight: bold;
  color: #ffffff !important; /* Белый текст */
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important; /* Усиленная тень для читаемости */
}

.no-workers {
  color: var(--text-hint);
}

.starting-label {
  margin-left: 8px;
  color: var(--warning);
  font-weight: 500;
}

/* TMA стили для новой шапки */
.tma-environment .redesigned-header {
  background-image: url('/taiger-banner.png') !important;
  background-size: cover !important; /* Покрывает всю ширину в TMA */
  background-repeat: no-repeat !important;
  background-position: center center !important; /* По центру в TMA */
  background-color: var(--tg-theme-bg-color, #1a1a1a) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important;
  padding: 4px 6px !important; /* Убираем отступ слева в TMA */
}

/* TMA оверлей для читаемости */
.tma-environment .redesigned-header::before {
  background: rgba(0, 0, 0, 0.5) !important; /* Более темный оверлей для TMA */
}
</style>

.tma-environment .service-title {
  color: #ffffff !important;
  font-size: 14px !important;
}

.tma-environment .workers-and-queue-line {
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important; /* Еще более сильная тень для TMA */
  font-weight: 700 !important; /* Максимальная жирность для TMA */
}

.tma-environment .active-label,
.tma-environment .queue-label {
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important;
  font-weight: 800 !important; /* Максимальная жирность */
}

.tma-environment .workers-and-queue-line .worker-badge {
  color: #000 !important; /* Черный текст в TMA тоже */
  text-shadow: none !important;
}

.tma-environment .worker-count,
.tma-environment .queue-count {
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important;
  font-weight: 800 !important;
}

.tma-environment .starting-label {
  color: #ffa500 !important;
}

.banner-section {
  display: none;
}

.banner-logo {
  height: 28px;
  width: auto;
  object-fit: contain;
}

.service-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.service-name {
  font-size: var(--text-md);
  font-weight: var(--weight-bold);
  color: var(--primary);
  line-height: 1.1;
}

.service-subtitle {
  font-size: var(--text-xs);
  color: var(--text-secondary);
  line-height: 1.2;
}

.service-status {
  flex-shrink: 0;
}

.status-display {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.status-icon {
  font-size: 16px;
}

.status-text {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.status-label {
  font-size: var(--text-xs);
  color: var(--text-hint);
  line-height: 1;
}

.status-value {
  font-size: var(--text-sm);
  font-weight: var(--weight-bold); /* Увеличиваем жирность */
  line-height: 1.1;
  color: #ffffff !important; /* Белый текст */
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.9) !important; /* Усиленная тень для читаемости */
}

/* Status Colors */
.status-online {
  color: var(--success) !important;
}

.status-maintenance {
  color: var(--warning) !important;
}

.status-offline {
  color: var(--error) !important;
}

.status-unknown {
  color: var(--text-hint) !important;
}

/* Language Selector - positioned on the far right */
.language-selector-wrapper {
  flex-shrink: 0;
  margin-left: auto;
}

/* Separator */
.header-separator {
  height: 1px;
  background: var(--bg-secondary);
  margin: 0 calc(-1 * var(--space-md));
}

/* Worker Info Section */
.worker-info-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.info-row {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.info-icon {
  font-size: 14px;
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}

.info-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  flex: 1;
}

.info-value {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  flex-shrink: 0;
}

.active-count {
  color: var(--success);
}

.queue-count {
  color: var(--text-secondary);
}

.starting-count {
  color: var(--warning);
}

/* Language Selector Styles */
.custom-language-select {
  position: relative;
  display: inline-block;
}

.selected-language {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border: 2px solid var(--primary);
  background-color: var(--primary);
  color: #ffffff;
  border-radius: var(--radius-sm);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: all 0.3s ease;
  min-width: 60px;
  justify-content: center;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.selected-language:hover {
  background-color: var(--primary-hover, #0056b3);
  border-color: var(--primary-hover, #0056b3);
  transform: translateY(-1px);
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.3);
}

.dropdown-arrow {
  width: 8px;
  height: 8px;
  transition: transform 0.2s ease;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.language-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  background: var(--bg-card);
  border: 1px solid var(--bg-secondary);
  border-radius: var(--radius-sm);
  z-index: 1000;
  margin-top: 2px;
  box-shadow: var(--shadow-md);
  min-width: 80px;
}

.language-option {
  padding: 6px 8px;
  color: var(--text-primary);
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: var(--text-xs);
  white-space: nowrap;
}

.language-option:hover {
  background-color: var(--bg-secondary);
}

/* Worker Badge Styles (copied from ServiceHeader.vue) */
.worker-list {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
}

.worker-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 500;
  border: 1px solid transparent;
  white-space: nowrap;
  position: relative;
}

.worker-badge.active {
  background-color: rgba(76, 175, 80, 0.2);
  border-color: rgba(76, 175, 80, 0.5);
  color: #4CAF50;
}

.worker-badge.starting {
  background-color: rgba(255, 193, 7, 0.2);
  border-color: rgba(255, 193, 7, 0.5);
  color: #FFC107;
}

.worker-badge.queue {
  background-color: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
  color: var(--text-secondary);
}

.worker-badge.current-user {
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 0 0 20px rgba(255, 255, 255, 0.6), 0 0 30px rgba(255, 255, 255, 0.4);
  border: 2px solid rgba(255, 255, 255, 0.9);
  animation: pulse 2s infinite;
}

.newcomer-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  font-size: 8px;
  z-index: 1;
}

.no-workers {
  color: var(--text-hint);
  font-size: 10px;
}

@keyframes pulse {
  0%, 100% {
    box-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 0 0 20px rgba(255, 255, 255, 0.6), 0 0 30px rgba(255, 255, 255, 0.4);
  }
  50% {
    box-shadow: 0 0 15px rgba(255, 255, 255, 1), 0 0 25px rgba(255, 255, 255, 0.8), 0 0 35px rgba(255, 255, 255, 0.6);
  }
}

.language-option.active {
  background-color: var(--primary);
  color: var(--text-white);
  font-weight: var(--weight-medium);
}

.language-option:first-child {
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.language-option:last-child {
  border-radius: 0 0 var(--radius-sm) var(--radius-sm);
}

/* TMA Dark Theme Support */
.tma-environment.tma-dark-theme .redesigned-header {
  /* Сохраняем фоновое изображение, только меняем border */
  border-bottom-color: rgba(255, 255, 255, 0.2);
}

.tma-environment.tma-dark-theme .workers-and-queue-line {
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important;
  font-weight: 700 !important;
}

.tma-environment.tma-dark-theme .active-label,
.tma-environment.tma-dark-theme .queue-label {
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important;
  font-weight: 800 !important;
}

.tma-environment.tma-dark-theme .worker-count,
.tma-environment.tma-dark-theme .queue-count {
  color: #ffffff !important;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.95) !important;
  font-weight: 800 !important;
}

.tma-environment.tma-dark-theme .header-separator {
  background: #404040;
}

.tma-environment.tma-dark-theme .selected-language {
  background-color: #3d3d3d;
  border-color: #555555;
  color: #ffffff;
}

.tma-environment.tma-dark-theme .selected-language:hover {
  background-color: #4d4d4d;
}

.tma-environment.tma-dark-theme .language-dropdown {
  background: #3d3d3d;
  border-color: #555555;
}

.tma-environment.tma-dark-theme .language-option {
  color: #ffffff;
}

.tma-environment.tma-dark-theme .language-option:hover {
  background-color: #4d4d4d;
}

/* TMA Specific Optimizations */
.tma-environment .redesigned-header {
  padding: 4px 6px !important;
  gap: 3px !important;
  /* НЕ переопределяем background - оставляем фоновое изображение */
}

.tma-environment .header-top-row {
  min-height: 20px !important;
  gap: 3px !important;
}

.tma-environment .banner-logo {
  height: 18px !important;
}

.tma-environment .service-name {
  font-size: 12px !important;
}

.tma-environment .service-subtitle {
  font-size: 8px !important;
}

.tma-environment .status-icon {
  font-size: 12px !important;
}

.tma-environment .status-label {
  font-size: 8px !important;
}

.tma-environment .status-value {
  font-size: 9px !important;
}

.tma-environment .info-row {
  gap: 2px !important;
}

.tma-environment .info-icon {
  font-size: 10px !important;
  width: 12px !important;
}

.tma-environment .info-label {
  font-size: 9px !important;
}

.tma-environment .info-value {
  font-size: 9px !important;
}

/* Enhanced TMA Language Selector Visibility */
.tma-environment .selected-language {
  padding: 4px 8px !important;
  font-size: 12px !important;
  min-width: 45px !important;
  background-color: #007bff !important;
  border: 2px solid #007bff !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3) !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.3) !important;
}

.tma-environment .selected-language:hover {
  background-color: #0056b3 !important;
  border-color: #0056b3 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.4) !important;
}

.tma-environment .dropdown-arrow {
  width: 10px !important;
  height: 10px !important;
  filter: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.3)) !important;
  stroke: #ffffff !important;
}

.tma-environment.tma-dark-theme .selected-language {
  background-color: #17a2b8 !important;
  border-color: #17a2b8 !important;
  color: #ffffff !important;
}

.tma-environment.tma-dark-theme .selected-language:hover {
  background-color: #138496 !important;
  border-color: #138496 !important;
}

/* Responsive adjustments for very small screens */
@media (max-width: 320px) {
  .redesigned-header {
    padding: var(--space-xs) var(--space-sm);
  }
  
  .banner-logo {
    height: 24px;
  }
  
  .service-name {
    font-size: var(--text-sm);
  }
  
  .service-subtitle {
    font-size: 10px;
  }
  
  .info-icon {
    font-size: 12px;
  }
  
  .info-label {
    font-size: 11px;
  }
  
  .info-value {
    font-size: 11px;
  }
}

.version-tag {
  font-size: 12px;
  background-color: #ff6b35;
  color: white;
  padding: 2px 6px;
  border-radius: 12px;
  margin-left: 8px;
  vertical-align: middle;
  font-weight: bold;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}
