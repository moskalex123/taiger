<template>
  <div class="wizard-navigation">
    <button 
      v-if="currentStep > 1"
      @click="$emit('prev')"
      class="nav-btn prev-btn"
      :disabled="isLoading"
    >
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <polyline points="15,18 9,12 15,6"/>
      </svg>
      {{ $t('wizard_prev') }}
    </button>
    
    <div class="nav-spacer"></div>
    
    <button 
      v-if="currentStep < totalSteps"
      @click="handleNext"
      class="nav-btn next-btn"
      :disabled="!canProceed || isLoading"
      :title="canProceed ? $t('wizard_next_tooltip') : $t('wizard_next_disabled_tooltip')"
    >
      {{ $t('wizard_next') }}
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
        <polyline points="9,18 15,12 9,6"/>
      </svg>
    </button>
    
    <button 
      v-if="currentStep === totalSteps"
      @click="handleFinish"
      class="nav-btn finish-btn"
      :disabled="!canProceed || isLoading"
      :title="canProceed ? $t('wizard_finish_tooltip') : $t('wizard_finish_disabled_tooltip')"
    >
      <div v-if="isLoading" class="button-spinner"></div>
      <span v-if="!isLoading">{{ $t('wizard_finish') }}</span>
      <span v-else>{{ $t('saving') }}</span>
    </button>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'WizardNavigation',
  props: {
    currentStep: {
      type: Number,
      required: true
    },
    totalSteps: {
      type: Number,
      required: true
    },
    canProceed: {
      type: Boolean,
      required: true
    },
    isLoading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['next', 'prev', 'finish'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();
    
    // Отладка состояния кнопок
    console.log('WizardNavigation props:', {
      currentStep: props.currentStep,
      totalSteps: props.totalSteps,
      canProceed: props.canProceed,
      isLoading: props.isLoading
    });
    
    const handleNext = () => {
      console.log('🔥 NEXT BUTTON CLICKED!');
      emit('next');
    };
    
    const handleFinish = () => {
      console.log('🔥 FINISH BUTTON CLICKED!');
      console.log('About to emit finish event');
      emit('finish');
      console.log('Finish event emitted');
    };
    
    return {
      $t,
      handleNext,
      handleFinish
    };
  }
});
</script>

<style scoped>

.wizard-navigation {
  display: flex;
  align-items: center;
  padding: 20px 28px;
  background: linear-gradient(120deg, rgba(99, 102, 241, 0.12), rgba(34, 211, 238, 0.1));
  border-top: 1px solid rgba(99, 102, 241, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
  flex-shrink: 0;
  gap: 16px;
}

.nav-spacer {
  flex: 1;
}


.nav-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 22px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  background: rgba(255, 255, 255, 0.65);
  color: var(--wizard-muted, #4b5563);
  box-shadow: 0 10px 18px rgba(99, 102, 241, 0.12);
}

.prev-btn {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(99, 102, 241, 0.18);
}

.prev-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(99, 102, 241, 0.18);
}

.next-btn {
  background: linear-gradient(135deg, var(--wizard-primary, #6366f1), var(--wizard-secondary, #8b5cf6));
  color: #ffffff;
}

.finish-btn {
  background: linear-gradient(135deg, var(--wizard-secondary, #8b5cf6), var(--wizard-accent, #22d3ee));
  color: #ffffff;
}

.next-btn:hover:not(:disabled),
.finish-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 14px 26px rgba(99, 102, 241, 0.28);
}

.nav-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.button-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* TMA optimized mobile styles */
@media (max-width: 768px) {
  .wizard-navigation {
    padding: 16px 20px;
  }
  
  .nav-btn {
    padding: 10px 18px;
    font-size: 13px;
    gap: 6px;
  }
}

@media (max-width: 480px) {
  .wizard-navigation {
    padding: 14px 16px;
  }
  
  .nav-btn {
    padding: 8px 14px;
    font-size: 12px;
  }
}
</style>