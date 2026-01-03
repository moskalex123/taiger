<template>
  <div class="home-tab">
    <!-- User Profile Card (Static) -->
    <div class="redesigned-card">
      <div class="card-header">
        <div class="user-profile-summary">
          <div class="user-avatar">
            <img :src="userInfo?.avatar_url || '/avatars/default.png'" alt="User Avatar" />
          </div>
          <div class="user-basic-info">
            <div class="username">{{ userInfo?.username || 'User' }} (ID: {{ userInfo?.id || 'N/A' }})</div>
            <!-- VIP уровень под именем пользователя -->
            <div v-if="userInfo?.VIP_level !== undefined" class="vip-level-compact" :style="vipStyles.getVipStyle(userInfo.VIP_level || 0)">
              ⭐ {{ $t('vip_level') }}: {{ userInfo?.VIP_level || 0 }}
            </div>
            <div v-else class="vip-level-compact" :style="vipStyles.getVipStyle(0)">
              ⭐ {{ $t('vip_level') }}: 0
            </div>
            <!-- Баланс под VIP уровнем -->
            <div v-if="userInfo?.balance !== undefined" class="balance-compact" :class="getBalanceColorClass(userInfo.balance)">
              🔋 <PriceDisplay 
                :price="userInfo.balance" 
                :show-exchange-info="true"
                :decimals="1"
              />
            </div>
            <div v-else class="balance-compact balance-unknown">
              🔋 {{ $t('balance') }}: {{ $t('loading') }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Primary Worker Control -->
    <div class="redesigned-card">
      <div class="card-header">
        <div class="worker-title-row">
          <h3 class="card-title">
            {{ getWorkerTitle() }}
            <span :class="['status-indicator', statusClass]">
              {{ getStatusIcon() }} {{ workerStatusDisplay }}
            </span>
          </h3>
          <span v-if="workerData?.queue_position" class="queue-info">
            {{ $t('queue_position') }}: {{ workerData.queue_position }}
          </span>
        </div>
      </div>
      
      <div v-if="error" class="error-state">
        <div class="activity-icon error">❌</div>
        <p>{{ $t('error') }}: {{ error }}</p>
      </div>
      
      <div v-else class="worker-control-content">
        <!-- Primary Action Button -->
        <div class="primary-action">
          <button 
            @click="toggleWorker" 
            :disabled="isButtonDisabled"
            :class="[
              'btn-redesigned', 
              'btn-primary', 
              'worker-action-btn', 
              isWorkerRunning ? 'worker-action-running' : 'worker-action-stopped', 
              { 'loading': isWorkerToggling }
            ]"
          >
            <div v-if="isWorkerToggling" class="loading-spinner"></div>
            <span v-else class="action-icon">{{ getActionIcon() }}</span>
            <span class="action-text">{{ getWorkerButtonText() }}</span>
          </button>
        </div>

        <!-- Warning Messages -->
        <div v-if="!hasChannelRules" class="warning-message">
          ⚠️ {{ $t('cannot_start_no_rules') }}
        </div>
        
        <div v-if="workerData?.status === 'auth_required'" class="auth-required-message">
          🔐 {{ $t('auth_required_message') }}
          <button @click="logout" class="btn-redesigned btn-secondary btn-sm">
            {{ $t('logout_and_reauth') }}
          </button>
        </div>

        <!-- Last Worker Log -->
        <div v-if="lastWorkerLog" class="last-log-display">
          <div class="last-log-content">
            {{ lastWorkerLog.message }}
          </div>
        </div>
      </div>
    </div>


  </div>
</template>

<script setup lang="ts">
import { ref, computed, inject, watch, onBeforeUnmount, type Ref, type ComputedRef } from 'vue'
import { useI18n } from 'vue-i18n'
import PriceDisplay from './PriceDisplay.vue'
import { useVipStyles } from '../composables/useVipStyles'

// Define interfaces for better type safety
interface UserInfo {
  id: number
  username: string
  balance?: number
  avatar_url?: string
  VIP_level?: number
}

