<template>
  <div v-if="show" class="progress-overlay">
    <div class="progress-modal">
      <div class="progress-header">
        <h3>{{ title }}</h3>
      </div>
      
      <div class="progress-content">
        <div class="progress-steps">
          <div 
            v-for="(step, index) in steps" 
            :key="index"
            :class="['progress-step', getStepClass(index)]"
          >
            <div class="step-icon">
              <svg v-if="step.status === 'completed'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polyline points="20,6 9,17 4,12"/>
              </svg>
              <svg v-else-if="step.status === 'loading'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" class="spin">
                <path d="M21 12a9 9 0 11-6.219-8.56"/>
              </svg>
              <svg v-else-if="step.status === 'error'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
              <span v-else class="step-number">{{ index + 1 }}</span>
            </div>
            <div class="step-content">
              <div class="step-title">{{ step.title }}</div>
              <div v-if="step.description" class="step-description">{{ step.description }}</div>
            </div>
          </div>
        </div>
        
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercentage + '%' }"></div>
        </div>
        
        <div class="progress-text">
          {{ currentStepText }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'Создание правила...'
  },
  steps: {
    type: Array,
    required: true
  }
});

const progressPercentage = computed(() => {
  const completedSteps = props.steps.filter(step => step.status === 'completed').length;
  return Math.round((completedSteps / props.steps.length) * 100);
});

const currentStepText = computed(() => {
  const currentStep = props.steps.find(step => step.status === 'loading');
  if (currentStep) {
    return currentStep.title;
  }
  
  const completedSteps = props.steps.filter(step => step.status === 'completed').length;
  if (completedSteps === props.steps.length) {
    return 'Готово!';
  }
  
  return 'Ожидание...';
});

const getStepClass = (index) => {
  const step = props.steps[index];
  return {
    'step-completed': step.status === 'completed',
    'step-loading': step.status === 'loading',
    'step-error': step.status === 'error',
    'step-pending': step.status === 'pending'
  };
};
</script>

<style scoped>
.progress-overlay {
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
  animation: fadeIn 0.3s ease-out;
}

.progress-modal {
  background: white;
  border-radius: 12px;
  padding: 0;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.4);
  animation: slideIn 0.3s ease-out;
}

.progress-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid #e0e0e0;
}

.progress-header h3 {
  margin: 0;
  color: #333;
  font-size: 20px;
  font-weight: 600;
}

.progress-content {
  padding: 24px;
}

.progress-steps {
  margin-bottom: 24px;
}

.progress-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
  transition: all 0.3s ease;
}

.progress-step:last-child {
  margin-bottom: 0;
}

.step-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.step-pending .step-icon {
  background: #f8f9fa;
  color: #6c757d;
  border: 2px solid #dee2e6;
}

.step-loading .step-icon {
  background: #007bff;
  color: white;
  border: 2px solid #007bff;
}

.step-completed .step-icon {
  background: #28a745;
  color: white;
  border: 2px solid #28a745;
}

.step-error .step-icon {
  background: #dc3545;
  color: white;
  border: 2px solid #dc3545;
}

.step-content {
  flex: 1;
  min-width: 0;
}

.step-title {
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
  transition: color 0.3s ease;
}

.step-loading .step-title {
  color: #007bff;
}

.step-completed .step-title {
  color: #28a745;
}

.step-error .step-title {
  color: #dc3545;
}

.step-description {
  font-size: 14px;
  color: #6c757d;
  line-height: 1.4;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #007bff, #28a745);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.progress-text {
  text-align: center;
  color: #6c757d;
  font-size: 14px;
  font-weight: 500;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-50px) scale(0.9);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

/* Мобильная адаптация */
@media (max-width: 768px) {
  .progress-modal {
    width: 95%;
    margin: 20px;
  }
  
  .progress-header {
    padding: 20px 20px 12px;
  }
  
  .progress-header h3 {
    font-size: 18px;
  }
  
  .progress-content {
    padding: 20px;
  }
  
  .progress-step {
    gap: 10px;
    margin-bottom: 12px;
  }
  
  .step-icon {
    width: 28px;
    height: 28px;
    font-size: 12px;
  }
  
  .step-title {
    font-size: 14px;
  }
  
  .step-description {
    font-size: 13px;
  }
}
</style>