<template>
  <div class="step-indicator">
    <div 
      v-for="(title, index) in stepTitles" 
      :key="index + 1"
      class="step-item"
      :class="{ 
        'active': currentStep === index + 1,
        'completed': currentStep > index + 1,
        'clickable': index + 1 <= currentStep
      }"
      @click="goToStep(index + 1)"
    >
      <div class="step-number">
        <span v-if="currentStep > index + 1" class="check-icon">✓</span>
        <span v-else>{{ index + 1 }}</span>
      </div>
      <div class="step-title">{{ title }}</div>
      <div v-if="index < stepTitles.length - 1" class="step-connector"></div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export default defineComponent({
  name: 'StepIndicator',
  props: {
    currentStep: {
      type: Number,
      required: true
    },
    totalSteps: {
      type: Number,
      required: true
    },
    stepTitles: {
      type: Array as () => string[],
      required: true
    }
  },
  emits: ['go-to-step'],
  setup(props, { emit }) {
    const goToStep = (step: number) => {
      if (step <= props.currentStep) {
        emit('go-to-step', step);
      }
    };

    return {
      goToStep
    };
  }
});
</script>

<style scoped>
.step-indicator {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 28px;
  background: linear-gradient(120deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
  border-bottom: 1px solid rgba(99, 102, 241, 0.15);
  overflow-x: auto;
  gap: 18px;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
}

.step-item.clickable {
  cursor: pointer;
}

.step-number {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 8px;
  transition: all 0.3s ease;
  font-size: 13px;
  background: rgba(99, 102, 241, 0.18);
  color: var(--wizard-muted, #6b7280);
  box-shadow: inset 0 0 0 1px rgba(99, 102, 241, 0.18);
}

.step-item.active .step-number {
  background: linear-gradient(135deg, var(--wizard-primary, #6366f1), var(--wizard-secondary, #8b5cf6));
  color: #ffffff;
  box-shadow: 0 10px 18px rgba(99, 102, 241, 0.35);
  transform: translateY(-2px);
}

.step-item.completed .step-number {
  background: linear-gradient(135deg, var(--wizard-secondary, #8b5cf6), var(--wizard-accent, #22d3ee));
  color: #ffffff;
  box-shadow: 0 8px 16px rgba(34, 211, 238, 0.25);
}

.step-title {
  font-size: 12px;
  text-align: center;
  color: var(--wizard-muted, #6b7280);
  max-width: 110px;
  line-height: 1.2;
}

.step-item.active .step-title {
  color: var(--wizard-primary, #6366f1);
  font-weight: 500;
}

.step-connector {
  position: absolute;
  top: 18px;
  left: calc(50% + 20px);
  right: -60px;
  height: 3px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.05));
  z-index: -1;
}

.step-item.completed .step-connector {
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.6), rgba(34, 211, 238, 0.6));
}

.check-icon {
  font-size: 14px;
}

/* TMA optimized mobile styles */
@media (max-width: 768px) {
  .step-indicator {
    padding: 16px;
    gap: 12px;
  }
  
  .step-number {
    width: 32px;
    height: 32px;
    font-size: 12px;
  }
  
  .step-item {
    min-width: 90px;
  }
  
  .step-title {
    font-size: 11px;
    max-width: 90px;
  }
  
  .step-connector {
    display: none;
  }
}

@media (max-width: 480px) {
  .step-indicator {
    padding: 12px;
    gap: 10px;
  }
  
  .step-number {
    width: 28px;
    height: 28px;
    font-size: 11px;
  }
  
  .step-item {
    min-width: 80px;
  }
  
  .step-title {
    font-size: 10px;
    max-width: 80px;
  }
}
</style>