interface WorkerData {
  status: string
  queue_position?: number
  remaining_seconds?: number
}

const { t: $t, locale } = useI18n()
const vipStyles = useVipStyles()

// Props and emits
defineEmits<{
  'show-activity': []
}>()

// Inject dashboard data and methods from parent Dashboard component with proper typing
const userInfo = inject<Ref<UserInfo | null>>('userInfo', ref(null))
const workerData = inject<Ref<WorkerData | null>>('workerData', ref(null))
const loading = inject<Ref<boolean>>('loading', ref(false))
const error = inject<Ref<string | null>>('error', ref(null))
const isWorkerToggling = inject<Ref<boolean>>('isWorkerToggling', ref(false))
const defaultLaunchInProgress = computed(() => false)
const externalLaunchInProgress = inject<ComputedRef<boolean>>('isLaunchInProgress', defaultLaunchInProgress)
const defaultStartLocked = computed(() => false)
const injectedStartLocked = inject<ComputedRef<boolean>>('isStartLocked', defaultStartLocked)
const hasChannelRules = inject<Ref<boolean>>('hasChannelRules', ref(false))
const realtimeLogs = inject<Ref<any[]>>('realtimeLogs', ref([]))

// Debug watcher for hasChannelRules
watch(hasChannelRules, (newValue, oldValue) => {
  console.log('🎯 HomeTab: hasChannelRules changed from', oldValue, 'to', newValue)
}, { immediate: true })
// Provide default implementations for missing methods
const toggleWorker = inject<() => void>('toggleWorker', () => {
  console.warn('toggleWorker method not provided')
})
const logout = inject<() => void>('logout', () => {
  console.warn('logout method not provided')
})

// Local state (убрали showUserDetails)
const remainingSeconds = ref<number | null>(null)
let remainingInterval: ReturnType<typeof setInterval> | null = null

const clearRemainingInterval = () => {
  if (remainingInterval) {
    clearInterval(remainingInterval)
    remainingInterval = null
  }
}

const initializeRemainingTimer = (data: WorkerData | null | undefined) => {
  if (!data || (data.status !== 'running' && data.status !== 'active')) {
    clearRemainingInterval()
    remainingSeconds.value = null
    return
  }

  const initial = data.remaining_seconds
  if (typeof initial !== 'number' || initial <= 0) {
    clearRemainingInterval()
    remainingSeconds.value = null
    return
  }

  remainingSeconds.value = Math.floor(initial)
  clearRemainingInterval()
  remainingInterval = setInterval(() => {
    if (remainingSeconds.value === null) {
      clearRemainingInterval()
      return
    }

    if (remainingSeconds.value <= 1) {
      remainingSeconds.value = 0
      clearRemainingInterval()
    } else {
      remainingSeconds.value -= 1
    }
  }, 1000)
}

watch(() => workerData.value, (newValue) => {
  initializeRemainingTimer(newValue || null)
}, { immediate: true, deep: true })

onBeforeUnmount(() => {
  clearRemainingInterval()
})

// Computed properties
const transitionalStatuses: string[] = ['starting', 'pending', 'processing', 'added_to_queue']

const isLaunchInProgress = computed(() => {
  if (externalLaunchInProgress.value) {
    return true
  }

  if (injectedStartLocked.value) {
    return true
  }

  const status = (workerData.value?.status || '') as string
  if (transitionalStatuses.includes(status)) {
    return true
  }
  if (isWorkerToggling.value) {
    return status === '' || status === 'stopped' || status === 'not_configured'
  }
  return false
})

