<template>
  <div class="service-header">
    <!-- 1. Logo section (first) -->
    <div class="logo-section">
      <img src="/taiger-banner.png" alt="Taiger Banner" class="service-logo" />
    </div>
    
    <!-- 2. Title and Navigation section (second) -->
    <div class="title-navigation-section">
      <div class="title-with-language">
        <h1 class="service-title">
          <span class="letter-t">t</span><span class="letter-ai">AI</span><span class="letter-g">g</span><span class="letter-e">e</span><span class="letter-r">r</span>
          <span class="version-tag">v{{ appVersion }}</span>
        </h1>
        <!-- Language selector next to title -->
        <div class="language-selector">
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
        <!-- Design selector next to language -->
        <div class="design-selector">
          <div class="custom-design-select" @click="toggleDesignDropdown">
            <div class="selected-design">
              <span v-if="currentDesign === 'new'">🆕 New</span>
              <span v-else>👴 Old</span>
              <svg class="dropdown-arrow" :class="{ 'open': showDesignDropdown }" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polyline points="6,9 12,15 18,9"></polyline>
              </svg>
            </div>
            <div v-if="showDesignDropdown" class="design-dropdown">
              <div 
                class="design-option" 
                :class="{ active: currentDesign === 'old' }"
                @click.stop="selectDesign('old')"
              >
                👴 Old Design
              </div>
              <div 
                class="design-option" 
                :class="{ active: currentDesign === 'new' }"
                @click.stop="selectDesign('new')"
              >
                🆕 New Design
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="navigation-buttons">
        <button 
          @click="$emit('navigate', 'dashboard')" 
          :class="{ active: currentPage === 'dashboard' }"
          class="nav-button">
          {{ $t('dashboard') }}
        </button>
        <button 
          @click="$emit('navigate', 'info')" 
          :class="{ active: currentPage === 'info' }"
          class="nav-button">
          {{ $t('info') }}
        </button>
      </div>
    </div>
    
    <!-- 3. Status section (third) -->
    <div class="status-section">
      <div class="status-line">{{ $t('state_of_service') }}: {{ serviceState }}</div>
      <div class="status-line">
        <span class="active-label">{{ $t('active_workers') }}</span>: 
        <span v-if="activeWorkers.length === 0" class="no-workers">{{ $t('no_workers') }}</span>
        <span v-else class="worker-list">
          <span 
            v-for="worker in activeWorkers" 
            :key="worker"
            :class="['worker-badge', 'active', { 'current-user': worker === currentUserId }]"
            :style="getWorkerStyle(worker)">
            <span v-if="workerNewcomers[worker]" class="newcomer-badge">🌟</span>
            {{ getWorkerDisplayName(worker) }}
          </span>
        </span>
        <span v-if="startingWorkers.length > 0" class="starting-label">
          {{ $t('starting') }}: 
          <span class="worker-list">
            <span 
              v-for="worker in startingWorkers" 
              :key="worker"
              :class="['worker-badge', 'starting', { 'current-user': worker === currentUserId }]"
              :style="getWorkerStyle(worker)">
              <span v-if="workerNewcomers[worker]" class="newcomer-badge">🌟</span>
              {{ getWorkerDisplayName(worker) }}
            </span>
          </span>
        </span>
        <span v-if="processingWorkers.length > 0" class="processing-label">
          {{ $t('processing') }}: 
          <span class="worker-list">
            <span 
              v-for="worker in processingWorkers" 
              :key="worker"
              :class="['worker-badge', 'processing', { 'current-user': worker === currentUserId }]"
              :style="getWorkerStyle(worker)">
              <span v-if="workerNewcomers[worker]" class="newcomer-badge">🌟</span>
              {{ getWorkerDisplayName(worker) }}
            </span>
          </span>
        </span>
      </div>
      <div v-if="queuedWorkers.length > 0" class="status-line">
        {{ $t('queue') }}: 
        <span class="worker-list">
          <span 
            v-for="worker in queuedWorkers" 
            :key="worker"
            :class="['worker-badge', 'queue', { 'current-user': worker === currentUserId }]"
            :style="getWorkerStyle(worker)">
            <span v-if="workerNewcomers[worker]" class="newcomer-badge">🌟</span>
            {{ getWorkerDisplayName(worker) }}
          </span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import Cookies from 'js-cookie';
import axios from 'axios';
import { useVipStyles } from '../composables/useVipStyles';
const appVersionParam = typeof window !== 'undefined' ? new URLSearchParams(window.location.search).get('v') : null;
const appVersion = appVersionParam || (import.meta.env as any).VITE_APP_VERSION || '5'

// Language switching
const { locale } = useI18n();
const currentLanguage = ref(locale.value);
const showLanguageDropdown = ref(false);

