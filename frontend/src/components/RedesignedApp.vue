<template>
  <div class="redesigned-ui">
    <!-- Redesigned Header -->
    <RedesignedHeader @settings-clicked="goToSettings" />
    
    <!-- Main Content Area -->
    <div class="redesigned-main">
      <div class="tab-content">
        <transition name="fade" mode="out-in">
          <!-- Home Tab -->
          <HomeTab 
            v-if="activeTab === 'home'"
            key="home"
            @show-activity="goToActivity"
          />
          
          <!-- Activity Tab -->
          <ActivityTab 
            v-else-if="activeTab === 'activity'" 
            key="activity"
          />
          
          <!-- Channels Tab -->
          <ChannelsTab 
            v-else-if="activeTab === 'channels'"
            key="channels"
            @open-rule-wizard="handleOpenRuleWizardEvent"
          >
            <template #channel-pairs-component>
              <slot name="channel-pairs"></slot>
            </template>
          </ChannelsTab>
          
          <!-- Settings Tab -->
          <SettingsTab 
            v-else-if="activeTab === 'settings'"
            key="settings"
            @show-info="emit('show-info')"
            @logout="emit('logout')"
            @toggle-ui-design="emit('toggle-ui-design', $event)"
            @refresh-account="emit('refresh-account')"
          />
        </transition>
      </div>
      
      <!-- Tab Navigation -->
      <TabNavigation 
        :active-tab="activeTab"
        @tab-changed="handleTabChange"
      />
    </div>
    
    <!-- Auxiliary slots rendered globally -->
    <slot name="modals"></slot>
    <slot name="notifications"></slot>
  </div>
</template>

<script setup lang="ts">
import { ref, provide, computed, watch, inject } from 'vue'
import RedesignedHeader from './RedesignedHeader.vue'
import TabNavigation from './TabNavigation.vue'
import HomeTab from './HomeTab.vue'
import ActivityTab from './ActivityTab.vue'
import ChannelsTab from './ChannelsTab.vue'
import SettingsTab from './SettingsTab.vue'

// Define props that will be passed down from the original Dashboard
interface Props {
  userInfo?: any
  workerData?: any
  loading?: boolean
  error?: string | null
  isWorkerToggling?: boolean
  isStartLocked?: boolean
  hasChannelRules?: boolean
  scheduledPosts?: any[]
  realtimeLogs?: any[]
  workerErrors?: any[]
  rules?: any[]
  subscribedChannels?: any[]
  adminChannels?: any[]
  loadingChannels?: boolean
  currentUserId?: number
  /**
   * Optional external request to switch the tab.
   * Used to auto-open the rule wizard for new users (no rules) by forcing the Channels tab.
   */
  requestedTab?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  userInfo: null,
  workerData: null,
  loading: false,
  error: null,
  isWorkerToggling: false,
  isStartLocked: false,
  hasChannelRules: false,
  scheduledPosts: () => [],
  realtimeLogs: () => [],
  workerErrors: () => [],
  rules: () => [],
  subscribedChannels: () => [],
  adminChannels: () => [],
  loadingChannels: false,
  currentUserId: 0,
  requestedTab: null
})

// Provide data to child components as computed reactive values
provide('userInfo', computed(() => props.userInfo))
provide('workerData', computed(() => props.workerData))
provide('loading', computed(() => props.loading))
provide('isLoading', computed(() => props.loading)) // Add isLoading alias for compatibility
provide('error', computed(() => props.error))
provide('isWorkerToggling', computed(() => props.isWorkerToggling || props.isStartLocked))
provide('isStartLocked', computed(() => props.isStartLocked))
const transitionalStatuses = ['starting', 'pending', 'processing', 'added_to_queue']
const launchInProgress = computed(() => {
  const status = props.workerData?.status || ''
  if (props.isStartLocked) return true
  return transitionalStatuses.includes(status)
})
provide('isLaunchInProgress', launchInProgress)
provide('hasChannelRules', computed(() => {
  console.log('🎯 RedesignedApp: Providing hasChannelRules:', props.hasChannelRules)
  return props.hasChannelRules
}))
provide('scheduledPosts', computed(() => {
  console.log('🎯 RedesignedApp: Providing scheduledPosts:', props.scheduledPosts?.length || 0)
  return props.scheduledPosts
}))
provide('realtimeLogs', computed(() => {
  console.log('🎯 RedesignedApp: Providing realtimeLogs:', props.realtimeLogs?.length || 0)
  return props.realtimeLogs
}))
provide('workerErrors', computed(() => {
  console.log('🎯 RedesignedApp: Providing workerErrors:', props.workerErrors?.length || 0)
  return props.workerErrors
}))
provide('rules', computed(() => props.rules))
provide('subscribedChannels', computed(() => {
  console.log('🎯 RedesignedApp: Providing subscribedChannels:', props.subscribedChannels?.length || 0)
  return props.subscribedChannels
}))
provide('adminChannels', computed(() => {
  console.log('🎯 RedesignedApp: Providing adminChannels:', props.adminChannels?.length || 0)
  return props.adminChannels
}))
provide('loadingChannels', computed(() => {
  console.log('🎯 RedesignedApp: Providing loadingChannels:', props.loadingChannels)
  return props.loadingChannels
}))
provide('currentUserId', computed(() => props.currentUserId))
provide('logs', computed(() => props.realtimeLogs || [])) // Provide logs from realtimeLogs
provide('activeTab', computed(() => activeTab.value)) // Provide activeTab to children

