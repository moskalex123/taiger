<template>
  <div class="simple-source-step">
    <h3>{{ $t('step_1_create_draft_channel') }}</h3>
    
    <div class="step-description">
      <p>{{ $t('draft_channel_explanation_1') }}</p>
      <p>{{ $t('draft_channel_explanation_2') }}</p>
      <p><strong>{{ $t('draft_channel_name_instruction') }}</strong></p>
      

    </div>
    
    <div v-if="!showExistingChannels" class="create-channel-form">
      <div class="form-group">
        <input 
          id="channel-name"
          v-model="newChannel.title"
          type="text" 
          class="channel-name-input"
          :placeholder="$t('draft_channel_default_name')"
          required
          @input="validateChannelName"
        >
        <div v-if="channelNameError" class="error-message">
          {{ channelNameError }}
        </div>
      </div>
    </div>

    <!-- Альтернативный вариант для опытных пользователей -->
    <div class="alternative-option">
      <button @click="toggleExistingChannelMode" class="link-button">
        {{ showExistingChannels ? $t('back_to_create_channel') : $t('i_already_have_draft_channel') }}
      </button>
    </div>

    <div v-if="showExistingChannels" class="existing-channels-section">
      <div class="form-group">
        <label>{{ $t('select_existing_draft_channel') }}:</label>
        
        <!-- Loading indicator -->
        <div v-if="loadingChannels" class="channels-loading">
          <div class="loading-spinner"></div>
          <span>{{ $t('loading_channels') || 'Загружаем каналы...' }} <span v-if="loadedChannelsCount > 0">({{ loadedChannelsCount }})</span></span>
        </div>
        
        <!-- Channel select -->
        <select 
          v-else
          :value="wizardData.source_channel" 
          @change="updateSourceChannel"
          class="channel-select"
        >
          <option value="">{{ $t('select_channel') }}</option>
          <option 
            v-for="channel in channels.subscribed" 
            :key="channel.id" 
            :value="getChannelValue(channel)"
          >
            {{ channel.title }} {{ channel.username ? `(@${channel.username})` : `(ID: ${channel.id})` }}
          </option>
        </select>
        
        <div v-if="!loadingChannels && (!channels.subscribed || !Array.isArray(channels.subscribed) || channels.subscribed.length === 0)" class="no-channels-message">
          <p>{{ $t('no_subscribed_channels_found') }}</p>
          <p><small>{{ $t('create_channel_first_or_subscribe') }}</small></p>
        </div>
      </div>
    </div>

    <!-- Индикатор создания канала -->
    <div v-if="creatingChannel" class="creating-indicator">
      <div class="spinner"></div>
      <span>{{ $t('creating_channel') }}...</span>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, onMounted, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import axios from 'axios';

