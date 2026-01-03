<template>
  <div class="tab-navigation">
    <button 
      v-for="tab in tabs" 
      :key="tab.id"
      @click="handleTabClick(tab.id)"
      :class="['tab-button', { active: activeTab === tab.id }]"
    >
      <div class="tab-icon">{{ tab.icon }}</div>
      <div class="tab-label">{{ $t(tab.label) }}</div>
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t: $t } = useI18n()

interface Tab {
  id: string
  icon: string
  label: string
}

interface Props {
  activeTab: string
}

withDefaults(defineProps<Props>(), {
  activeTab: 'home'
})

const emit = defineEmits<{
  'tab-changed': [tabId: string]
}>()

const handleTabClick = (tabId: string) => {
  console.log('TabNavigation: Tab clicked:', tabId)
  emit('tab-changed', tabId)
}

const tabs: Tab[] = [
  { id: 'home', icon: '📊', label: 'dashboard' },
  { id: 'activity', icon: '📝', label: 'agent_log' },
  { id: 'channels', icon: '📢', label: 'channels' },
  { id: 'settings', icon: '⚙️', label: 'settings' }
]
</script>

<style scoped>
/* Tab navigation styles are defined in redesign.css */
</style>