const workerStatusDisplay = computed(() => {
  if (!workerData.value || !workerData.value.status) return $t('unknown') || 'Unknown'

  if (isLaunchInProgress.value) {
    const status = workerData.value.status
    if (status === 'pending') {
      const position = workerData.value.queue_position
      return position ? `${$t('queue')} (${position})` : $t('queue')
    }
    if (status === 'processing') {
      return $t('processing_worker')
    }
    const activeLabel = $t('active') || 'Active'
    const startingSuffix = $t('starting_worker') || 'Starting'
    return `${activeLabel} (${startingSuffix})`
  }
  
  const status = workerData.value.status
  const statusMap: { [key: string]: string } = {
    'running': $t('running') || 'Running',
    'active': $t('active') || 'Active', 
    'stopped': $t('stopped') || 'Stopped',
    'stopping': $t('stopping') || 'Stopping',
    'error': $t('error') || 'Error',
    'not_configured': $t('not_configured') || 'Not Configured',
    'auth_required': $t('auth_required') || 'Auth Required',
    'pending': $t('pending') || 'Pending'
  }
  
  const baseLabel = statusMap[status] || ($t('unknown') || 'Unknown')

  if ((status === 'running' || status === 'active') && remainingSeconds.value && remainingSeconds.value > 0) {
    const suffix = $t('seconds_short') || 's'
    return `${baseLabel} (${remainingSeconds.value}${suffix})`
  }

  return baseLabel
})

const statusClass = computed(() => {
  if (!workerData.value) return 'status-unknown'
  
  const status = workerData.value.status
  if (isLaunchInProgress.value || status === 'running' || status === 'active') return 'status-running'
  if (status === 'starting' || status === 'pending' || status === 'processing' || status === 'added_to_queue') return 'status-starting'
  if (status === 'error' || status === 'auth_required') return 'status-error'
  if (status === 'stopped') return 'status-stopped'
  return 'status-unknown'
})

const isButtonDisabled = computed(() => {
  return loading.value || isWorkerToggling.value || isLaunchInProgress.value || !hasChannelRules.value || 
         (userInfo.value?.balance !== undefined && userInfo.value.balance < 0)
})

const isWorkerRunning = computed(() => {
  if (isLaunchInProgress.value) {
    return true
  }
  return workerData.value?.status === 'running' || workerData.value?.status === 'active'
})



// Methods (убрали toggleUserProfile)

const getBalanceColorClass = (balance: number) => {
  if (balance >= 1) return 'text-success'
  if (balance >= 0.1) return 'text-warning'
  return 'text-error'
}

const getStatusIcon = () => {
  if (!workerData.value) return '⚪'
  
  const status = workerData.value.status
  const iconMap: { [key: string]: string } = {
    'running': '🟢',
    'active': '🟢',
    'stopped': '🔴',
    'starting': '🟡',
    'stopping': '🟡',
    'error': '🔴',
    'not_configured': '⚪',
    'auth_required': '🔒',
    'pending': '🟡',
    'processing': '🟡',
    'added_to_queue': '🟡'
  }
  
  if (isLaunchInProgress.value) {
    return '🟢'
  }

  return iconMap[status] || '⚪'
}

const getWorkerTitle = () => {
  const userId = userInfo.value?.id
  if (!userId) {
    return $t('worker_control') || 'Worker Control'
  }
  
  // Check current locale
  if ($t('locale') === 'ru' || locale.value === 'ru') {
    return `Ваш агент №${userId}`
  } else {
    return `Worker ${userId}`
  }
}

// Get last log (any log) from current session
const lastWorkerLog = computed(() => {
  const logs = realtimeLogs.value || []
  if (!Array.isArray(logs) || logs.length === 0) {
    return null
  }
  
  // Просто берем последний лог без фильтрации
  return logs[0] || null
})

const getActionIcon = () => {
  return isWorkerRunning.value ? '⏹️' : '▶️'
}

const getWorkerButtonText = () => {
  if (isWorkerToggling.value || isLaunchInProgress.value) {
    return isLaunchInProgress.value ? $t('starting_worker') : $t('stopping_worker')
  }
  return isWorkerRunning.value ? $t('stop_worker') : $t('start_worker')
}

</script>

<style scoped>
.home-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.card-title {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  flex-wrap: wrap;
}

