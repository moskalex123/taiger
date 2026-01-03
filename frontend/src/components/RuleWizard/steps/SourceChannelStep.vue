<template>
  <div class="source-channel-step">
    <div class="step-header">
      <h3>{{ $t('wizard_step_source_title') }}</h3>
      <p class="step-description">{{ $t('wizard_step_source_description') }}</p>
    </div>

    <div class="channel-selection">
      <div class="channel-field">
        <label for="source_channel">
          <div class="label-with-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
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
          class="channel-select"
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
    </div>

    <div class="create-channel-section">
      <div class="section-divider">
        <span>{{ $t('or') }}</span>
      </div>
      
      <div class="create-channel-card">
        <div class="card-header">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="16"/>
            <line x1="8" y1="12" x2="16" y2="12"/>
          </svg>
          <h4>{{ $t('create_new_channel') }}</h4>
        </div>
        <p class="card-description">{{ $t('create_channel_wizard_description') }}</p>
        <button @click="toggleCreateForm" class="create-btn" type="button">
          {{ showCreateForm ? $t('cancel') : $t('create_channel') }}
        </button>
        
        <form v-if="showCreateForm" @submit.prevent="createChannel" class="create-form">
          <div class="form-group">
            <label for="channel_title">{{ $t('channel_title') }}</label>
            <input 
              type="text" 
              id="channel_title" 
              v-model="newChannel.title" 
              :placeholder="$t('channel_title_placeholder')"
              required
            >
          </div>
          
          <div class="form-group">
            <label for="channel_description">{{ $t('channel_description') }}</label>
            <textarea 
              id="channel_description" 
              v-model="newChannel.description"
              :placeholder="$t('channel_description_placeholder')"
              rows="3"
            ></textarea>
          </div>
          
          <div class="checkbox-group">
            <label class="checkbox-label">
              <input 
                type="checkbox" 
                v-model="newChannel.is_megagroup"
              >
              <span class="checkmark"></span>
              {{ $t('create_as_supergroup') }}
            </label>
          </div>
          
          <button type="submit" :disabled="creatingChannel || !newChannel.title.trim()" class="submit-btn">
            <div v-if="creatingChannel" class="button-spinner"></div>
            <span v-if="!creatingChannel">{{ $t('create_channel') }}</span>
            <span v-else>{{ $t('creating') }}...</span>
          </button>
        </form>
      </div>
    </div>

    <div v-if="wizardData.text_to_delete !== undefined" class="text-deletion-section">
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
import { defineComponent, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import axios from 'axios';

export default defineComponent({
  name: 'SourceChannelStep',
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
  emits: ['update-data', 'refresh-channels'],
  setup(_props, { emit }) {
    const { t: $t } = useI18n();
    
    const showCreateForm = ref(false);
    const creatingChannel = ref(false);
    const newChannel = ref({
      title: '',
      description: '',
      is_megagroup: false
    });

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

    const updateTextToDelete = (event: Event) => {
      const target = event.target as HTMLInputElement;
      emit('update-data', { text_to_delete: target.value });
    };

    const toggleCreateForm = () => {
      showCreateForm.value = !showCreateForm.value;
      if (!showCreateForm.value) {
        newChannel.value = {
          title: '',
          description: '',
          is_megagroup: false
        };
      }
    };

    const createChannel = async () => {
      if (creatingChannel.value) return;
      
      creatingChannel.value = true;
      try {
        // Support both cookie-based auth and token-based auth (for TMA)
        const token = localStorage.getItem('auth_token');
        const headers: any = {};
        
        if (token) {
          headers['Authorization'] = 'Bearer ' + token;
        }
        
        const response = await axios.post('/api/channel_pairs/create-channel', newChannel.value, {
          withCredentials: true,
          headers
        });
        
        if (response.data.status === 'success') {
          // Refresh channels list
          emit('refresh-channels');
          
          // Reset form
          showCreateForm.value = false;
          newChannel.value = {
            title: '',
            description: '',
            is_megagroup: false
          };
          
          // Show success message
          alert($t('channel_created_successfully') + ': ' + response.data.title);
        }
      } catch (error: unknown) {
        console.error('Error creating channel:', error instanceof Error ? error.message : String(error));
        alert($t('error_creating_channel'));
      } finally {
        creatingChannel.value = false;
      }
    };

    return {
      $t,
      showCreateForm,
      creatingChannel,
      newChannel,
      getChannelValue,
      updateSourceChannel,
      updateTextToDelete,
      toggleCreateForm,
      createChannel
    };
  }
});
</script>

<style scoped>
.source-channel-step {
  max-width: 600px;
  margin: 0 auto;
}

.step-header {
  text-align: center;
  margin-bottom: 40px;
}

.step-header h3 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 28px;
  font-weight: 600;
}

.step-description {
  color: #666;
  font-size: 16px;
  line-height: 1.6;
  margin: 0;
}

.channel-selection {
  margin-bottom: 40px;
}

.channel-field {
  display: flex;
  flex-direction: column;
}

.label-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
  font-size: 16px;
}

.channel-select {
  width: 100%;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 15px;
  transition: all 0.2s ease;
  background: white;
  color: #333;
}

.channel-select:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0, 123, 255, 0.1);
}

/* Темная тема для select */
.tma-dark-theme .channel-select,
.theme-dark .channel-select,
[data-theme="dark"] .channel-select {
  background: rgba(15, 23, 42, 0.95) !important;
  border-color: rgba(99, 102, 241, 0.4) !important;
  color: #f8fafc !important;
}

.tma-dark-theme .channel-select option,
.theme-dark .channel-select option,
[data-theme="dark"] .channel-select option {
  background: rgba(15, 23, 42, 0.98) !important;
  color: #f8fafc !important;
}

/* Светлая тема для select (убеждаемся, что читаемо) */
.channel-select option {
  background: white;
  color: #333;
}

.field-help {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #666;
  margin-top: 8px;
  line-height: 1.4;
}

.section-divider {
  text-align: center;
  margin: 30px 0;
  position: relative;
}

.section-divider::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  background: #e0e0e0;
}

.section-divider span {
  background: white;
  padding: 0 20px;
  color: #666;
  font-size: 14px;
  font-weight: 500;
}

.create-channel-card {
  background: #f8f9fa;
  border: 2px dashed #dee2e6;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  transition: all 0.2s ease;
}

.create-channel-card:hover {
  border-color: #007bff;
  background: #f0f7ff;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 12px;
}

.card-header svg {
  color: #007bff;
}

.card-header h4 {
  margin: 0;
  color: #333;
  font-size: 18px;
  font-weight: 600;
}

.card-description {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
  margin: 0 0 20px 0;
}

.create-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
}

.create-btn:hover {
  background: #0056b3;
}

.create-form {
  margin-top: 24px;
  text-align: left;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-weight: 500;
  color: #333;
  margin-bottom: 6px;
  font-size: 14px;
}

.form-group input,
.form-group textarea {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #007bff;
}

.checkbox-group {
  margin-bottom: 20px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #28a745;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
  width: 100%;
}

.submit-btn:hover:not(:disabled) {
  background: #1e7e34;
}

.submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.button-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top: 2px solid currentColor;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.text-deletion-section {
  background: #f8f9fa;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  margin-top: 30px;
}

.text-deletion-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 16px;
  font-weight: 600;
}

.field-group label {
  display: block;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
  font-size: 14px;
}

.field-group input {
  width: 100%;
  padding: 12px;
  border: 2px solid #e0e0e0;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s ease;
}

.field-group input:focus {
  outline: none;
  border-color: #007bff;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>