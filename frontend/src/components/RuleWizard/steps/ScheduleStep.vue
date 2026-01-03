<template>
  <div class="schedule-step">
    <div class="step-header">
      <h3>{{ $t('wizard_step_schedule_title') }}</h3>
      <p class="step-description">{{ $t('wizard_step_schedule_description') }}</p>
    </div>

    <div class="schedule-form">
      <div class="time-range-section">
        <h4>{{ $t('posting_delay_range') }}</h4>
        <div class="time-range-visual">
          <div class="time-input-group">
            <label for="hour_min">{{ $t('minimum_delay') }}</label>
            <div class="time-input-wrapper">
              <input 
                type="number"
                id="hour_min"
                :value="wizardData.hour_min"
                @input="updateHourMin"
                min="0"
                max="23"
                class="time-input"
              >
              <span class="time-unit">{{ $t('hours') }}</span>
            </div>
          </div>

          <div class="range-connector">
            <svg width="40" height="24" viewBox="0 0 40 24" fill="none" stroke="currentColor">
              <line x1="8" y1="12" x2="32" y2="12"/>
              <polyline points="28,8 32,12 28,16"/>
            </svg>
          </div>

          <div class="time-input-group">
            <label for="hour_max">{{ $t('maximum_delay') }}</label>
            <div class="time-input-wrapper">
              <input 
                type="number"
                id="hour_max"
                :value="wizardData.hour_max"
                @input="updateHourMax"
                min="0"
                max="23"
                class="time-input"
              >
              <span class="time-unit">{{ $t('hours') }}</span>
            </div>
          </div>
        </div>

        <div class="range-slider-section">
          <div class="slider-container">
            <input 
              type="range"
              :value="wizardData.hour_min"
              @input="updateHourMin"
              min="0"
              max="23"
              class="range-slider min-slider"
            >
            <input 
              type="range"
              :value="wizardData.hour_max"
              @input="updateHourMax"
              min="0"
              max="23"
              class="range-slider max-slider"
            >
          </div>
          <div class="slider-labels">
            <span>0h</span>
            <span>6h</span>
            <span>12h</span>
            <span>18h</span>
            <span>23h</span>
          </div>
        </div>
      </div>

      <div class="schedule-info">
        <div class="info-card">
          <div class="info-header">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12,6 12,12 16,14"/>
            </svg>
            <h4>{{ $t('how_scheduling_works') }}</h4>
          </div>
          <p>{{ $t('scheduling_explanation') }}</p>
        </div>

        <div class="current-settings">
          <h4>{{ $t('current_settings') }}</h4>
          <div class="settings-preview">
            <div class="setting-item">
              <span class="setting-label">{{ $t('delay_range') }}:</span>
              <span class="setting-value">{{ wizardData.hour_min }}h - {{ wizardData.hour_max }}h</span>
            </div>
            <div class="setting-item">
              <span class="setting-label">{{ $t('average_delay') }}:</span>
              <span class="setting-value">{{ averageDelay }}h</span>
            </div>
          </div>
        </div>
      </div>

      <div class="presets-section">
        <h4>{{ $t('schedule_presets') }}</h4>
        <div class="presets-grid">
          <div 
            v-for="preset in schedulePresets" 
            :key="preset.name"
            class="preset-card"
            :class="{ active: isPresetActive(preset) }"
            @click="applyPreset(preset)"
          >
            <div class="preset-header">
              <h5>{{ preset.name }}</h5>
              <span class="preset-range">{{ preset.hour_min }}h - {{ preset.hour_max }}h</span>
            </div>
            <p class="preset-description">{{ preset.description }}</p>
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
  name: 'ScheduleStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    }
  },
  emits: ['update-data'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();

    const schedulePresets = computed(() => [
      {
        name: $t('preset_immediate'),
        description: $t('preset_immediate_description'),
        hour_min: 0,
        hour_max: 1
      },
      {
        name: $t('preset_quick'),
        description: $t('preset_quick_description'),
        hour_min: 1,
        hour_max: 3
      },
      {
        name: $t('preset_standard'),
        description: $t('preset_standard_description'),
        hour_min: 3,
        hour_max: 8
      },
      {
        name: $t('preset_delayed'),
        description: $t('preset_delayed_description'),
        hour_min: 8,
        hour_max: 16
      },
      {
        name: $t('preset_daily'),
        description: $t('preset_daily_description'),
        hour_min: 20,
        hour_max: 23
      }
    ]);

    const averageDelay = computed(() => {
      const min = props.wizardData.hour_min || 0;
      const max = props.wizardData.hour_max || 0;
      return ((min + max) / 2).toFixed(1);
    });

    const updateHourMin = (event: Event) => {
      const target = event.target as HTMLInputElement;
      const value = parseInt(target.value);
      
      // Ensure min doesn't exceed max
      const maxValue = props.wizardData.hour_max || 23;
      const finalValue = Math.min(value, maxValue);
      
      emit('update-data', { hour_min: finalValue });
    };

    const updateHourMax = (event: Event) => {
      const target = event.target as HTMLInputElement;
      const value = parseInt(target.value);
      
      // Ensure max doesn't go below min
      const minValue = props.wizardData.hour_min || 0;
      const finalValue = Math.max(value, minValue);
      
      emit('update-data', { hour_max: finalValue });
    };

    const applyPreset = (preset: any) => {
      emit('update-data', {
        hour_min: preset.hour_min,
        hour_max: preset.hour_max
      });
    };

    const isPresetActive = (preset: any) => {
      return props.wizardData.hour_min === preset.hour_min && 
             props.wizardData.hour_max === preset.hour_max;
    };

    return {
      $t,
      schedulePresets,
      averageDelay,
      updateHourMin,
      updateHourMax,
      applyPreset,
      isPresetActive
    };
  }
});
</script>

