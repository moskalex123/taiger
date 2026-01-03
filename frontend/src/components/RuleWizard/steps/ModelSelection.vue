<template>
  <div class="model-selection-step">
    <div class="step-header">
      <h3>{{ $t('wizard_step_model_title') }}</h3>
      <p class="step-description">{{ $t('wizard_step_model_description') }}</p>
    </div>

    <div class="model-options">
      <div 
        class="model-option no-ai"
        :class="{ selected: !wizardData.model_id }"
        @click="selectNoAI"
      >
        <div class="option-header">
          <div class="option-radio">
            <div v-if="!wizardData.model_id" class="radio-selected"></div>
          </div>
          <div class="option-title">
            <h4>{{ $t('no_ai_processing') }}</h4>
            <span class="option-price">{{ $t('free') }}</span>
          </div>
        </div>
        <p class="option-description">{{ $t('no_ai_processing_description') }}</p>
      </div>

      <div 
        v-for="model in models" 
        :key="model.id"
        class="model-option"
        :class="{ selected: wizardData.model_id === model.id }"
        @click="selectModel(model)"
      >
        <div class="option-header">
          <div class="option-radio">
            <div v-if="wizardData.model_id === model.id" class="radio-selected"></div>
          </div>
          <div class="option-title">
            <h4>{{ model.model_visible_name || model.model }}</h4>
            <span class="option-price">{{ model.api_price !== null ? `🔋${model.api_price}` : '' }}</span>
          </div>
        </div>
        <p class="option-description">{{ getModelDescription(model) }}</p>
        
        <div v-if="model.system_content" class="model-preview">
          <div class="preview-label">{{ $t('default_instructions') }}:</div>
          <div class="preview-content">{{ model.system_content }}</div>
        </div>
      </div>
    </div>

    <div v-if="selectedModel" class="model-info">
      <h4>{{ $t('selected_model_info') }}</h4>
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">{{ $t('model_name') }}:</span>
          <span class="info-value">{{ selectedModel.model }}</span>
        </div>
        <div class="info-item">
          <span class="info-label">{{ $t('cost_per_post') }}:</span>
          <span class="info-value">${{ (selectedModel.price_per_post || 0).toFixed(3) }}</span>
        </div>
        <div v-if="selectedModel.max_tokens" class="info-item">
          <span class="info-label">{{ $t('default_max_tokens') }}:</span>
          <span class="info-value">{{ selectedModel.max_tokens }}</span>
        </div>
        <div v-if="selectedModel.temperature" class="info-item">
          <span class="info-label">{{ $t('default_temperature') }}:</span>
          <span class="info-value">{{ selectedModel.temperature }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { getDefaultSystemPrompt } from '@/utils/systemPrompt'; // Add this line

export default defineComponent({
  name: 'ModelSelectionStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    },
    models: {
      type: Array,
      required: true
    }
  },
  emits: ['update-data'],
  setup(props, { emit }) {
    const { t: $t, locale } = useI18n();

    const selectedModel = computed(() => {
      if (!props.wizardData.model_id) return null;
      return props.models.find((m: any) => m.id === props.wizardData.model_id);
    });

    const selectNoAI = () => {
      emit('update-data', {
        model_id: null,
        system_content: '',
        max_tokens: null,
        temperature: null,
        top_p: null
      });
    };

    const selectModel = async (model: any) => {
      // Get default system prompt from project settings
      const defaultSystemPrompt = await getDefaultSystemPrompt(locale.value);
      
      emit('update-data', {
        model_id: model.id,
        system_content: defaultSystemPrompt, // Use project settings instead of model.system_content
        max_tokens: model.max_tokens,
        temperature: model.temperature,
        top_p: model.top_p
      });
    };

    const getModelDescription = (model: any) => {
      // Можно добавить описания для разных моделей
      if (model.model.includes('gpt-4')) {
        return $t('gpt4_description');
      } else if (model.model.includes('gpt-3.5')) {
        return $t('gpt35_description');
      } else if (model.model.includes('claude')) {
        return $t('claude_description');
      }
      return $t('ai_model_generic_description');
    };

    return {
      $t,
      selectedModel,
      selectNoAI,
      selectModel,
      getModelDescription
    };
  }
});
</script>

<style scoped>
.model-selection-step {
  max-width: 700px;
  margin: 0 auto;
}

.step-header {
  text-align: center;
  margin-bottom: 40px;
}

.step-header h3 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 24px;
}

.step-description {
  color: #666;
  font-size: 16px;
  line-height: 1.5;
  margin: 0;
}

.model-options {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 30px;
}

.model-option {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.model-option:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.model-option.selected {
  border-color: #007bff;
  background: #f0f7ff;
}

.model-option.no-ai.selected {
  border-color: #28a745;
  background: #f0fff4;
}

.option-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.option-radio {
  width: 20px;
  height: 20px;
  border: 2px solid #ccc;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.model-option.selected .option-radio {
  border-color: #007bff;
}

.model-option.no-ai.selected .option-radio {
  border-color: #28a745;
}

.radio-selected {
  width: 10px;
  height: 10px;
  background: #007bff;
  border-radius: 50%;
}

.model-option.no-ai.selected .radio-selected {
  background: #28a745;
}

.option-title {
  flex: 1;
}

.option-title h4 {
  margin: 0 0 4px 0;
  color: #333;
  font-size: 18px;
}

.option-price {
  color: #666;
  font-size: 14px;
  font-weight: 500;
}

.option-description {
  color: #666;
  font-size: 14px;
  line-height: 1.4;
  margin: 0;
}

.model-preview {
  margin-top: 16px;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 4px;
  border-left: 3px solid #007bff;
}

.preview-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
  font-weight: 500;
}

.preview-content {
  font-size: 13px;
  color: #333;
  line-height: 1.4;
}

.model-info {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.model-info h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.info-label {
  font-size: 14px;
  color: #666;
}

.info-value {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}
</style>
