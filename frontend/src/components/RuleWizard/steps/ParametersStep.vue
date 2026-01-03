<template>
  <div class="parameters-step">
    <div class="step-header">
      <h3>{{ $t('wizard_step_parameters_title') }}</h3>
      <p class="step-description">{{ $t('wizard_step_parameters_description') }}</p>
    </div>

    <div v-if="!wizardData.model_id" class="no-ai-notice">
      <div class="notice-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <circle cx="12" cy="12" r="10"/>
          <line x1="12" y1="8" x2="12" y2="12"/>
          <line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </div>
      <div class="notice-content">
        <h4>{{ $t('no_ai_selected') }}</h4>
        <p>{{ $t('no_ai_parameters_notice') }}</p>
      </div>
    </div>

    <div v-else class="parameters-form">
      <div class="parameter-group">
        <div class="parameter-header">
          <label for="max_tokens">
            <div class="label-with-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14,2 14,8 20,8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
              </svg>
              {{ $t('max_tokens_label') }}
            </div>
          </label>
          <span class="parameter-value">{{ wizardData.max_tokens || 'Auto' }}</span>
        </div>
        <input 
          type="range"
          id="max_tokens"
          :value="wizardData.max_tokens || 100"
          @input="updateMaxTokens"
          min="50"
          max="5000"
          step="50"
          class="parameter-slider"
        >
        <div class="parameter-info">
          <div class="range-labels">
            <span>50</span>
            <span>5000</span>
          </div>
          <div class="parameter-help">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            {{ $t('max_tokens_help') }}
          </div>
        </div>
      </div>

      <div class="parameter-group">
        <div class="parameter-header">
          <label for="temperature">
            <div class="label-with-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/>
              </svg>
              {{ $t('temperature_label') }}
            </div>
          </label>
          <span class="parameter-value">{{ wizardData.temperature || 'Auto' }}</span>
        </div>
        <input 
          type="range"
          id="temperature"
          :value="wizardData.temperature || 0.7"
          @input="updateTemperature"
          min="0"
          max="2"
          step="0.1"
          class="parameter-slider"
        >
        <div class="parameter-info">
          <div class="range-labels">
            <span>{{ $t('conservative') }}</span>
            <span>{{ $t('creative') }}</span>
          </div>
          <div class="parameter-help">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            {{ $t('temperature_help') }}
          </div>
        </div>
      </div>

      <div class="parameter-group">
        <div class="parameter-header">
          <label for="top_p">
            <div class="label-with-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <polygon points="13,2 3,14 12,14 11,22 21,10 12,10 13,2"/>
              </svg>
              {{ $t('top_p_label') }}
            </div>
          </label>
          <span class="parameter-value">{{ wizardData.top_p || 'Auto' }}</span>
        </div>
        <input 
          type="range"
          id="top_p"
          :value="wizardData.top_p || 0.9"
          @input="updateTopP"
          min="0.1"
          max="1"
          step="0.1"
          class="parameter-slider"
        >
        <div class="parameter-info">
          <div class="range-labels">
            <span>{{ $t('focused') }}</span>
            <span>{{ $t('diverse') }}</span>
          </div>
          <div class="parameter-help">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            {{ $t('top_p_help') }}
          </div>
        </div>
      </div>

      <div class="presets-section">
        <h4>{{ $t('parameter_presets') }}</h4>
        <div class="presets-grid">
          <div 
            v-for="preset in parameterPresets" 
            :key="preset.name"
            class="preset-card"
            @click="applyPreset(preset)"
          >
            <div class="preset-header">
              <h5>{{ preset.name }}</h5>
              <button class="apply-preset-btn">{{ $t('apply') }}</button>
            </div>
            <p class="preset-description">{{ preset.description }}</p>
            <div class="preset-values">
              <span>{{ $t('temperature') }}: {{ preset.temperature }}</span>
              <span>{{ $t('top_p') }}: {{ preset.top_p }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'ParametersStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    }
  },
  emits: ['update-data'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();

    const parameterPresets = computed(() => [
      {
        name: $t('preset_balanced'),
        description: $t('preset_balanced_description'),
        temperature: 0.7,
        top_p: 0.9
      },
      {
        name: $t('preset_creative'),
        description: $t('preset_creative_description'),
        temperature: 1.2,
        top_p: 0.95
      },
      {
        name: $t('preset_precise'),
        description: $t('preset_precise_description'),
        temperature: 0.3,
        top_p: 0.7
      },
      {
        name: $t('preset_conservative'),
        description: $t('preset_conservative_description'),
        temperature: 0.1,
        top_p: 0.5
      }
    ]);

    const updateMaxTokens = (event: Event) => {
      const target = event.target as HTMLInputElement;
      emit('update-data', { max_tokens: parseInt(target.value) });
    };

    const updateTemperature = (event: Event) => {
      const target = event.target as HTMLInputElement;
      emit('update-data', { temperature: parseFloat(target.value) });
    };

    const updateTopP = (event: Event) => {
      const target = event.target as HTMLInputElement;
      emit('update-data', { top_p: parseFloat(target.value) });
    };

    const applyPreset = (preset: any) => {
      emit('update-data', {
        temperature: preset.temperature,
        top_p: preset.top_p
      });
    };

    return {
      $t,
      parameterPresets,
      updateMaxTokens,
      updateTemperature,
      updateTopP,
      applyPreset
    };
  }
});
</script>

<style scoped>
.parameters-step {
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

.no-ai-notice {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: #fff3cd;
  border: 1px solid #ffeaa7;
  border-radius: 8px;
  color: #856404;
}

.notice-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.notice-content h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
}

.notice-content p {
  margin: 0;
  font-size: 14px;
  line-height: 1.4;
}

.parameters-form {
  display: flex;
  flex-direction: column;
  gap: 40px;
}

.parameter-group {
  background: #f8f9fa;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.parameter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.label-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #333;
}

.parameter-value {
  font-size: 16px;
  font-weight: 600;
  color: #007bff;
  background: white;
  padding: 4px 12px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.parameter-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  background: #e0e0e0;
  outline: none;
  margin-bottom: 12px;
}

.parameter-slider::-webkit-slider-thumb {
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #007bff;
  cursor: pointer;
}

.parameter-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #007bff;
  cursor: pointer;
  border: none;
}

.parameter-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

.parameter-help {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.presets-section h4 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 18px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 16px;
}

.preset-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: white;
}

.preset-card:hover {
  border-color: #007bff;
  background: #f8f9ff;
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

.apply-preset-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.apply-preset-btn:hover {
  background: #0056b3;
}

.preset-description {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  margin: 0 0 8px 0;
}

.preset-values {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #888;
}
</style>