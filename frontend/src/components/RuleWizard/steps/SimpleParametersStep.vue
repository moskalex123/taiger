<template>
  <div class="simple-parameters-step">
    <h3>{{ $t('step_4_generation_parameters') }}</h3>
    
    <div v-if="!wizardData.model_id" style="background: #fff3cd; padding: 15px; border-radius: 8px; border: 1px solid #ffeaa7;">
      <p style="margin: 0;">{{ $t('no_ai_no_parameters') }}</p>
    </div>

    <div v-else>
      <p>{{ $t('configure_ai_parameters') }}</p>
      
      <div class="parameter-group" style="margin-bottom: 25px;">
        <label style="display: block; font-weight: bold; margin-bottom: 8px;">
          {{ $t('max_response_length', { value: wizardData.max_tokens || $t('auto') }) }}
        </label>
        <input 
          type="range"
          :value="wizardData.max_tokens || 100"
          @input="updateMaxTokens"
          min="50"
          max="5000"
          step="50"
          style="width: 100%; margin-bottom: 5px;"
        >
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #666;">
          <span>50 ({{ $t('short') }})</span>
          <span>5000 ({{ $t('long') }})</span>
        </div>
        <p style="font-size: 13px; color: #666; margin: 5px 0 0 0;">
          {{ $t('max_tokens_help') }}
        </p>
      </div>

      <div class="parameter-group" style="margin-bottom: 25px;">
        <label style="display: block; font-weight: bold; margin-bottom: 8px;">
          {{ $t('creativity', { value: wizardData.temperature || $t('auto') }) }}
        </label>
        <input 
          type="range"
          :value="wizardData.temperature || 0.7"
          @input="updateTemperature"
          min="0"
          max="2"
          step="0.1"
          style="width: 100%; margin-bottom: 5px;"
        >
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #666;">
          <span>0 ({{ $t('conservative') }})</span>
          <span>2 ({{ $t('creative') }})</span>
        </div>
        <p style="font-size: 13px; color: #666; margin: 5px 0 0 0;">
          {{ $t('creativity_help') }}
        </p>
      </div>

      <div class="parameter-group" style="margin-bottom: 25px;">
        <label style="display: block; font-weight: bold; margin-bottom: 8px;">
          {{ $t('diversity', { value: wizardData.top_p || $t('auto') }) }}
        </label>
        <input 
          type="range"
          :value="wizardData.top_p || 0.9"
          @input="updateTopP"
          min="0.1"
          max="1"
          step="0.1"
          style="width: 100%; margin-bottom: 5px;"
        >
        <div style="display: flex; justify-content: space-between; font-size: 12px; color: #666;">
          <span>0.1 ({{ $t('focused') }})</span>
          <span>1.0 ({{ $t('diverse') }})</span>
        </div>
        <p style="font-size: 13px; color: #666; margin: 5px 0 0 0;">
          {{ $t('diversity_help') }}
        </p>
      </div>

      <div style="background: #f0f7ff; padding: 15px; border-radius: 8px; margin-top: 20px;">
        <h4 style="margin: 0 0 10px 0;">{{ $t('quick_settings') }}</h4>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
          <button @click="applyPreset('balanced')" style="padding: 8px 16px; background: #6c757d; color: white; border: none; border-radius: 4px; cursor: pointer;">
            {{ $t('balanced') }}
          </button>
          <button @click="applyPreset('creative')" style="padding: 8px 16px; background: #17a2b8; color: white; border: none; border-radius: 4px; cursor: pointer;">
            {{ $t('creative') }}
          </button>
          <button @click="applyPreset('precise')" style="padding: 8px 16px; background: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">
            {{ $t('precise') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'SimpleParametersStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    }
  },
  emits: ['update-data'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();
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

    const applyPreset = (preset: string) => {
      const presets = {
        balanced: { temperature: 0.7, top_p: 0.9 },
        creative: { temperature: 1.2, top_p: 0.95 },
        precise: { temperature: 0.3, top_p: 0.7 }
      };
      
      const presetData = presets[preset];
      if (presetData) {
        emit('update-data', presetData);
      }
    };

    return {
      updateMaxTokens,
      updateTemperature,
      updateTopP,
      applyPreset,
      $t
    };
  }
});
</script>

<style scoped>
.simple-parameters-step {
  padding: 20px;
}

/* Мобильная оптимизация */
@media (max-width: 768px) {
  .simple-parameters-step {
    padding: 15px;
  }
  
  .simple-parameters-step h3 {
    font-size: 18px;
    margin-bottom: 10px;
  }
  
  .simple-parameters-step p {
    font-size: 14px;
    margin-bottom: 15px;
  }
  
  .simple-parameters-step h4 {
    font-size: 16px;
    margin-bottom: 8px;
  }
  
  .parameter-group {
    margin-bottom: 20px !important;
  }
  
  .parameter-group label {
    font-size: 13px !important;
    margin-bottom: 6px !important;
  }
  
  .parameter-group p {
    font-size: 11px !important;
    margin: 4px 0 0 0 !important;
  }
  
  .parameter-group div {
    font-size: 11px !important;
  }
  
  .simple-parameters-step button {
    font-size: 12px !important;
    padding: 6px 12px !important;
  }
}
</style>