<style scoped>
.schedule-step {
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

.schedule-form {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.time-range-section {
  background: #f8f9fa;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.time-range-section h4 {
  margin: 0 0 20px 0;
  color: #333;
  font-size: 18px;
}

.time-range-visual {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  margin-bottom: 30px;
}

.time-input-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.time-input-group label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.time-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
  padding: 8px 12px;
  border-radius: 6px;
  border: 2px solid #e0e0e0;
}

.time-input {
  border: none;
  outline: none;
  font-size: 18px;
  font-weight: 600;
  color: #333;
  width: 60px;
  text-align: center;
}

.time-unit {
  font-size: 14px;
  color: #666;
}

.range-connector {
  color: #007bff;
  margin-top: 20px;
}

.slider-container {
  position: relative;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  margin-bottom: 12px;
}

.range-slider {
  position: absolute;
  width: 100%;
  height: 6px;
  background: transparent;
  outline: none;
  -webkit-appearance: none;
}

.range-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #007bff;
  cursor: pointer;
  position: relative;
  z-index: 2;
}

.range-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #007bff;
  cursor: pointer;
  border: none;
  position: relative;
  z-index: 2;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

.schedule-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.info-card {
  background: #e3f2fd;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #bbdefb;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.info-header svg {
  color: #1976d2;
}

.info-header h4 {
  margin: 0;
  color: #1976d2;
  font-size: 16px;
}

.info-card p {
  margin: 0;
  font-size: 14px;
  color: #1565c0;
  line-height: 1.4;
}

.current-settings {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.current-settings h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
}

.settings-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.setting-label {
  font-size: 14px;
  color: #666;
}

.setting-value {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.presets-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 18px;
}

.presets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
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

.preset-range {
  font-size: 12px;
  color: #007bff;
  font-weight: 500;
}

.preset-description {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
  margin: 0;
}

@media (max-width: 768px) {
  .time-range-visual {
    flex-direction: column;
    gap: 16px;
  }
  
  .range-connector {
    transform: rotate(90deg);
    margin: 0;
  }
  
  .schedule-info {
    grid-template-columns: 1fr;
  }
}
</style>