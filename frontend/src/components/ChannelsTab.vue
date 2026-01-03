<template>
  <div class="channels-tab">
    <!-- Pass through the existing ChannelPairs component for form functionality -->
    <!-- We need the ChannelPairs component to be rendered so its modals can appear -->
    <slot name="channel-pairs-component"></slot>
    
    <!-- Floating Action Button for Adding New Rule -->
    <button @click="handlePlusButtonClick" class="btn-fab">
      ➕
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, inject, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { tmaLog } from '../utils/tmaUtils'

const { t: $t } = useI18n()

// Define emits
const emit = defineEmits<{
  'open-rule-wizard': []
}>()

// Methods
const handlePlusButtonClick = () => {
  tmaLog('📺 TMA ChannelsTab: + button clicked, emitting open-rule-wizard event')
  emit('open-rule-wizard')
}
</script>

<style scoped>
.channels-tab {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
  position: relative;
  min-height: calc(100vh - 160px);
}

.btn-fab {
  position: fixed;
  bottom: 80px;
  right: 20px;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--primary-color);
  color: white;
  border: none;
  font-size: 24px;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
}

.btn-fab:hover {
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}
</style>