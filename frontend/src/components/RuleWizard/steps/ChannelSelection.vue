<template>
  <div class="channel-selection-step">
    <div class="step-header">
      <h3>{{ $t('wizard_step_channels_title') }}</h3>
      <p class="step-description">{{ $t('wizard_step_channels_description') }}</p>
    </div>

    <div class="channel-fields">
      <div class="channel-field">
        <label for="source_channel">
          <div class="label-with-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10,9 9,9 8,9"/>
            </svg>
            {{ $t('source_channel_label') }}
          </div>
        </label>
        <select 
          id="source_channel" 
          :value="wizardData.source_channel" 
          @change="updateSourceChannel"
          required
        >
          <option value="">{{ $t('select_draft_channel') }}</option>
          <option 
            v-for="channel in channels.subscribed" 
            :key="channel.id" 
            :value="getChannelValue(channel)"
          >
            {{ channel.title }} {{ channel.username ? `(@${channel.username})` : `(ID: ${channel.id})` }}
          </option>
        </select>
        <div class="field-help">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ $t('source_channel_help') }}
        </div>
      </div>

      <div class="channel-arrow">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path d="M5 12h14m-7-7 7 7-7 7"/>
        </svg>
      </div>

      <div class="channel-field">
        <label for="target_channel">
          <div class="label-with-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <polyline points="10,13 12,15 16,11"/>
            </svg>
            {{ $t('target_channel_label') }}
          </div>
        </label>
        <select 
          id="target_channel" 
          :value="wizardData.target_channel" 
          @change="updateTargetChannel"
          required
        >
          <option value="">{{ $t('select_clean_channel') }}</option>
          <option 
            v-for="channel in channels.admin" 
            :key="channel.id" 
            :value="getChannelValue(channel)"
          >
            {{ channel.title }} {{ channel.username ? `(@${channel.username})` : `(ID: ${channel.id})` }}
          </option>
        </select>
        <div class="field-help">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ $t('target_channel_help') }}
        </div>
      </div>
    </div>

    <div class="text-deletion-section">
      <h4>{{ $t('text_deletion_title') }}</h4>
      <div class="field-group">
        <label for="text_to_delete">{{ $t('text_to_delete_label') }}</label>
        <input 
          type="text" 
          id="text_to_delete" 
          :value="wizardData.text_to_delete"
          @input="updateTextToDelete"
          :placeholder="$t('text_to_delete_placeholder')"
        >
        <div class="field-help">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ $t('text_to_delete_help') }}
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'ChannelSelection',
  props: {
    wizardData: {
      type: Object,
      required: true
    },
    channels: {
      type: Object,
      required: true
    }
  },
  emits: ['update-data'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();

    const getChannelValue = (channel: any): string => {
      if (channel.username) {
        return channel.username.startsWith('@') ? channel.username : `@${channel.username}`;
      }
      return channel.id.toString();
    };

    const updateSourceChannel = (event: Event) => {
      const target = event.target as HTMLSelectElement;
      emit('update-data', { source_channel: target.value || null });
    };

    const updateTargetChannel = (event: Event) => {
      const target = event.target as HTMLSelectElement;
      emit('update-data', { target_channel: target.value || null });
    };

    const updateTextToDelete = (event: Event) => {
      const target = event.target as HTMLInputElement;
      emit('update-data', { text_to_delete: target.value });
    };

    return {
      $t,
      getChannelValue,
      updateSourceChannel,
      updateTargetChannel,
      updateTextToDelete
    };
  }
});
</script>

<style scoped>
.channel-selection-step {
  max-width: 600px;
  margin: 0 auto;
}

.step-header {
  text-align: center;
  margin-bottom: 40px;
}

.step-header h3 {
  margin: 0 0 12px 0;
  color: var(--tg-theme-text-color, var(--text-primary, #333));
  font-size: 20px;
}

.step-description {
  color: var(--tg-theme-hint-color, var(--text-secondary, #666));
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
}

.channel-fields {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 40px;
}

.channel-field {
  flex: 1;
}

.label-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--tg-theme-text-color, var(--text-primary, #333));
  margin-bottom: 8px;
  font-size: 14px;
}

.channel-field select {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--tg-theme-section-separator-color, var(--border-primary, #e0e0e0));
  border-radius: 6px;
  font-size: 14px;
  background: var(--tg-theme-bg-color, var(--bg-primary, white));
  color: var(--tg-theme-text-color, var(--text-primary, #333));
  transition: border-color 0.2s ease;
}

.channel-field select:focus {
  outline: none;
  border-color: var(--tg-theme-button-color, var(--primary, #007bff));
}

.tma-dark-theme .channel-field select,
.theme-dark .channel-field select,
[data-theme="dark"] .channel-field select {
  background: rgba(15, 23, 42, 0.95) !important;
  border: 1px solid rgba(99, 102, 241, 0.4) !important;
  color: #f8fafc !important;
}

.tma-dark-theme .channel-field select option,
.theme-dark .channel-field select option,
[data-theme="dark"] .channel-field select option {
  background: rgba(15, 23, 42, 0.98) !important;
  color: #f8fafc !important;
}

/* Светлая тема - убеждаемся, что читаемо */
.channel-field select option {
  background: white;
  color: #1f2937;
}

.field-group input:focus {
  outline: none;
  border-color: var(--tg-theme-button-color, var(--primary, #007bff));
}

.channel-arrow {
  color: var(--tg-theme-button-color, var(--primary, #007bff));
  margin-top: 20px;
}

.field-help {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--tg-theme-hint-color, var(--text-secondary, #666));
  margin-top: 6px;
  line-height: 1.4;
}

.text-deletion-section {
  background: var(--tg-theme-secondary-bg-color, var(--bg-secondary, #f8f9fa));
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--tg-theme-section-separator-color, var(--border-primary, #e9ecef));
}

.text-deletion-section h4 {
  margin: 0 0 12px 0;
  color: var(--tg-theme-text-color, var(--text-primary, #333));
  font-size: 16px;
}

.field-group label {
  display: block;
  font-weight: 500;
  color: var(--tg-theme-text-color, var(--text-primary, #333));
  margin-bottom: 6px;
  font-size: 14px;
}

.field-group input {
  width: 100%;
  padding: 10px;
  border: 1px solid var(--tg-theme-section-separator-color, var(--border-primary, #e0e0e0));
  border-radius: 6px;
  font-size: 14px;
  background: var(--tg-theme-bg-color, var(--bg-primary, white));
  color: var(--tg-theme-text-color, var(--text-primary, #333));
  transition: border-color 0.2s ease;
}

.field-group input:focus {
  outline: none;
  border-color: var(--tg-theme-button-color, var(--primary, #007bff));
}

/* TMA optimized mobile styles */
@media (max-width: 768px) {
  .step-header {
    margin-bottom: 24px;
  }
  
  .step-header h3 {
    font-size: 18px;
  }
  
  .step-description {
    font-size: 13px;
  }
  
  .channel-fields {
    flex-direction: column;
    gap: 12px;
    margin-bottom: 24px;
  }
  
  .channel-arrow {
    transform: rotate(90deg);
    margin: 0;
  }
  
  .text-deletion-section {
    padding: 12px;
  }
  
  .text-deletion-section h4 {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .step-header h3 {
    font-size: 16px;
  }
  
  .step-description {
    font-size: 12px;
  }
  
  .channel-fields {
    gap: 8px;
    margin-bottom: 16px;
  }
  
  .label-with-icon {
    font-size: 13px;
  }
  
  .field-help {
    font-size: 10px;
  }
}
</style>