const changeLanguage = () => {
  locale.value = currentLanguage.value;
  Cookies.set('language', currentLanguage.value, { expires: 365 });
};

const toggleLanguageDropdown = () => {
  showLanguageDropdown.value = !showLanguageDropdown.value;
};

const selectLanguage = (lang: string) => {
  currentLanguage.value = lang;
  showLanguageDropdown.value = false;
  changeLanguage();
};

// Design switching
const currentDesign = ref(Cookies.get('design') || 'old');
const showDesignDropdown = ref(false);

const changeDesign = () => {
  Cookies.set('design', currentDesign.value, { expires: 365 });
  $emit('switch-design', currentDesign.value);
  // Optionally reload to apply new design
  // window.location.reload();
};

const toggleDesignDropdown = () => {
  showDesignDropdown.value = !showDesignDropdown.value;
};

const selectDesign = (design: string) => {
  currentDesign.value = design;
  showDesignDropdown.value = false;
  changeDesign();
};

// Close dropdown when clicking outside
const handleClickOutside = (event: Event) => {
  const target = event.target as HTMLElement;
  if (!target.closest('.language-selector')) {
    showLanguageDropdown.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
  // Listen for clicks outside design dropdown as well
  document.addEventListener('click', handleDesignClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
  document.removeEventListener('click', handleDesignClickOutside);
});

const handleDesignClickOutside = (event: Event) => {
  const target = event.target as HTMLElement;
  if (!target.closest('.design-selector')) {
    showDesignDropdown.value = false;
  }
};

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

interface ServiceStatusData {
  service_state: string;
  active_workers: number[];
  starting_workers: number[];
  processing_workers: number[];
  queue: number[];
  worker_vips?: { [key: number]: number };
  usernames?: { [key: number]: string };
  worker_newcomers?: { [key: number]: boolean };
}

// Props
interface Props {
  currentPage?: string;
  currentUserId?: number;
}

withDefaults(defineProps<Props>(), {
  currentPage: 'dashboard',
  currentUserId: undefined
});

// Emits
defineEmits<{
  navigate: [page: string]
}>();

const serviceState = ref('offline');
const activeWorkers = ref<number[]>([]);
const startingWorkers = ref<number[]>([]);
const processingWorkers = ref<number[]>([]);
const queuedWorkers = ref<number[]>([]);
const workerVips = ref<{ [key: number]: number }>({});
const usernames = ref<{ [key: number]: string }>({});
const workerNewcomers = ref<{ [key: number]: boolean }>({});
const refreshInterval = ref<number | null>(null);

// Use VIP styles composable
const vipStyles = useVipStyles();

const getWorkerStyle = (workerId: number) => {
  const isNewcomer = workerNewcomers.value[workerId] || false;
  if (isNewcomer) {
    return {
      backgroundColor: '#FFD700',
      color: '#000',
      fontWeight: 'bold',
      border: '2px solid #FFA500',
      boxShadow: '0 0 8px rgba(255, 215, 0, 0.6)'
    };
  }
  const vipLevel = workerVips.value[workerId] || 0;
  return vipStyles.getVipStyle(vipLevel);
};

const getWorkerDisplayName = (workerId: number) => {
  return workerId.toString();
};

const fetchServiceStatus = async () => {
  try {
    const response = await axios.get<ServiceStatusData>('/api/queue/service-status', { withCredentials: true });
    const data = response.data;
    
    serviceState.value = data.service_state || 'offline';
    activeWorkers.value = data.active_workers || [];
    startingWorkers.value = data.starting_workers || [];
    processingWorkers.value = data.processing_workers || [];
    queuedWorkers.value = data.queue || [];
    workerVips.value = data.worker_vips || {};
    usernames.value = data.usernames || {};
    workerNewcomers.value = data.worker_newcomers || {};
  } catch (error) {
    console.error('Failed to fetch service status:', error);
    serviceState.value = 'offline';
    activeWorkers.value = [];
    startingWorkers.value = [];
    processingWorkers.value = [];
    queuedWorkers.value = [];
    workerVips.value = {};
    usernames.value = {};
    workerNewcomers.value = {};
  }
};

const startRefreshInterval = () => {
  refreshInterval.value = window.setInterval(fetchServiceStatus, 5000); // Update every 5 seconds
};

const stopRefreshInterval = () => {
  if (refreshInterval.value) {
    window.clearInterval(refreshInterval.value);
    refreshInterval.value = null;
  }
};

onMounted(() => {
  fetchServiceStatus();
  startRefreshInterval();
});

onUnmounted(() => {
  stopRefreshInterval();
});
</script>

<style scoped>
.service-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  background: linear-gradient(135deg, #d5a673, #173154, #8A2BE2, #FF8C00, #d5a673);
  background-size: 400% 400%;
  animation: headerGradientShift 12s ease-in-out infinite;
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
  margin: 10px;
  gap: 20px;
  min-height: 80px;
}

@keyframes headerGradientShift {
  0% { background-position: 0% 50%; }
  25% { background-position: 100% 50%; }
  50% { background-position: 50% 100%; }
  75% { background-position: 0% 50%; }
  100% { background-position: 0% 50%; }
}

.logo-section {
  flex: 0 0 auto;
  text-align: left;
}

.service-logo {
  height: 60px;
  width: auto;
  display: block;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  filter: blur(0.5px);
}

.title-navigation-section {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.title-with-language {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
}

.service-title {
  margin: 0;
  font-size: 2rem;
  font-weight: bold;
  font-family: 'Arial Black', 'Helvetica', sans-serif;
  letter-spacing: 2px;
}

.letter-t {
  color: #000;
  text-shadow: 0 0 15px rgba(255, 255, 255, 1), 0 0 25px rgba(255, 255, 255, 0.8), 0 0 35px rgba(255, 255, 255, 0.6), 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.letter-ai {
  color: #8A2BE2;
  text-shadow: 0 0 20px rgba(255, 215, 0, 1), 0 0 30px rgba(255, 215, 0, 0.8), 0 0 40px rgba(255, 215, 0, 0.6), 0 0 50px rgba(138, 43, 226, 0.4), 2px 2px 4px rgba(0, 0, 0, 0.5);
  font-weight: 900;
}

.letter-g {
  color: #000;
  text-shadow: 0 0 15px rgba(255, 255, 255, 1), 0 0 25px rgba(255, 255, 255, 0.8), 0 0 35px rgba(255, 255, 255, 0.6), 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.letter-e {
  color: #FF8C00;
  text-shadow: 0 0 20px rgba(255, 140, 0, 1), 0 0 30px rgba(255, 140, 0, 0.8), 0 0 40px rgba(255, 140, 0, 0.6), 0 0 50px rgba(255, 165, 0, 0.4), 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.letter-r {
  color: #000;
  text-shadow: 0 0 15px rgba(255, 255, 255, 1), 0 0 25px rgba(255, 255, 255, 0.8), 0 0 35px rgba(255, 255, 255, 0.6), 2px 2px 4px rgba(0, 0, 0, 0.5);
}

.version-tag {
  display: inline-block;
  margin-left: 10px;
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  font-size: 0.8rem;
  font-weight: bold;
  border-radius: 12px;
  vertical-align: middle;
  box-shadow: 0 0 8px rgba(255, 255, 255, 0.5);
}

.navigation-buttons {
  display: flex;
  justify-content: center;
  gap: 10px;
}

.nav-button {
  padding: 8px 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: bold;
  transition: all 0.3s ease;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
}

.nav-button:hover {
  background-color: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-1px);
}

.nav-button.active {
  background-color: rgba(255, 255, 255, 0.3);
  border-color: rgba(255, 255, 255, 0.7);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.status-section {
  flex: 0 0 auto;
  text-align: right;
  font-size: 0.9rem;
  line-height: 1.4;
  text-shadow: 0 0 8px rgba(255, 255, 255, 0.8), 0 0 16px rgba(255, 255, 255, 0.6), 1px 1px 2px rgba(0, 0, 0, 0.4);
  background: linear-gradient(45deg, rgba(213, 166, 115, 0.3), rgba(23, 49, 84, 0.3), rgba(138, 43, 226, 0.2), rgba(255, 140, 0, 0.2));
  background-size: 400% 400%;
  animation: gradientShift 8s ease-in-out infinite;
  padding: 10px;
  border-radius: 8px;
  min-width: 200px;
}

@keyframes gradientShift {
  0% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
  100% { background-position: 0% 50%; }
}

.status-line {
  margin-bottom: 2px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.worker-list {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.worker-badge {
  padding: 2px 6px;
  border-radius: 8px;
  background-color: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.3);
  font-weight: bold;
  font-size: 12px;
  color: inherit;
  text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.worker-badge.active {
  background-color: rgba(76, 175, 80, 0.2);
  border-color: rgba(76, 175, 80, 0.5);
}

.worker-badge.starting {
  background-color: rgba(255, 193, 7, 0.2);
  border-color: rgba(255, 193, 7, 0.5);
  animation: pulse 1.5s infinite;
}

.worker-badge.processing {
  background-color: rgba(33, 150, 243, 0.2);
  border-color: rgba(33, 150, 243, 0.5);
  animation: processing-pulse 1s infinite;
}

.worker-badge.queue {
  background-color: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.3);
}

.newcomer-badge {
  margin-right: 4px;
  font-size: 14px;
  animation: star-twinkle 1.5s ease-in-out infinite alternate;
}

@keyframes star-twinkle {
  from {
    opacity: 0.8;
    transform: scale(1);
  }
  to {
    opacity: 1;
    transform: scale(1.1);
  }
}

.worker-badge.current-user {
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.8), 0 0 20px rgba(255, 255, 255, 0.6), 0 0 30px rgba(255, 255, 255, 0.4);
  border: 2px solid rgba(255, 255, 255, 0.9);
  background-color: rgba(255, 255, 255, 0.95);
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

@keyframes processing-pulse {
  0% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.05); }
  100% { opacity: 1; transform: scale(1); }
}

.no-workers {
  color: rgba(255, 255, 255, 0.7);
  font-style: italic;
  font-size: 12px;
}

.starting-label {
  margin-left: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.processing-label {
  margin-left: 8px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.active-label {
  color: white;
  font-weight: bold;
}



.language-selector {
  display: flex;
  align-items: center;
}

.custom-language-select {
  position: relative;
  display: inline-block;
}

.selected-language {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background-color: rgba(255, 255, 255, 0.1);
  color: white;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(5px);
  min-width: 80px;
}

.selected-language:hover {
  background-color: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
}

.dropdown-arrow {
  width: 12px;
  height: 12px;
  transition: transform 0.2s ease;
}

.dropdown-arrow.open {
  transform: rotate(180deg);
}

.language-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: rgba(44, 62, 80, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  backdrop-filter: blur(10px);
  z-index: 1000;
  margin-top: 2px;
}

.language-option {
  padding: 8px 12px;
  color: white;
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: 12px;
}

.language-option:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.language-option.active {
  background-color: rgba(255, 255, 255, 0.2);
  font-weight: bold;
}

.language-option:first-child {
  border-radius: 6px 6px 0 0;
}

.language-option:last-child {
  border-radius: 0 0 6px 6px;
}



/* Mobile optimizations for ServiceHeader */
@media (max-width: 768px) {
  .service-header {
    flex-direction: column;
    padding: 8px;
    gap: 8px;
  }
  
  .logo-section {
    width: 100%;
    text-align: center;
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  .service-logo {
    max-width: 150px;
    height: auto;
  }
  
  .title-navigation-section {
    width: 100%;
  }
  
  .title-with-language {
    flex-direction: column;
    gap: 10px;
    margin-bottom: 10px;
  }
  
  .service-title {
    font-size: 20px;
    margin: 4px 0;
  }
  
  .navigation-buttons {
    display: flex;
    justify-content: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  
  .nav-button {
    padding: 8px 16px;
    font-size: 13px;
    min-height: 40px;
    flex: 1;
    min-width: 110px;
  }
  
  .status-section {
    width: 100%;
    text-align: center;
    min-width: auto;
  }
  
  .selected-language {
    font-size: 12px;
    padding: 4px 8px;
    min-height: 32px;
    min-width: 80px;
  }
  
  .language-option {
    font-size: 12px;
    padding: 8px 10px;
  }
  
  .navigation-buttons {
    margin-bottom: 10px;
  }
  
  .status-line {
    font-size: 11px;
    margin: 3px 0;
    line-height: 1.3;
  }
  
  .worker-badge {
    font-size: 10px;
    padding: 2px 6px;
    margin: 1px;
    display: inline-block;
  }
  
  .worker-list {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 2px;
  }
}

/* Small mobile devices */
@media (max-width: 480px) {
  .service-header {
    padding: 8px;
    gap: 8px;
  }
  
  .service-logo {
    max-width: 150px;
  }
  
  .service-title {
    font-size: 18px;
    margin: 3px 0;
  }
  
  .nav-button {
    padding: 6px 12px;
    font-size: 12px;
    min-width: 90px;
  }
  
  .status-line {
    font-size: 11px;
  }
  
  .worker-badge {
    font-size: 9px;
    padding: 1px 4px;
  }
}

/* Small screens - keep all status info visible */
@media (max-width: 360px) {
  .service-header {
    padding: 6px;
    gap: 6px;
  }
  
  .service-title {
    font-size: 16px;
    margin: 2px 0;
  }
  
  .nav-button {
    padding: 5px 10px;
    font-size: 11px;
    min-width: 80px;
    min-height: 36px;
  }
  
  .selected-language {
    font-size: 10px;
    padding: 3px 6px;
    min-height: 28px;
    min-width: 60px;
  }
  
  .status-line {
    font-size: 10px;
    margin: 2px 0;
  }
  
  .worker-badge {
    font-size: 8px;
    padding: 1px 3px;
  }
  
  .title-with-language {
    flex-direction: column;
    gap: 6px;
  }
}
</style>