.user-profile-summary {
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  gap: var(--space-md);
  flex: 1;
  width: 100%;
}

.user-avatar {
  display: flex;
  align-items: flex-start;
}

.user-avatar img {
  align-self: flex-start;
  width: 96px;
  height: 96px;
  border-radius: var(--radius-full);
  object-fit: cover;
  border: 3px solid var(--primary);
  background-color: var(--bg-secondary);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.user-basic-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.username {
  font-size: var(--text-md);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
  margin-bottom: var(--space-xs);
  width: 100%;
}

.vip-level-compact {
  display: inline-block;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  margin-bottom: var(--space-xs);
  border: 1px solid transparent;
}

.balance-compact {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
}

.balance-unknown {
  color: var(--text-hint);
  font-style: italic;
}

/* Balance color classes */
.text-success {
  color: var(--success) !important;
}

.text-warning {
  color: var(--warning) !important;
}

.text-error {
  color: var(--error) !important;
}

.expand-icon {
  transition: transform 0.2s ease;
  font-size: 16px;
  color: var(--text-hint);
}

.expand-icon.expanded {
  transform: rotate(180deg);
}

.user-details {
  margin-top: var(--space-md);
  padding-top: var(--space-md);
  border-top: 1px solid var(--bg-secondary);
}

.vip-level {
  display: inline-block;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  margin-bottom: var(--space-md);
}

.worker-control-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.worker-status-display {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.status-label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.queue-info {
  font-size: var(--text-sm);
  color: var(--text-hint);
  text-align: center;
}

.primary-action {
  margin: var(--space-md) 0;
}

.worker-action-btn {
  width: 100%;
  min-height: 56px;
  font-size: var(--text-lg);
  font-weight: var(--weight-semibold);
  box-shadow: 0 0 0 rgba(239, 68, 68, 0.4);
  animation: worker-pulse 3s ease-in-out infinite;
}

.worker-action-btn.loading {
  opacity: 0.7;
  cursor: not-allowed;
  animation-play-state: paused;
}

.worker-action-btn:disabled {
  animation: none;
  box-shadow: none;
}
.worker-action-btn.worker-action-running {
  animation-duration: 2.5s;
}

.worker-action-btn.worker-action-stopped {
  animation-duration: 3.5s;
}

@keyframes worker-pulse {
  0%, 100% {
    box-shadow: 0 0 0 rgba(239, 68, 68, 0.2);
  }
  50% {
    box-shadow: 0 0 18px rgba(239, 68, 68, 0.45);
  }
}

.action-icon {
  font-size: 20px;
  margin-right: var(--space-sm);
}

.warning-message, 
.auth-required-message {
  padding: var(--space-md);
  border-radius: var(--radius-md);
  background: rgba(255, 152, 0, 0.1);
  border: 1px solid var(--warning);
  color: var(--warning);
  font-size: var(--text-sm);
  text-align: center;
}

.auth-required-message {
  background: rgba(244, 67, 54, 0.1);
  border-color: var(--error);
  color: var(--error);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-sm);
}

.last-log-display {
  margin-top: var(--space-md);
  padding: var(--space-sm);
  background: var(--bg-section);
  border-radius: var(--radius-md);
  border: 1px solid var(--bg-secondary);
}

.last-log-content {
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.4;
}

.loading-state, 
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-sm);
  padding: var(--space-lg);
  color: var(--text-secondary);
}

.activity-preview {
  max-height: 200px;
  overflow: hidden;
}

.no-activity {
  text-align: center;
  color: var(--text-hint);
  padding: var(--space-lg);
  font-style: italic;
}

.btn-sm {
  padding: var(--space-xs) var(--space-sm);
  font-size: var(--text-sm);
  min-height: 32px;
}

/* TMA specific styles */
.tma-environment .last-log-display {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.tma-environment .log-label {
  color: rgba(255, 255, 255, 0.6);
}

.tma-environment .last-log-content {
  color: rgba(255, 255, 255, 0.9);
}
</style>