export default defineComponent({
  name: 'SimpleSourceStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    },
    channels: {
      type: Object,
      required: true
    },
    loadingChannels: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update-data', 'refresh-channels', 'next'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();
    
    const showExistingChannels = ref(false);
    const creatingChannel = ref(false);
    const channelNameError = ref('');
    const newChannel = ref({
      title: 'Черновик',
      description: '',
      is_megagroup: false
    });
    
    // Счетчик загруженных каналов
    const loadedChannelsCount = ref(0);
    const totalChannelsCount = ref(0);
    
    // Вычисляем количество загруженных каналов при изменении props.channels
    watch(() => props.channels, (newChannels) => {
      if (newChannels && newChannels.subscribed && Array.isArray(newChannels.subscribed)) {
        loadedChannelsCount.value = newChannels.subscribed.length;
        totalChannelsCount.value = newChannels.subscribed.length;
      }
    }, { immediate: true });

    // Инициализация - устанавливаем значение по умолчанию
    onMounted(() => {
      // Если у пользователя нет каналов, сразу показываем форму создания
      if (!props.channels.subscribed || !Array.isArray(props.channels.subscribed) || props.channels.subscribed.length === 0) {
        showExistingChannels.value = false;
      }
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

    const validateChannelName = () => {
      const name = newChannel.value.title.trim();
      if (!name) {
        channelNameError.value = $t('channel_name_required');
        return false;
      }
      if (name.length < 2) {
        channelNameError.value = $t('channel_name_too_short');
        return false;
      }
      if (name.length > 64) {
        channelNameError.value = $t('channel_name_too_long');
        return false;
      }
      channelNameError.value = '';
      return true;
    };

    const toggleExistingChannelMode = () => {
      showExistingChannels.value = !showExistingChannels.value;
      if (!showExistingChannels.value) {
        // Возвращаемся к созданию канала - очищаем выбранный канал
        emit('update-data', { source_channel: null });
      } else {
        // Переключаемся в режим выбора существующих каналов - загружаем каналы
        emit('refresh-channels');
      }
    };

    // Function to stop worker
    const stopWorker = async () => {
      try {
        // Support both cookie-based auth and token-based auth (for TMA)
        const token = localStorage.getItem('auth_token');
        const headers: any = {};
        
        if (token) {
          headers['Authorization'] = 'Bearer ' + token;
        }
        
        const response = await axios.post('/api/worker/stop', {}, {
          withCredentials: true,
          headers
        });
        console.log('Worker stopped:', response.data);
      } catch (error) {
        console.error('Error stopping worker:', error);
        // Don't throw error - channel creation should continue even if worker stop fails
      }
    };

    const createChannelAndProceed = async () => {
      console.log('createChannelAndProceed called', {
        isValid: validateChannelName(),
        isCreating: creatingChannel.value,
        channelData: newChannel.value
      });
      
      if (!validateChannelName() || creatingChannel.value) {
        console.log('Validation failed or already creating, returning');
        return;
      }
      
      creatingChannel.value = true;
      try {
        // Stop worker before creating channel to avoid session conflicts
        console.log('Stopping worker before channel creation...');
        await stopWorker();
        console.log('Worker stopped successfully');
        
        // Small delay to ensure worker is fully stopped
        await new Promise(resolve => setTimeout(resolve, 1000));
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
          // Обновляем список каналов
          emit('refresh-channels');
          
          // Устанавливаем созданный канал как источник
          const createdChannelValue = response.data.username ? 
            (response.data.username.startsWith('@') ? response.data.username : `@${response.data.username}`) :
            response.data.id.toString();
          
          emit('update-data', { source_channel: createdChannelValue });
          
          // Автоматически переходим к следующему шагу
          setTimeout(() => {
            emit('next');
          }, 500);
          
        } else {
          throw new Error(response.data.message || 'Unknown error');
        }
      } catch (error: unknown) {
        console.error('Error creating channel:', error instanceof Error ? error.message : String(error));
        
        let errorMessage = $t('error_creating_channel');
        
        if (error && typeof error === 'object' && 'response' in error) {
          const errorObj = error as { response?: { status: number, data: any } };
          const status = errorObj.response?.status;
          const data = errorObj.response?.data;
          
          if (data && data.detail) {
            errorMessage = `${$t('error_creating_channel')}: ${data.detail}`;
          } else if (data && data.message) {
            errorMessage = `${$t('error_creating_channel')}: ${data.message}`;
          } else {
            errorMessage = `${$t('error_creating_channel')} (${status})`;
          }
        } else if (error && typeof error === 'object' && 'request' in error) {
          errorMessage = `${$t('error_creating_channel')}: Ошибка сети`;
        } else {
          errorMessage = `${$t('error_creating_channel')}: ${error instanceof Error ? error.message : String(error)}`;
        }
        
        channelNameError.value = errorMessage;
      } finally {
        creatingChannel.value = false;
      }
    };

    // Переопределяем логику кнопки "Далее" в родительском компоненте
    const canProceed = () => {
      if (showExistingChannels.value) {
        return !!props.wizardData.source_channel;
      } else {
        return validateChannelName() && !creatingChannel.value;
      }
    };

    const handleNext = () => {
      console.log('SimpleSourceStep handleNext called', {
        showExistingChannels: showExistingChannels.value,
        sourceChannel: props.wizardData.source_channel,
        newChannelTitle: newChannel.value.title
      });

      if (showExistingChannels.value) {
        // Если выбран существующий канал, просто завершаем обработку
        console.log('Using existing channel, wizard will advance step');
      } else {
        // Если создаем новый канал, сохраняем данные для создания позже
        if (!validateChannelName()) {
          console.log('Validation failed, returning');
          return;
        }

        console.log('Saving source channel data for later creation...');
        const sourceChannelName = newChannel.value.title.trim();
        emit('update-data', {
          source_channel_data: {
            title: sourceChannelName,
            description: newChannel.value.description || `Канал-черновик для ${sourceChannelName}`,
            is_megagroup: newChannel.value.is_megagroup || false
          }
        });

        // Данные сохранены, wizard сам перейдет к следующему шагу
      }
    };

    return {
      showExistingChannels,
      creatingChannel,
      channelNameError,
      newChannel,
      getChannelValue,
      updateSourceChannel,
      validateChannelName,
      toggleExistingChannelMode,
      createChannelAndProceed,
      canProceed,
      handleNext,
      $t,
      loadedChannelsCount,
      totalChannelsCount
    };
  }
});
</script>

