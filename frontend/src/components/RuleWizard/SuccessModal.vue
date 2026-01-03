<template>
  <div class="success-modal-overlay">
    <div class="success-modal">
      <div class="success-header">
        <div class="success-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
        </div>
        <h2>{{ $t('rule_created_successfully') }}</h2>
      </div>

      <div class="success-content">
        <h3>{{ $t('what_to_do_next') }}</h3>
        <p>{{ $t('next_steps_instruction') }}</p>
        
        <div class="steps-list">
          <div class="step-item">
            <span class="step-number">1</span>
            <span class="step-text">{{ $t('step_1_post_to_draft') }}</span>
          </div>
          <div class="step-item">
            <span class="step-number">2</span>
            <span class="step-text">{{ $t('step_2_wait_processing') }}</span>
          </div>
          <div class="step-item">
            <span class="step-number">3</span>
            <span class="step-text">{{ $t('step_3_check_target') }}</span>
          </div>
          <div class="step-item">
            <span class="step-number">4</span>
            <span class="step-text">{{ $t('step_4_monitor_logs') }}</span>
          </div>
        </div>

        <div class="channel-info">
          <div class="channel-item">
            <strong>{{ $t('source_channel') }}:</strong> {{ sourceChannelName }}
          </div>
          <div class="channel-item">
            <strong>{{ $t('target_channel') }}:</strong> {{ targetChannelName }}
          </div>
        </div>
      </div>

      <div class="success-footer">
        <button @click="$emit('close')" class="continue-btn">
          {{ $t('continue_to_dashboard') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'SuccessModal',
  props: {
    sourceChannelName: {
      type: String,
      required: true
    },
    targetChannelName: {
      type: String,
      required: true
    }
  },
  emits: ['close'],
  setup() {
    const { t: $t } = useI18n();
    
    return {
      $t
    };
  }
});
</script>

<style scoped>
.success-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10001;
  padding: 20px;
}

.success-modal {
  background: white;
  border-radius: 12px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
}

.success-header {
  text-align: center;
  padding: 30px 30px 20px;
  border-bottom: 1px solid #e0e0e0;
}

.success-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  background: #28a745;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.success-header h2 {
  margin: 0;
  color: #28a745;
  font-size: 24px;
  font-weight: 600;
}

.success-content {
  padding: 30px;
}

.success-content h3 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
}

.success-content p {
  margin: 0 0 24px 0;
  color: #666;
  line-height: 1.6;
}

.steps-list {
  margin-bottom: 24px;
}

.step-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}

.step-number {
  width: 24px;
  height: 24px;
  background: #007bff;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.step-text {
  color: #333;
  line-height: 1.5;
}

.channel-info {
  background: #e3f2fd;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 24px;
}

.channel-item {
  margin-bottom: 8px;
  color: #1565c0;
  font-size: 14px;
}

.channel-item:last-child {
  margin-bottom: 0;
}

.success-footer {
  padding: 20px 30px;
  border-top: 1px solid #e0e0e0;
  text-align: center;
}

.continue-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
  min-width: 200px;
}

.continue-btn:hover {
  background: #0056b3;
}

@media (max-width: 768px) {
  .success-modal-overlay {
    padding: 10px;
  }
  
  .success-header {
    padding: 20px 20px 16px;
  }
  
  .success-content {
    padding: 20px;
  }
  
  .success-footer {
    padding: 16px 20px;
  }
  
  .continue-btn {
    width: 100%;
  }
}
</style>