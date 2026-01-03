<template>
  <div class="simple-model-step">
    <h3>{{ $t('step_2_select_ai_model') }}</h3>
    <p>{{ $t('select_ai_model_description') }}</p>

    <div class="model-form">
      <!-- No AI Processing Option -->
      <div class="model-section">
        <h4>{{ $t('processing_options') }}</h4>
        <div class="model-options">
          <div 
            class="model-option"
            :class="{ selected: !wizardData.model_id }"
            @click="selectNoAI"
          >
            <div class="model-header">
              <div class="model-icon">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                  <line x1="9" y1="9" x2="15" y2="15"/>
                  <line x1="15" y1="9" x2="9" y2="15"/>
                </svg>
              </div>
              <div class="model-info">
                <h5>{{ $t('no_ai_processing') }}</h5>
                <p>{{ $t('messages_copied_as_is') }}</p>
              </div>
              <div class="model-price">
                <span class="price-free">{{ $t('free') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- AI Models Section -->
      <div class="model-section">
        <h4>{{ $t('ai_models') }}</h4>
        
        <!-- Model Categories -->
        <div class="model-categories">
          <div 
            v-for="category in modelCategories" 
            :key="category.key"
            class="category-tab"
            :class="{ active: selectedCategory === category.key }"
            @click="selectedCategory = category.key"
          >
            <svg width="16" height="16" :viewBox="category.iconViewBox" fill="currentColor">
              <path :d="category.iconPath"/>
            </svg>
            {{ category.name }}
          </div>
        </div>

        <!-- Models Grid -->
        <div class="models-grid">
          <div 
            v-for="model in filteredModels" 
            :key="model.id"
            class="model-card"
            :class="{ selected: wizardData.model_id === model.id }"
            @click="selectModel(model)"
          >
            <div class="model-header">
              <div class="model-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                  <path d="M12 2L2 7v10c0 5.55 3.84 10 9 11 5.16-1 9-5.45 9-11V7l-10-5z"/>
                  <path d="m8 12 2 2 4-4"/>
                </svg>
              </div>
              <div class="model-info">
                <h5>{{ model.model_visible_name || model.model }}</h5>
                <div class="model-meta">
                  <span class="provider-badge">{{ getProviderName(model.provider) }}</span>
                  <span v-if="model.api_price" class="cost-badge">{{ $t('cost_per_post', { cost: model.api_price.toFixed(3) }) }}</span>
                </div>
              </div>
              <div class="model-price">
                <span v-if="model.price_per_post" class="price">{{ model.price_per_post.toFixed(3) }}₽</span>
                <span v-else class="price-free">{{ $t('free') }}</span>
              </div>
            </div>
            
            <div class="model-details">
              <div class="detail-row">
                <span class="detail-label">{{ $t('max_tokens') }}:</span>
                <span class="detail-value">{{ model.max_tokens?.toLocaleString() || 'N/A' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ $t('temperature') }}:</span>
                <span class="detail-value">{{ model.temperature || '0.7' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ $t('top_p') }}:</span>
                <span class="detail-value">{{ model.top_p || '0.9' }}</span>
              </div>
            </div>

            <div v-if="wizardData.model_id === model.id" class="selected-indicator">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polyline points="20,6 9,17 4,12"/>
              </svg>
              {{ $t('selected') }}
            </div>
          </div>
        </div>
      </div>

      <!-- Model Presets -->
      <div class="presets-section">
        <h4>{{ $t('model_presets') }}</h4>
        <div class="presets-grid">
          <div 
            v-for="preset in modelPresets" 
            :key="preset.name"
            class="preset-card"
            :class="{ active: isPresetActive(preset) }"
            @click="applyPreset(preset)"
          >
            <div class="preset-header">
              <h5>{{ preset.name }}</h5>
              <span class="preset-category">{{ preset.category }}</span>
            </div>
            <p class="preset-description">{{ preset.description }}</p>
            <div class="preset-models">
              <span 
                v-for="modelId in preset.model_ids" 
                :key="modelId"
                class="model-tag"
              >
                {{ getModelName(modelId) }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Current Selection Info -->
      <div v-if="selectedModel" class="current-selection">
        <div class="selection-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12,6 12,12 16,14"/>
          </svg>
          <h4>{{ $t('current_selection') }}</h4>
        </div>
        <div class="selection-details">
          <div class="selection-model">
            <strong>{{ selectedModel.model_visible_name || selectedModel.model }}</strong>
            <span v-if="selectedModel.price_per_post" class="cost">
              {{ $t('cost_per_post', { cost: selectedModel.price_per_post.toFixed(3) }) }}
            </span>
          </div>
          <div class="selection-benefits">
            <div class="benefit-item">
              <span class="benefit-label">{{ $t('max_tokens') }}:</span>
              <span class="benefit-value">{{ selectedModel.max_tokens?.toLocaleString() || 'N/A' }}</span>
            </div>
            <div class="benefit-item">
              <span class="benefit-label">{{ $t('processing_speed') }}:</span>
              <span class="benefit-value">{{ getProcessingSpeed(selectedModel) }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { getDefaultSystemPrompt } from '@/utils/systemPrompt';

export default defineComponent({
  name: 'SimpleModelStep',
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
    const { t: $t } = useI18n();
    const selectedCategory = ref('all');

    const modelCategories = computed(() => [
      {
        key: 'all',
        name: $t('all_models'),
        iconViewBox: '0 0 24 24',
        iconPath: 'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z'
      },
      {
        key: 'fast',
        name: $t('fast_models'),
        iconViewBox: '0 0 24 24',
        iconPath: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z'
      },
      {
        key: 'quality',
        name: $t('quality_models'),
        iconViewBox: '0 0 24 24',
        iconPath: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z'
      },
      {
        key: 'free',
        name: $t('free_models'),
        iconViewBox: '0 0 24 24',
        iconPath: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z'
      }
    ]);

    const modelPresets = computed(() => [
      {
        name: $t('preset_fast_processing'),
        description: $t('preset_fast_processing_desc'),
        category: $t('efficiency'),
        model_ids: [1, 2, 3]
      },
      {
        name: $t('preset_high_quality'),
        description: $t('preset_high_quality_desc'),
        category: $t('quality'),
        model_ids: [10, 11, 12]
      },
      {
        name: $t('preset_balanced'),
        description: $t('preset_balanced_desc'),
        category: $t('balance'),
        model_ids: [5, 6, 7]
      },
      {
        name: $t('preset_free_only'),
        description: $t('preset_free_only_desc'),
        category: $t('economy'),
        model_ids: [20, 21, 22]
      }
    ]);

    const filteredModels = computed(() => {
      if (selectedCategory.value === 'all') {
        return props.models;
      } else if (selectedCategory.value === 'fast') {
        return props.models.filter((m: any) => m.max_tokens && m.max_tokens < 4000);
      } else if (selectedCategory.value === 'quality') {
        return props.models.filter((m: any) => m.max_tokens && m.max_tokens >= 8000);
      } else if (selectedCategory.value === 'free') {
        return props.models.filter((m: any) => !m.price_per_post || m.price_per_post === 0);
      }
      return props.models;
    });

    const selectedModel = computed(() => {
      if (!props.wizardData.model_id) return null;
      return props.models.find((m: any) => m.id === props.wizardData.model_id);
    });

    const getProviderName = (provider: number) => {
      const providers: Record<number, string> = {
        0: $t('default_provider'),
        1: 'OpenRouter',
        2: 'Hyperbolic',
        3: 'Anthropic'
      };
      return providers[provider] || $t('unknown_provider');
    };

    const getModelName = (modelId: number) => {
      const model = props.models.find((m: any) => m.id === modelId);
      return model ? (model.model_visible_name || model.model) : `ID:${modelId}`;
    };

    const getProcessingSpeed = (model: any) => {
      if (!model.max_tokens) return $t('unknown');
      if (model.max_tokens < 4000) return $t('very_fast');
      if (model.max_tokens < 8000) return $t('fast');
      if (model.max_tokens < 16000) return $t('medium');
      return $t('slow');
    };

    const selectNoAI = async () => {
      emit('update-data', {
        model_id: null,
        system_content: '',
        max_tokens: null,
        temperature: null,
        top_p: null
      });
    };

    const selectModel = async (model: any) => {
      const defaultSystemPrompt = await getDefaultSystemPrompt('ru');
      emit('update-data', {
        model_id: model.id,
        system_content: defaultSystemPrompt,
        max_tokens: model.max_tokens,
        temperature: model.temperature,
        top_p: model.top_p
      });
    };

    const applyPreset = (preset: any) => {
      // Apply the first model from the preset
      if (preset.model_ids.length > 0) {
        const model = props.models.find((m: any) => m.id === preset.model_ids[0]);
        if (model) {
          selectModel(model);
        }
      }
    };

    const isPresetActive = (preset: any) => {
      if (!props.wizardData.model_id) return false;
      return preset.model_ids.includes(props.wizardData.model_id);
    };

    return {
      selectedCategory,
      modelCategories,
      modelPresets,
      filteredModels,
      selectedModel,
      getProviderName,
      getModelName,
      getProcessingSpeed,
      selectNoAI,
      selectModel,
      applyPreset,
      isPresetActive,
      $t
    };
  }
});
</script>

<style scoped>
.simple-model-step {
  padding: 20px;
}

.simple-model-step h3 {
  text-align: center;
  margin-bottom: 8px;
  font-size: 24px;
  color: #333;
}

.simple-model-step > p {
  text-align: center;
  margin-bottom: 30px;
  color: #666;
  font-size: 16px;
}

.model-form {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.model-section {
  background: #f8f9fa;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.model-section h4 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 18px;
  text-align: center;
}

.model-options {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-option {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.model-option:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.model-option.selected {
  border-color: #007bff;
  background: #f0f7ff;
}

.model-header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.model-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background: #e3f2fd;
  color: #1976d2;
  flex-shrink: 0;
}

.model-info {
  flex: 1;
}

.model-info h5 {
  margin: 0 0 4px 0;
  color: #333;
  font-size: 16px;
  font-weight: 500;
}

.model-info p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.model-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.provider-badge, .cost-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.provider-badge {
  background: #e8f5e8;
  color: #2e7d32;
}

.cost-badge {
  background: #fff3e0;
  color: #f57c00;
}

.model-price {
  display: flex;
  align-items: center;
}

.price {
  font-size: 16px;
  font-weight: 600;
  color: #1976d2;
}

.price-free {
  font-size: 14px;
  font-weight: 500;
  color: #4caf50;
}

.model-categories {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.category-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border-radius: 20px;
  background: white;
  border: 1px solid #e0e0e0;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
  color: #666;
}

.category-tab:hover {
  border-color: #007bff;
  color: #007bff;
}

.category-tab.active {
  background: #007bff;
  border-color: #007bff;
  color: white;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.model-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
  position: relative;
}

.model-card:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.model-card.selected {
  border-color: #007bff;
  background: #f0f7ff;
}

.model-details {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e0e0e0;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 14px;
}

.detail-label {
  color: #666;
}

.detail-value {
  color: #333;
  font-weight: 500;
}

.selected-indicator {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  background: #4caf50;
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.presets-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 18px;
  text-align: center;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}

.preset-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.preset-card:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.preset-card.active {
  border-color: #007bff;
  background: #f0f7ff;
}

.preset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.preset-header h5 {
  margin: 0;
  color: #333;
  font-size: 14px;
  font-weight: 500;
}

.preset-category {
  font-size: 12px;
  color: #007bff;
  font-weight: 500;
}

.preset-description {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  margin: 0 0 12px 0;
}

.preset-models {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.model-tag {
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.current-selection {
  background: #e8f5e8;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #c8e6c9;
}

.selection-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  color: #2e7d32;
}

.selection-header h4 {
  margin: 0;
  font-size: 16px;
}

.selection-model {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  font-size: 16px;
}

.selection-benefits {
  display: flex;
  gap: 20px;
}

.benefit-item {
  display: flex;
  gap: 8px;
}

.benefit-label {
  color: #2e7d32;
  font-size: 14px;
}

.benefit-value {
  color: #1b5e20;
  font-weight: 500;
  font-size: 14px;
}

.cost {
  color: #f57c00;
  font-weight: 600;
}

/* Mobile optimization */
@media (max-width: 768px) {
  .simple-model-step {
    padding: 15px;
  }
  
  .model-categories {
    justify-content: center;
  }
  
  .category-tab {
    font-size: 12px;
    padding: 6px 10px;
  }
  
  .models-grid {
    grid-template-columns: 1fr;
  }
  
  .presets-grid {
    grid-template-columns: 1fr;
  }
  
  .selection-benefits {
    flex-direction: column;
    gap: 8px;
  }
}
</style>