<style scoped>
.simple-source-step {
  padding: 28px;
  background: rgba(255, 255, 255, 0.82);
  border-radius: 18px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  box-shadow: 0 18px 40px rgba(99, 102, 241, 0.12);
  position: relative;
}

.simple-source-step::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(140deg, rgba(99, 102, 241, 0.12), rgba(34, 211, 238, 0.08));
  opacity: 0.85;
  z-index: -1;
  pointer-events: none;
}

.simple-source-step h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 18px;
  color: var(--wizard-primary, #6366f1);
}

.step-description {
  margin-bottom: 26px;
  line-height: 1.65;
}

.step-description p {
  margin-bottom: 12px;
  color: var(--wizard-muted, #6b7280);
}

.step-description strong {
  color: var(--wizard-primary, #6366f1);
}

.create-channel-form {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
  padding: 22px;
  border-radius: 14px;
  border: 1px solid rgba(99, 102, 241, 0.18);
  margin-bottom: 22px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.form-group {
  margin-bottom: 20px;
}



.channel-name-input,
.channel-description-input {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: rgba(255, 255, 255, 0.92);
  color: var(--wizard-text, #1f2937);
}

.channel-name-input:focus,
.channel-description-input:focus {
  outline: none;
  border-color: var(--wizard-primary, #6366f1);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.18);
}



.alternative-option {
  text-align: center;
  margin: 20px 0;
}

.link-button {
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.18);
  color: var(--wizard-primary, #6366f1);
  cursor: pointer;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 999px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  font-weight: 500;
  text-decoration: none;
}

.link-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 20px rgba(99, 102, 241, 0.18);
}

.existing-channels-section {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.12), rgba(139, 92, 246, 0.06));
  padding: 20px;
  border-radius: 14px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}

.channel-select {
  width: 100%;
  padding: 12px;
  border: 1px solid rgba(34, 211, 238, 0.25);
  border-radius: 10px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--wizard-text, #1f2937);
  transition: all 0.2s ease;
}

.channel-select:focus {
  outline: none;
  border-color: var(--wizard-accent, #22d3ee);
  box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.18);
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
  background: rgba(255, 255, 255, 0.98);
  color: #1f2937;
}

.error-message {
  color: #ef4444;
  font-size: 12px;
  margin-top: 5px;
  padding: 5px 0;
}


.channels-loading {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 18px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  color: var(--wizard-text, #1f2937);
  font-size: 14px;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(99, 102, 241, 0.15);
  border-top: 2px solid var(--wizard-primary, #6366f1);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.no-channels-message {
  margin-top: 12px;
  padding: 14px;
  background: rgba(253, 230, 138, 0.16);
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 10px;
  color: #92400e;
}

.no-channels-message p {
  margin: 0 0 6px 0;
  font-size: 14px;
}

.no-channels-message p:last-child {
  margin: 0;
}

.no-channels-message small {
  color: rgba(146, 64, 14, 0.8);
  font-size: 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.creating-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.18), rgba(99, 102, 241, 0.12));
  border-radius: 12px;
  color: var(--wizard-primary, #6366f1);
  font-weight: 500;
  border: 1px solid rgba(99, 102, 241, 0.18);
}



.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(99, 102, 241, 0.15);
  border-top: 2px solid var(--wizard-primary, #6366f1);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

/* Мобильная оптимизация */
@media (max-width: 768px) {
  .simple-source-step {
    padding: 22px;
  }
  
  .simple-source-step h3 {
    font-size: 19px;
    margin-bottom: 16px;
  }
  
  .step-description p {
    font-size: 14px;
    margin-bottom: 10px;
  }
  
  .create-channel-form {
    padding: 18px;
  }
  
  .form-group {
    margin-bottom: 15px;
  }
  

  
  .channel-name-input,
  .channel-description-input,
  .channel-select {
    font-size: 16px; /* Prevent zoom on iOS */
    padding: 12px;
  }
  
  .checkbox-hint {
    font-size: 11px;
    margin-left: 20px;
  }
  
  .link-button {
    font-size: 13px;
    padding: 8px 12px;
  }
  
  .existing-channels-section {
    padding: 18px;
  }
}

@media (max-width: 480px) {
  .simple-source-step {
    padding: 16px;
  }
  
  .create-channel-form,
  .existing-channels-section {
    padding: 14px;
  }
  
  .step-description p {
    font-size: 13px;
  }
  
  .creating-indicator {
    padding: 12px;
    font-size: 14px;
  }
  
  .spinner {
    width: 18px;
    height: 18px;
  }
}
</style>