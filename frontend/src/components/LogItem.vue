<template>
  <div class="log-item" :class="{ 'log-new': isNew }">
    <div class="log-header">
      <span class="log-level" :class="`level-${log.level}`">{{ log.level }}</span>
      <span class="log-time">{{ formattedTime }}</span>
    </div>
    <div class="log-message">{{ translatedMessage }}</div>
    <div v-if="log.details" class="log-details">{{ log.details }}</div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, computed } from 'vue'

interface LogMessage {
  id: string
  timestamp: string
  level: 'info' | 'success' | 'warning' | 'error'
  message: string
  details?: string
  status?: string
}

const props = defineProps<{
  log: LogMessage,
  isNew: boolean,
  translateFn: Function,
  formatTimeFn: Function
}>()

const translatedMessage = computed(() => {
  return props.translateFn(props.log)
})

const formattedTime = computed(() => {
    return props.formatTimeFn(props.log.timestamp)
})

</script>