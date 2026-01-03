<template>
  <div class="target-channel-step">
    <div class="step-header">
      <h3>{{ $t('step_2_create_target_channel') }}</h3>
      <div class="step-description">
        <p>{{ $t('target_channel_explanation_1') }} {{ $t('target_channel_explanation_2') }}</p>
      </div>
    </div>

    <div v-if="!showExistingChannels" class="create-channel-form">
      <div class="form-group">
        <input 
          id="target-channel-name"
          v-model="newChannel.title"
          type="text" 
          class="channel-name-input"
          :placeholder="$t('my_new_channel')"
          required
          @input="onTargetChannelNameInput"
        >
        <div v-if="channelNameError" class="error-message">
          {{ channelNameError }}
        </div>
      </div>
      

    </div>



    <!-- Альтернативный вариант для опытных пользователей -->
    <div class="alternative-option">
      <button @click="toggleExistingChannelMode" class="link-button">
        {{ showExistingChannels ? $t('back_to_create_channel') : $t('i_already_have_target_channel') }}
      </button>
    </div>

    <div v-if="showExistingChannels" class="existing-channels-section">
      <div class="form-group">
        <label>{{ $t('select_existing_target_channel') }}:</label>
        
        <!-- Loading indicator -->
        <div v-if="loadingChannels" class="channels-loading">
          <div class="loading-spinner"></div>
          <span>{{ $t('loading_channels') || 'Загружаем каналы...' }} <span v-if="loadedChannelsCount > 0">({{ loadedChannelsCount }})</span></span>
        </div>
        
        <!-- Channel select -->
        <select 
          v-else
          :value="wizardData.target_channel" 
          @change="updateTargetChannel"
          class="channel-select"
        >
          <option value="">{{ $t('select_channel') }}</option>
          <option 
            v-for="channel in channels.admin" 
            :key="channel.id" 
            :value="getChannelValue(channel)"
          >
            {{ channel.title }} {{ channel.username ? `(@${channel.username})` : `(ID: ${channel.id})` }}
          </option>
        </select>
        
        <div v-if="!loadingChannels && (!channels.admin || !Array.isArray(channels.admin) || channels.admin.length === 0)" class="no-channels-message">
          <p>{{ $t('no_admin_channels_found') }}</p>
          <p><small>{{ $t('create_channel_first_or_become_admin') }}</small></p>
        </div>
      </div>
    </div>

    <div class="timing-info">
      <div class="info-card">
        <div class="info-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12,6 12,12 16,14"/>
          </svg>
          <h4>{{ $t('posting_schedule') }}</h4>
        </div>
        <div v-if="!showScheduleEdit" class="schedule-display">
          <p>{{ $t('posts_will_be_published_with_delay', { min: wizardData.hour_min, max: wizardData.hour_max, frequency: getPostingFrequency() }) }}</p>
          <button @click="toggleScheduleEdit" class="change-schedule-btn">
            {{ $t('change') }}
          </button>
        </div>
        <div v-else class="schedule-edit-form">
          <div class="schedule-inputs">
            <div class="input-group">
              <label>{{ $t('minimum_delay') }}:</label>
              <input 
                v-model.number="tempSchedule.hour_min" 
                type="number" 
                min="0" 
                max="168"
                class="schedule-input"
              >
              <span class="input-suffix">{{ $t('hours') }}</span>
            </div>
            <div class="input-group">
              <label>{{ $t('maximum_delay') }}:</label>
              <input 
                v-model.number="tempSchedule.hour_max" 
                type="number" 
                min="0" 
                max="168"
                class="schedule-input"
              >
              <span class="input-suffix">{{ $t('hours') }}</span>
            </div>
          </div>
          <div class="schedule-buttons">
            <button @click="saveSchedule" class="save-schedule-btn">
              {{ $t('save_schedule') }}
            </button>
            <button @click="cancelScheduleEdit" class="cancel-schedule-btn">
              {{ $t('cancel_edit') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="ai-model-info">
      <div class="info-card">
        <div class="info-header">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path d="M12 2L2 7v10c0 5.55 3.84 10 9 11 5.16-1 9-5.45 9-11V7l-10-5z"/>
            <path d="m8 12 2 2 4-4"/>
          </svg>
          <h4>{{ $t('ai_model_label') }}</h4>
        </div>
        <div v-if="!showModelEdit" class="model-display">
          <p v-if="selectedModel">
            {{ $t('ai_processing_with_model', { 
              model: selectedModel.model_visible_name || selectedModel.model, 
              price: selectedModel.price_per_post ? selectedModel.price_per_post.toFixed(3) : '0.000' 
            }) }}
          </p>
          <p v-else>{{ $t('no_ai_processing') }}</p>
          <button @click="toggleModelEdit" class="change-model-btn">
            {{ $t('change') }}
          </button>
        </div>
        <div v-else class="model-edit-form">
          <div class="model-selection">
            <div class="model-options">
              <div 
                class="model-option"
                :class="{ selected: !wizardData.model_id }"
                @click="selectNoAI"
              >
                <div class="model-header">
                  <div class="model-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
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
              
              <div 
                v-for="model in models" 
                :key="model.id"
                class="model-option"
                :class="{ selected: wizardData.model_id === model.id }"
                @click="selectModel(model)"
              >
                <div class="model-header">
                  <div class="model-icon">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
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
              </div>
            </div>
          </div>
          <div class="model-buttons">
            <button @click="saveModel" class="save-model-btn">
              {{ $t('save_rule') }}
            </button>
            <button @click="cancelModelEdit" class="cancel-model-btn">
              {{ $t('cancel_edit') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import axios from 'axios';

export default defineComponent({
  name: 'TargetChannelStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    },
    channels: {
      type: Object,
      required: true
    },
    models: {
      type: Array,
      required: true
    },
    loadingChannels: {
      type: Boolean,
      default: false
    }
  },
  emits: ['update-data', 'refresh-channels', 'finish', 'update-button-state', 'ready-to-create-rule'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();
    
    const showExistingChannels = ref(false);
    const creatingChannel = ref(false);
    const channelNameError = ref('');
    const showScheduleEdit = ref(false);
    const showModelEdit = ref(false);
    const tempSchedule = ref({
      hour_min: props.wizardData.hour_min || 7,
      hour_max: props.wizardData.hour_max || 9
    });
    const tempModel = ref({
      model_id: props.wizardData.model_id || 45,
      system_content: props.wizardData.system_content || '',
      max_tokens: props.wizardData.max_tokens || null,
      temperature: props.wizardData.temperature || null,
      top_p: props.wizardData.top_p || null
    });
    const newChannel = ref({
      title: 'Мой канал',
      description: '',
      is_megagroup: false
    });
    
    // Счетчик загруженных каналов
    const loadedChannelsCount = ref(0);
    const totalChannelsCount = ref(0);
    
    // Вычисляем количество загруженных каналов при изменении props.channels
    watch(() => props.channels, (newChannels) => {
      if (newChannels && newChannels.admin && Array.isArray(newChannels.admin)) {
        loadedChannelsCount.value = newChannels.admin.length;
        totalChannelsCount.value = newChannels.admin.length;
      }
    }, { immediate: true });

    const getChannelValue = (channel: any): string => {
      if (channel.username) {
        return channel.username.startsWith('@') ? channel.username : `@${channel.username}`;
      }
      return channel.id.toString();
    };



    const updateTargetChannel = (event: Event) => {
      const target = event.target as HTMLSelectElement;
      emit('update-data', { target_channel: target.value || null });
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

    const onTargetChannelNameInput = () => {
      validateChannelName();
      emit('update-button-state');
    };

    const toggleExistingChannelMode = () => {
      showExistingChannels.value = !showExistingChannels.value;
      if (!showExistingChannels.value) {
        // Возвращаемся к созданию канала - очищаем выбранный канал
        emit('update-data', { target_channel: null });
      } else {
        // Переключаемся в режим выбора существующих каналов - загружаем каналы
        console.log('TargetChannelStep: Switching to existing channels mode');
        console.log('Current channels:', props.channels);
        console.log('Admin channels:', props.channels?.admin);
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
      } catch (error: unknown) {
        console.error('Error stopping worker:', error instanceof Error ? error.message : String(error));
        // Don't throw error - channel creation should continue even if worker stop fails
      }
    };

    const createChannelAndFinish = async () => {
      console.log('createChannelAndFinish called', {
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
          
          // Устанавливаем созданный канал как целевой
          const createdChannelValue = response.data.username ? 
            (response.data.username.startsWith('@') ? response.data.username : `@${response.data.username}`) :
            response.data.id.toString();
          
          emit('update-data', { target_channel: createdChannelValue });
          
          // Уведомляем о готовности данных для создания правила
          setTimeout(() => {
            emit('ready-to-create-rule');
          }, 100);
          
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

    // Переопределяем логику кнопки "Завершить"
    const canProceed = () => {
      if (showExistingChannels.value) {
        return !!props.wizardData.target_channel;
      } else {
        return validateChannelName() && !creatingChannel.value;
      }
    };

    const handleFinish = () => {
      console.log('TargetChannelStep handleFinish called', {
        showExistingChannels: showExistingChannels.value,
        targetChannel: props.wizardData.target_channel,
        newChannelTitle: newChannel.value.title
      });
      
      if (showExistingChannels.value) {
        // Если выбран существующий канал, сразу готовы создавать правило
        console.log('Using existing channel, emitting ready-to-create-rule');
        emit('ready-to-create-rule');
      } else {
        // Если создаем новый канал, сохраняем данные для создания позже
        if (!validateChannelName()) {
          console.log('Validation failed, returning');
          return;
        }
        
        console.log('Saving target channel data for later creation...');
        const targetChannelName = newChannel.value.title.trim();
        emit('update-data', { 
          target_channel_data: {
            title: targetChannelName,
            description: newChannel.value.description || `Канал-чистовик для ${targetChannelName}`,
            is_megagroup: newChannel.value.is_megagroup || false
          }
        });
        
        // Готовы создавать каналы и правило
        emit('ready-to-create-rule');
      }
    };

    const toggleScheduleEdit = () => {
      showScheduleEdit.value = true;
      // Обновляем временные значения текущими данными
      tempSchedule.value = {
        hour_min: props.wizardData.hour_min || 7,
        hour_max: props.wizardData.hour_max || 9
      };
    };

    const saveSchedule = () => {
      // Валидация
      if (tempSchedule.value.hour_min >= tempSchedule.value.hour_max) {
        tempSchedule.value.hour_max = tempSchedule.value.hour_min + 1;
      }
      
      // Обновляем данные мастера
      emit('update-data', {
        hour_min: tempSchedule.value.hour_min,
        hour_max: tempSchedule.value.hour_max
      });
      
      showScheduleEdit.value = false;
    };

    const cancelScheduleEdit = () => {
      showScheduleEdit.value = false;
      // Возвращаем исходные значения
      tempSchedule.value = {
        hour_min: props.wizardData.hour_min || 7,
        hour_max: props.wizardData.hour_max || 9
      };
    };

    const getPostingFrequency = () => {
      const minHours = props.wizardData.hour_min || 7;
      const maxHours = props.wizardData.hour_max || 9;
      const avgHours = (minHours + maxHours) / 2;
      const postsPerDay = Math.round(24 / avgHours);
      
      if (postsPerDay === 1) {
        return '1 пост в день';
      } else if (postsPerDay >= 2 && postsPerDay <= 4) {
        return `${postsPerDay} поста в день`;
      } else if (postsPerDay >= 5) {
        return `${postsPerDay} постов в день`;
      } else {
        return 'менее 1 поста в день';
      }
    };

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

    const toggleModelEdit = () => {
      showModelEdit.value = true;
      // Обновляем временные значения текущими данными
      tempModel.value = {
        model_id: props.wizardData.model_id || 45,
        system_content: props.wizardData.system_content || '',
        max_tokens: props.wizardData.max_tokens || null,
        temperature: props.wizardData.temperature || null,
        top_p: props.wizardData.top_p || null
      };
    };

    const selectNoAI = async () => {
      tempModel.value.model_id = null;
      tempModel.value.system_content = '';
      tempModel.value.max_tokens = null;
      tempModel.value.temperature = null;
      tempModel.value.top_p = null;
    };

    const selectModel = async (model: any) => {
      const { getDefaultSystemPrompt } = await import('@/utils/systemPrompt');
      const defaultSystemPrompt = await getDefaultSystemPrompt('ru');
      
      tempModel.value.model_id = model.id;
      tempModel.value.system_content = defaultSystemPrompt;
      tempModel.value.max_tokens = model.max_tokens;
      tempModel.value.temperature = model.temperature;
      tempModel.value.top_p = model.top_p;
    };

    const saveModel = async () => {
      // Обновляем данные мастера
      emit('update-data', {
        model_id: tempModel.value.model_id,
        system_content: tempModel.value.system_content,
        max_tokens: tempModel.value.max_tokens,
        temperature: tempModel.value.temperature,
        top_p: tempModel.value.top_p
      });
      
      showModelEdit.value = false;
    };

    const cancelModelEdit = () => {
      showModelEdit.value = false;
      // Возвращаем исходные значения
      tempModel.value = {
        model_id: props.wizardData.model_id || 45,
        system_content: props.wizardData.system_content || '',
        max_tokens: props.wizardData.max_tokens || null,
        temperature: props.wizardData.temperature || null,
        top_p: props.wizardData.top_p || null
      };
    };

    return {
      $t,
      showExistingChannels,
      creatingChannel,
      channelNameError,
      showScheduleEdit,
      tempSchedule,
      newChannel,
      getChannelValue,
      updateTargetChannel,
      validateChannelName,
      onTargetChannelNameInput,
      toggleExistingChannelMode,
      createChannelAndFinish,
      canProceed,
      handleFinish,
      toggleScheduleEdit,
      saveSchedule,
      cancelScheduleEdit,
      getPostingFrequency,
      selectedModel,
      getProviderName,
      toggleModelEdit,
      selectNoAI,
      selectModel,
      saveModel,
      cancelModelEdit,
      loadedChannelsCount,
      totalChannelsCount
    };
  }
});
</script>

<style scoped>
.target-channel-step {
  max-width: 760px;
  margin: 0 auto;
  background: rgba(255, 255, 255, 0.82);
  border-radius: 18px;
  border: 1px solid rgba(99, 102, 241, 0.12);
  box-shadow: 0 18px 40px rgba(99, 102, 241, 0.12);
  padding: 32px;
  position: relative;
}

.target-channel-step::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(140deg, rgba(99, 102, 241, 0.12), rgba(34, 211, 238, 0.08));
  opacity: 0.85;
  z-index: -1;
  pointer-events: none;
}

.step-header {
  text-align: center;
  margin-bottom: 32px;
}

.step-header h3 {
  margin: 0 0 14px 0;
  color: var(--wizard-primary, #6366f1);
  font-size: 26px;
  font-weight: 600;
}

.description-with-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.step-description {
  color: var(--wizard-muted, #6b7280);
  font-size: 16px;
  line-height: 1.65;
  margin: 0;
}

.create-channel-btn {
  background: linear-gradient(135deg, var(--wizard-primary, #6366f1), var(--wizard-secondary, #8b5cf6));
  color: #ffffff;
  border: none;
  padding: 10px 20px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  white-space: nowrap;
  box-shadow: 0 12px 22px rgba(99, 102, 241, 0.28);
}

.create-channel-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 28px rgba(99, 102, 241, 0.32);
}



.channel-selection {
  margin-bottom: 30px;
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
  color: var(--wizard-primary, #6366f1);
  margin-bottom: 8px;
  font-size: 14px;
}

.channel-select {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(34, 211, 238, 0.25);
  border-radius: 12px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: rgba(255, 255, 255, 0.92);
  color: var(--wizard-text, #1f2937);
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

.field-help {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--wizard-muted, #6b7280);
  margin-top: 8px;
  line-height: 1.4;
}

.timing-info {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(34, 211, 238, 0.1));
  border: 1px solid rgba(99, 102, 241, 0.18);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
  margin-bottom: 20px;
}

.ai-model-info {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.12), rgba(34, 211, 238, 0.08));
  border: 1px solid rgba(139, 92, 246, 0.18);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.info-card {
  padding: 20px;
}

.info-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.info-header svg {
  color: var(--wizard-accent, #22d3ee);
}

.info-header h4 {
  margin: 0;
  color: var(--wizard-primary, #6366f1);
  font-size: 15px;
  font-weight: 600;
}

.info-card p {
  margin: 0;
  font-size: 13px;
  color: var(--wizard-muted, #6b7280);
  line-height: 1.55;
}

.schedule-display {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.schedule-display p {
  margin: 0;
  flex: 1;
}

.change-schedule-btn {
  background: linear-gradient(135deg, var(--wizard-primary, #6366f1), var(--wizard-secondary, #8b5cf6));
  color: #ffffff;
  border: none;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  white-space: nowrap;
  box-shadow: 0 10px 18px rgba(99, 102, 241, 0.2);
}

.change-schedule-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 24px rgba(99, 102, 241, 0.3);
}

.model-display {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.model-display p {
  margin: 0;
  flex: 1;
}

.change-model-btn {
  background: linear-gradient(135deg, var(--wizard-secondary, #8b5cf6), var(--wizard-accent, #22d3ee));
  color: #ffffff;
  border: none;
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  white-space: nowrap;
  box-shadow: 0 10px 18px rgba(139, 92, 246, 0.2);
}

.change-model-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 24px rgba(139, 92, 246, 0.3);
}

.model-edit-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.model-selection {
  max-height: 300px;
  overflow-y: auto;
}

.model-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.model-option {
  border: 2px solid rgba(139, 92, 246, 0.15);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  background: rgba(255, 255, 255, 0.92);
}

.model-option:hover {
  border-color: var(--wizard-secondary, #8b5cf6);
  background: rgba(139, 92, 246, 0.05);
}

.model-option.selected {
  border-color: var(--wizard-secondary, #8b5cf6);
  background: rgba(139, 92, 246, 0.12);
}

.model-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: rgba(139, 92, 246, 0.1);
  color: var(--wizard-secondary, #8b5cf6);
  flex-shrink: 0;
}

.model-info {
  flex: 1;
}

.model-info h5 {
  margin: 0 0 4px 0;
  color: var(--wizard-text, #1f2937);
  font-size: 14px;
  font-weight: 500;
}

.model-meta {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.provider-badge, .cost-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.provider-badge {
  background: rgba(139, 92, 246, 0.1);
  color: var(--wizard-secondary, #8b5cf6);
}

.cost-badge {
  background: rgba(253, 230, 138, 0.2);
  color: #92400e;
}

.model-price {
  display: flex;
  align-items: center;
}

.price {
  font-size: 14px;
  font-weight: 600;
  color: var(--wizard-secondary, #8b5cf6);
}

.price-free {
  font-size: 12px;
  font-weight: 500;
  color: #22c55e;
}

.model-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.save-model-btn {
  background: linear-gradient(135deg, var(--wizard-secondary, #8b5cf6), var(--wizard-accent, #22d3ee));
  color: #ffffff;
  border: none;
  padding: 9px 18px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 12px 20px rgba(139, 92, 246, 0.2);
}

.save-model-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 26px rgba(139, 92, 246, 0.28);
}

.cancel-model-btn {
  background: rgba(255, 255, 255, 0.6);
  color: var(--wizard-muted, #6b7280);
  border: 1px solid rgba(139, 92, 246, 0.15);
  padding: 9px 18px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.cancel-model-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 18px rgba(139, 92, 246, 0.18);
}

.schedule-edit-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.schedule-inputs {
  display: flex;
  gap: 12px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.input-group label {
  font-size: 12px;
  font-weight: 500;
  color: var(--wizard-primary, #6366f1);
}

.schedule-input {
  padding: 10px 12px;
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--wizard-text, #1f2937);
  font-size: 14px;
  width: 90px;
  transition: all 0.2s ease;
}

.schedule-input:focus {
  outline: none;
  border-color: var(--wizard-primary, #6366f1);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.18);
}

.input-suffix {
  font-size: 12px;
  color: var(--wizard-muted, #6b7280);
  margin-left: 8px;
}

.schedule-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.save-schedule-btn {
  background: linear-gradient(135deg, var(--wizard-secondary, #8b5cf6), var(--wizard-accent, #22d3ee));
  color: #ffffff;
  border: none;
  padding: 9px 18px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 12px 20px rgba(34, 211, 238, 0.2);
}

.save-schedule-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 16px 26px rgba(139, 92, 246, 0.28);
}

.cancel-schedule-btn {
  background: rgba(255, 255, 255, 0.6);
  color: var(--wizard-muted, #6b7280);
  border: 1px solid rgba(99, 102, 241, 0.15);
  padding: 9px 18px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.cancel-schedule-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 18px rgba(99, 102, 241, 0.18);
}

.create-channel-section {
  margin-bottom: 30px;
}

.create-channel-card {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(241, 245, 255, 0.92));
  border: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 16px;
  padding: 26px;
  box-shadow: 0 16px 32px rgba(99, 102, 241, 0.12);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 20px;
}

.card-header svg {
  color: var(--wizard-primary, #6366f1);
}

.card-header h4 {
  margin: 0;
  color: var(--wizard-primary, #6366f1);
  font-size: 18px;
  font-weight: 600;
}

.create-form {
  text-align: left;
}

.form-group {
  margin-bottom: 20px;
}



.form-group input,
.form-group textarea {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  font-size: 14px;
  transition: all 0.2s ease;
  box-sizing: border-box;
  background: rgba(255, 255, 255, 0.92);
  color: var(--wizard-text, #1f2937);
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--wizard-primary, #6366f1);
  box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.18);
}

.checkbox-group {
  margin-bottom: 20px;
}


.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--wizard-text, #1f2937);
}

.checkbox-label input[type="checkbox"] {
  width: auto;
  margin: 0;
}


.form-buttons {
  display: flex;
  gap: 14px;
  justify-content: flex-end;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.6);
  color: var(--wizard-muted, #6b7280);
  border: 1px solid rgba(99, 102, 241, 0.18);
  padding: 12px 20px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.cancel-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 22px rgba(99, 102, 241, 0.18);
}

.submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: linear-gradient(135deg, var(--wizard-secondary, #8b5cf6), var(--wizard-accent, #22d3ee));
  color: #ffffff;
  border: none;
  padding: 12px 22px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: 0 16px 28px rgba(34, 211, 238, 0.28);
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 20px 32px rgba(139, 92, 246, 0.32);
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

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}


.create-channel-form {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
  padding: 24px;
  border-radius: 16px;
  border: 1px solid rgba(99, 102, 241, 0.18);
  margin-bottom: 24px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
}

.channel-name-input,
.channel-description-input {
  width: 100%;
  padding: 14px;
  border: 1px solid rgba(99, 102, 241, 0.28);
  border-radius: 12px;
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
  margin: 22px 0;
}

.link-button {
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.18);
  color: var(--wizard-primary, #6366f1);
  cursor: pointer;
  font-size: 14px;
  padding: 8px 18px;
  border-radius: 999px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  font-weight: 600;
  text-decoration: none;
}

.link-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 20px rgba(99, 102, 241, 0.18);
}


.existing-channels-section {
  background: linear-gradient(135deg, rgba(34, 211, 238, 0.12), rgba(139, 92, 246, 0.06));
  padding: 20px;
  border-radius: 16px;
  border: 1px solid rgba(34, 211, 238, 0.2);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
}


.no-channels-message {
  margin-top: 12px;
  padding: 14px;
  background: rgba(253, 230, 138, 0.16);
  border: 1px solid rgba(245, 158, 11, 0.28);
  border-radius: 12px;
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

.error-message {
  color: #ef4444;
  font-size: 12px;
  margin-top: 5px;
  padding: 5px 0;
}

.checkbox-group {
  margin-bottom: 15px;
}

.checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--wizard-text, #1f2937);
}

.checkbox-label input[type="checkbox"] {
  margin-top: 2px;
}

.checkbox-text {
  color: var(--wizard-text, #1f2937);
}

.checkbox-hint {
  font-size: 12px;
  color: var(--wizard-muted, #6b7280);
  margin-top: 4px;
  margin-left: 24px;
  line-height: 1.4;
}

@media (max-width: 768px) {
  .description-with-button {
    flex-direction: column;
    gap: 16px;
  }
  
  .form-buttons {
    flex-direction: column;
  }
  
  .schedule-display {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
  
  .schedule-inputs {
    flex-direction: column;
    gap: 12px;
  }
  
  .schedule-buttons {
    justify-content: stretch;
  }
  
  .save-schedule-btn,
  .cancel-schedule-btn {
    flex: 1;
  }
}
</style>