// Provide service status data for the header
const serviceStatus = computed(() => {
  // Calculate service status based on worker data and other indicators
  let status = 'unknown'
  if (props.workerData) {
    if (props.workerData.status === 'running' || props.workerData.status === 'active') {
      status = 'online'
    } else if (props.workerData.status === 'maintenance') {
      status = 'maintenance'
    } else if (props.workerData.status === 'stopped' || props.workerData.status === 'offline') {
      status = 'offline'
    }
  }
  
  return {
    status: status,
    active_workers: props.workerData?.status === 'running' || props.workerData?.status === 'active' ? 1 : 0,
    queue_length: props.workerData?.queue_position || 0,
    starting_workers: props.workerData?.status === 'starting' ? 1 : 0
  }
})
provide('serviceStatus', serviceStatus)

// Provide worker control methods
provide('toggleWorker', () => {
  console.log('🎯 RedesignedApp: toggleWorker called, emitting to parent')
  emit('toggle-worker')
})
provide('startWorker', () => {
  console.log('🎯 RedesignedApp: startWorker called, emitting to parent')
  emit('start-worker')
})
provide('stopWorker', () => {
  console.log('🎯 RedesignedApp: stopWorker called, emitting to parent')
  emit('stop-worker')
})
// Define emits
const emit = defineEmits<{
  'show-info': []
  'logout': []
  'toggle-ui-design': [enabled: boolean]
  'open-rule-wizard': []
  'toggle-worker': []
  'start-worker': []
  'stop-worker': []
  'fetch-scheduled-posts': []
  'fetch-worker-errors': []
  'refresh-account': []
}>()

provide('logout', () => {
  emit('logout')
})
provide('fetchScheduledPosts', async () => {
  emit('fetch-scheduled-posts')
})
provide('fetchWorkerErrors', async () => {
  emit('fetch-worker-errors')
})
provide('refreshLogs', async () => {
  emit('fetch-scheduled-posts')
  emit('fetch-worker-errors')
})
// These will be provided by the actual ChannelPairs component when it mounts
// provide('openRuleWizard', () => {})
// provide('editRule', (rule: any) => {})
// provide('deleteRule', (id: number) => {})
provide('getChannelDisplayName', (channelValue: string | null, channels: any[]) => {
  if (!channelValue || !Array.isArray(channels) || channels.length === 0) return 'Unknown Channel'
  const channel = channels.find(c => c.id.toString() === channelValue || c.username === channelValue)
  return channel ? channel.title : 'Unknown Channel'
})

// Local state
const activeTab = ref('home')
console.log('RedesignedApp: activeTab initialized to:', activeTab.value)

// Allow parents to control the tab when needed (e.g. auto-open wizard)
watch(
  () => props.requestedTab,
  (requested) => {
    if (requested && requested !== activeTab.value) {
      console.log('RedesignedApp: requestedTab -> switching activeTab to', requested)
      activeTab.value = requested
    }
  },
  { immediate: true }
)

// Provide a setter so children (e.g. ChannelPairs/RuleWizard) can route the user back to dashboard
provide('setActiveTab', (tabId: string) => {
  console.log('RedesignedApp: setActiveTab called with', tabId)
  activeTab.value = tabId
})

// Watch activeTab changes
watch(activeTab, (newTab, oldTab) => {
  console.log('RedesignedApp: activeTab changed from', oldTab, 'to', newTab)
})

// Methods
const handleTabChange = (tabId: string) => {
  console.log('RedesignedApp: handleTabChange called with', tabId)
  activeTab.value = tabId
  console.log('RedesignedApp: activeTab set to', activeTab.value)
}

const goToActivity = () => {
  activeTab.value = 'activity'
}

const goToSettings = () => {
  activeTab.value = 'settings'
}

const handleOpenRuleWizardEvent = () => {
  console.log('🎨 RedesignedApp: Received open-rule-wizard event, forwarding to App.vue')
  // Try to use the injected openRuleWizard method first
  const openRuleWizard = inject('openRuleWizard', null);
  if (openRuleWizard && typeof openRuleWizard === 'function') {
    console.log('🎨 RedesignedApp: Calling injected openRuleWizard method')
    openRuleWizard();
  } else {
    console.log('🎨 RedesignedApp: No injected openRuleWizard found, forwarding event to App.vue')
    emit('open-rule-wizard');
  }
}

// Watch for data changes
watch([() => props.scheduledPosts, () => props.realtimeLogs, () => props.workerErrors], ([posts, logs, errors]) => {
  console.log('🎯 RedesignedApp: Data changed:', {
    scheduledPosts: posts?.length || 0,
    realtimeLogs: logs?.length || 0,
    workerErrors: errors?.length || 0
  })
}, { deep: true })
</script>

<style scoped>
/* All styles are defined in redesign.css */
</style>
