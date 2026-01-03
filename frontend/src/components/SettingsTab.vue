<template>
  <div class="settings-tab">
    <!-- Account Refresh Section -->
    <div v-if="isTMAEnvironment" class="redesigned-card">
      <div class="settings-section">
        <div class="setting-item" @click="refreshAccount">
          <div class="setting-info">
            <div class="setting-icon">🔄</div>
            <div class="setting-content">
              <div class="setting-title">{{ $t('refresh_account') || 'Refresh Account' }}</div>
              <div class="setting-description">{{ $t('refresh_account_desc') || 'Update account data if you switched Telegram accounts' }}</div>
            </div>
          </div>
          <div class="setting-action">
            <div v-if="isRefreshing" class="loading-spinner-small"></div>
            <span v-else class="arrow">▶</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Preferences Section -->
    <div class="redesigned-card">
      <div class="card-header">
        <h3 class="card-title">{{ $t('preferences') || 'Preferences' }}</h3>
      </div>
      
      <div class="settings-section">
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-icon">🎨</div>
            <div class="setting-content">
              <div class="setting-title">{{ $t('theme') || 'Theme' }}</div>
              <div class="setting-description">{{ $t('interface_appearance') || 'Interface appearance' }}</div>
            </div>
          </div>
          <div class="setting-action">
            <select v-model="selectedTheme" @change="changeTheme" class="form-select">
              <option value="auto">{{ $t('auto') || 'Auto' }}</option>
              <option value="light">{{ $t('light') || 'Light' }}</option>
              <option value="dark">{{ $t('dark') || 'Dark' }}</option>
            </select>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-icon">🔄</div>
            <div class="setting-content">
              <div class="setting-title">{{ $t('ui_design') || 'UI Design' }}</div>
              <div class="setting-description">{{ $t('switch_between_interfaces') || 'Switch between old and new interface' }}</div>
            </div>
          </div>
          <div class="setting-action">
            <label class="toggle-switch">
              <input type="checkbox" v-model="useRedesignedUI" @change="toggleUIDesign">
              <span class="toggle-slider"></span>
            </label>
            <span class="toggle-label">{{ $t('new_design') || 'New Design' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Worker Settings Section -->
    <div class="redesigned-card">
      <div class="card-header">
        <h3 class="card-title">{{ $t('worker_settings') || 'Worker Settings' }}</h3>
      </div>
      
      <div class="settings-section">
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-icon">⏱️</div>
            <div class="setting-content">
              <div class="setting-title">{{ $t('auto_stop_timeout') || 'Auto-stop Timeout' }}</div>
              <div class="setting-description">{{ $t('worker_auto_stop_desc') || 'Worker automatically stops after this time' }}</div>
            </div>
          </div>
          <div class="setting-action">
            <span class="setting-value">{{ getAutoStopTimeout() }}</span>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-icon">🔊</div>
            <div class="setting-content">
              <div class="setting-title">{{ $t('sound_notifications') || 'Sound Notifications' }}</div>
              <div class="setting-description">{{ $t('play_sounds_for_events') || 'Play sounds for worker events' }}</div>
            </div>
          </div>
          <div class="setting-action">
            <label class="toggle-switch">
              <input type="checkbox" v-model="soundEnabled" @change="updateSoundSettings">
              <span class="toggle-slider"></span>
            </label>
          </div>
        </div>
      </div>
    </div>

    <!-- Support Section -->
    <div class="redesigned-card">
      <div class="card-header">
        <h3 class="card-title">{{ $t('support') || 'Support' }}</h3>
      </div>
      
      <div class="settings-section">
        <div class="setting-item" @click="showInfoPage">
          <div class="setting-info">
            <div class="setting-icon">❓</div>
            <div class="setting-content">
              <div class="setting-title">{{ $t('help_faq') || 'Help & FAQ' }}</div>
              <div class="setting-description">{{ $t('get_help_support') || 'Get help and support' }}</div>
            </div>
          </div>
          <div class="setting-action">
            <span class="arrow">▶</span>
          </div>
        </div>
        
        <div class="setting-item">
          <div class="setting-info">
            <div class="setting-icon">📝</div>
            <div class="setting-content">
              <div class="setting-title">{{ $t('send_feedback') || 'Send Feedback' }}</div>
              <div class="setting-description">{{ $t('report_issues_suggestions') || 'Report issues or suggestions' }}</div>
            </div>
          </div>
          <div class="setting-action">
            <span class="arrow">▶</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Account Actions -->
    <div class="redesigned-card">
      <div class="logout-section">
        <button @click="confirmLogout" class="btn-redesigned btn-danger logout-btn">
          🚪 {{ $t('logout') || 'Logout' }}
        </button>
      </div>
    </div>

    <!-- Logout Confirmation Modal -->
    <div v-if="showLogoutModal" class="modal-overlay" @click="cancelLogout">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">{{ $t('confirm_logout') || 'Confirm Logout' }}</h3>
        </div>
        <div class="modal-body">
          <p>{{ $t('logout_confirmation_message') || 'Are you sure you want to logout?' }}</p>
        </div>
        <div class="modal-footer">
          <button @click="cancelLogout" class="btn-redesigned btn-secondary">
            {{ $t('cancel') || 'Cancel' }}
          </button>
          <button @click="performLogout" class="btn-redesigned btn-danger">
            {{ $t('logout') || 'Logout' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, inject, computed, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t: $t } = useI18n()

interface UserInfo {
  id: number
  username: string
  balance?: number
  avatar_url?: string
  VIP_level?: number
}

// Define emits
const emit = defineEmits<{
  'show-info': []
  'logout': []
  'toggle-ui-design': [enabled: boolean]
  'refresh-account': []
}>()

// Inject user data
const userInfo = inject<Ref<UserInfo | null>>('userInfo', ref(null))

// Local state
const showLogoutModal = ref(false)
const selectedTheme = ref('auto')
const notificationsEnabled = ref(true)
const soundEnabled = ref(true)
const useRedesignedUI = ref(true) // This should be injected from parent
const isRefreshing = ref(false)

const isTMAEnvironment = computed(() => {
  return document.body.classList.contains('tma-environment') || 
         !!(window as any).Telegram?.WebApp?.initData
})

// Methods

const changeTheme = () => {
  // Save theme preference
  localStorage.setItem('preferred_theme', selectedTheme.value)
  
  // Apply theme changes to document
  applyTheme(selectedTheme.value)
}

const applyTheme = (theme: string) => {
  const root = document.documentElement
  const body = document.body
  
  // Remove existing theme classes
  body.classList.remove('theme-light', 'theme-dark', 'theme-auto')
  
  // Apply new theme
  if (theme === 'dark') {
    body.classList.add('theme-dark')
    updateTMATheme('dark')
  } else if (theme === 'light') {
    body.classList.add('theme-light')
    updateTMATheme('light')
  } else {
    // Auto theme - use system preference
    body.classList.add('theme-auto')
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    updateTMATheme(systemDark ? 'dark' : 'light')
  }
}

const updateTMATheme = (theme: 'light' | 'dark') => {
  const body = document.body
  if (!body.classList.contains('tma-environment')) return
  
  const root = document.documentElement
  
  if (theme === 'dark') {
    // Dark theme colors for TMA
    root.style.setProperty('--tg-theme-bg-color', '#1a1a1a')
    root.style.setProperty('--tg-theme-text-color', '#ffffff')
    root.style.setProperty('--tg-theme-hint-color', '#b0b0b0')
    root.style.setProperty('--tg-theme-link-color', '#64b5f6')
    root.style.setProperty('--tg-theme-button-color', '#64b5f6')
    root.style.setProperty('--tg-theme-button-text-color', '#000000')
    
    body.style.backgroundColor = '#1a1a1a'
    body.style.color = '#ffffff'
    body.classList.add('tma-dark-theme')
    body.classList.remove('tma-light-theme')
  } else {
    // Light theme colors for TMA
    root.style.setProperty('--tg-theme-bg-color', '#ffffff')
    root.style.setProperty('--tg-theme-text-color', '#1a1a1a')
    root.style.setProperty('--tg-theme-hint-color', '#666666')
    root.style.setProperty('--tg-theme-link-color', '#0088cc')
    root.style.setProperty('--tg-theme-button-color', '#0088cc')
    root.style.setProperty('--tg-theme-button-text-color', '#ffffff')
    
    body.style.backgroundColor = '#ffffff'
    body.style.color = '#1a1a1a'
    body.classList.add('tma-light-theme')
    body.classList.remove('tma-dark-theme')
  }
}

const toggleUIDesign = () => {
  // Emit to parent component to toggle UI design
  emit('toggle-ui-design', useRedesignedUI.value)
}

const updateNotifications = () => {
  localStorage.setItem('notifications_enabled', notificationsEnabled.value.toString())
}

const updateSoundSettings = () => {
  localStorage.setItem('sound_enabled', soundEnabled.value.toString())
}

const showInfoPage = () => {
  emit('show-info')
}

const confirmLogout = () => {
  showLogoutModal.value = true
}

const cancelLogout = () => {
  showLogoutModal.value = false
}

const performLogout = () => {
  showLogoutModal.value = false
  emit('logout')
}

const refreshAccount = async () => {
  if (isRefreshing.value) return

  isRefreshing.value = true
  try {
    emit('refresh-account')
    setTimeout(() => {
      console.log('Account refresh completed')
    }, 1000)
  } catch (error) {
    console.error('Account refresh failed:', error)
  } finally {
    setTimeout(() => {
      isRefreshing.value = false
    }, 2000)
  }
}

const getAutoStopTimeout = () => {
  const vipLevel = userInfo.value?.VIP_level || 0
  const timeouts = { 0: 5, 1: 10, 2: 20, 3: 30 }
  return `${timeouts[vipLevel as keyof typeof timeouts] || 5} min`
}

// Load saved preferences on component mount
const loadPreferences = () => {
  const savedTheme = localStorage.getItem('preferred_theme')
  if (savedTheme) {
    selectedTheme.value = savedTheme
    applyTheme(savedTheme)
  } else {
    // Default to auto theme
    selectedTheme.value = 'auto'
    applyTheme('auto')
  }
  
  const savedNotifications = localStorage.getItem('notifications_enabled')
  if (savedNotifications) notificationsEnabled.value = savedNotifications === 'true'
  
  const savedSound = localStorage.getItem('sound_enabled')
  if (savedSound) soundEnabled.value = savedSound === 'true'
}

// Initialize preferences
loadPreferences()

// Listen for system theme changes when theme is set to auto
const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
const handleSystemThemeChange = (e: MediaQueryListEvent) => {
  if (selectedTheme.value === 'auto') {
    updateTMATheme(e.matches ? 'dark' : 'light')
  }
}
mediaQuery.addEventListener('change', handleSystemThemeChange)
</script>

<style scoped>
.settings-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.settings-section {
  display: flex;
  flex-direction: column;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-md);
  border-bottom: 1px solid var(--bg-secondary);
  cursor: pointer;
  transition: background 0.2s ease;
}

.setting-item:hover {
  background: var(--bg-section);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-info {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex: 1;
}

.setting-icon {
  font-size: 24px;
  width: 32px;
  text-align: center;
}

.setting-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.setting-title {
  font-size: var(--text-md);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
}

.setting-description {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.setting-action {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.setting-value {
  font-size: var(--text-sm);
  color: var(--text-hint);
  font-weight: var(--weight-medium);
}

.arrow {
  color: var(--text-hint);
  font-size: 12px;
}

.form-select {
  min-width: 120px;
  margin: 0;
}

.toggle-switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
}

.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: var(--bg-secondary);
  border-radius: 24px;
  transition: 0.3s;
}

.toggle-slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background-color: white;
  border-radius: 50%;
  transition: 0.3s;
  box-shadow: var(--shadow-sm);
}

input:checked + .toggle-slider {
  background-color: var(--primary);
}

input:checked + .toggle-slider:before {
  transform: translateX(20px);
}

.toggle-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
  margin-left: var(--space-xs);
}

.loading-spinner-small {
  width: 16px;
  height: 16px;
  border: 2px solid var(--bg-secondary);
  border-top: 2px solid var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.logout-section {
  padding: var(--space-md);
  text-align: center;
}

.logout-btn {
  width: 100%;
  max-width: 200px;
}

/* Mobile responsive adjustments */
@media (max-width: 768px) {
  .setting-item {
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-md);
  }
  
  .setting-info {
    justify-content: flex-start;
  }
  
  .setting-action {
    justify-content: flex-end;
  }
}
</style>