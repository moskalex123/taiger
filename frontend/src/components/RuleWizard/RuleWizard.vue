<template>
  <div class="rule-wizard-overlay">
    <!-- Loading overlay when wizard first opens -->
    <div v-if="wizardLoading" class="wizard-loading-overlay">
      <div class="wizard-loading-content">
        <div class="loading-spinner"></div>
        <p>{{ $t('loading_available_channels') }}</p>
        <p v-if="channels.subscribed && channels.admin" class="channel-count">
          {{ $t('loading_channels_count', { count: (channels.subscribed?.length || 0) + (channels.admin?.length || 0) }) }}
        </p>
      </div>
    </div>

    <div class="rule-wizard-modal">
      <div class="wizard-header">
        <h2>{{ $t('create_new_rule_wizard') }}</h2>
        <button @click="$emit('close')" class="close-btn">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>

      <StepIndicator 
        :current-step="currentStep" 
        :total-steps="totalSteps"
        :step-titles="stepTitles"
        @go-to-step="goToStep"
      />

      <div class="wizard-content">
        <component 
          :is="currentStepComponent"
          ref="currentStepRef"
          :wizard-data="wizardData"
          :channels="channels"
          :models="models"
          :loading-channels="loadingChannels"
          @update-data="updateWizardData"
          @refresh-channels="$emit('refresh-channels')"
          @update-button-state="() => forceUpdate++"
          @rule-created-successfully="handleRuleCreatedSuccessfully"
          @ready-to-create-rule="createRule"
          @next="nextStep"
          @prev="prevStep"
          @finish="finishWizard"
        />
      </div>

      <WizardNavigation
        :current-step="currentStep"
        :total-steps="totalSteps"
        :can-proceed="canProceed"
        :is-loading="isLoading"
        @next="nextStep"
        @prev="prevStep"
        @finish="finishWizard"
      />
    </div>

    <SuccessModal
      v-if="showSuccessModal"
      :source-channel-name="createdChannels.source"
      :target-channel-name="createdChannels.target"
      @close="closeSuccessModal"
    />

    <ProgressIndicator
      :show="showProgress"
      :title="$t('creating_rule_and_starting_worker')"
      :steps="progressSteps"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent, ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import axios from 'axios';
import { API_BASE_URL } from '@/config';
import { getDefaultSystemPrompt } from '@/utils/systemPrompt';
import { useNotifications } from '@/composables/useNotifications';
import StepIndicator from './StepIndicator.vue';
import WizardNavigation from './WizardNavigation.vue';
import SimpleSourceStep from './steps/SimpleSourceStep.vue';
import SimpleInstructionsStep from './steps/SimpleInstructionsStep.vue';
import SimpleScheduleStep from './steps/SimpleScheduleStep.vue';
import TargetChannelStep from './steps/TargetChannelStep.vue';
import SuccessModal from './SuccessModal.vue';
import ProgressIndicator from '../ProgressIndicator.vue';

interface WizardData {
  source_channel: string | null;
  target_channel: string | null;
  source_channel_data?: { title: string; description: string };
  target_channel_data?: { title: string; description: string };
  text_to_delete: string;
  model_id: number | null;
  system_content: string;
  max_tokens: number | null;
  temperature: number | null;
  top_p: number | null;
  hour_min: number;
  hour_max: number;
}

export default defineComponent({
  name: 'RuleWizard',
  components: {
    StepIndicator,
    WizardNavigation,
    SimpleSourceStep,
    SimpleInstructionsStep,
    SimpleScheduleStep,
    TargetChannelStep,
    SuccessModal,
    ProgressIndicator
  },
  props: {
    channels: {
      type: Object,
      required: true
    },
    models: {
      type: Array,
      required: true
    },
    editingRule: {
      type: Object,
      default: null
    },
    loadingChannels: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close', 'save', 'refresh-channels', 'rule-created-successfully'],
  setup(props, { emit }) {
    const { t: $t, locale } = useI18n();
    const { showError } = useNotifications();

    // Prevent background scrolling when modal is open
    onMounted(() => {
      document.body.style.overflow = 'hidden';
    });

    onBeforeUnmount(() => {
      document.body.style.overflow = '';
    });

    const currentStep = ref(1);
    const totalSteps = 2;
    const isLoading = ref(false);
    const forceUpdate = ref(0);
    const showSuccessModal = ref(false);
    const createdChannels = ref({ source: '', target: '' });
    const currentStepRef = ref(null);
    const showProgress = ref(false);
    const wizardLoading = ref(true); // Show loading when wizard first opens
    const progressSteps = ref([
      { id: 0, title: $t('progress_stop_agent'), description: $t('progress_stop_agent_desc'), status: 'pending' },
      { id: 1, title: $t('progress_create_channels'), description: $t('progress_create_channels_desc'), status: 'pending' },
      { id: 2, title: $t('progress_save_rule'), description: $t('progress_save_rule_desc'), status: 'pending' },
      { id: 3, title: $t('progress_start_agent'), description: $t('progress_start_agent_desc'), status: 'pending' },
      { id: 4, title: $t('progress_finalize'), description: $t('progress_finalize_desc'), status: 'pending' }
    ]);

    const stepTitles = computed(() => [
      $t('wizard_step_create_draft'),
      $t('wizard_step_create_target')
    ]);

    const wizardData = ref<WizardData>({
      source_channel: null,
      target_channel: null,
      text_to_delete: '',
      model_id: null, // Будет установлено в onMounted
      system_content: '',
      max_tokens: null,
      temperature: null,
      top_p: null,
      hour_min: 7,
      hour_max: 9
    });

    const stepComponents = {
      1: SimpleSourceStep, // Создание канала-черновика (с автонастройками)
      2: TargetChannelStep // Создание канала-чистовика и запуск
    };

    const currentStepComponent = computed(() => stepComponents[currentStep.value]);

    const canProceed = computed(() => {
      // Проверяем canProceed у текущего шага, если он доступен
      if (currentStepRef.value && currentStepRef.value.canProceed) {
        return currentStepRef.value.canProceed();
      }
      
      // Fallback логика
      if (currentStep.value === 1) {
        return true;
      }
      
      if (currentStep.value === 2) {
        return true;
      }
      
      return false;
    });

    const updateWizardData = (data: Partial<WizardData>) => {
      wizardData.value = { ...wizardData.value, ...data };
      // Принудительно обновляем canProceed
      forceUpdate.value++;
      console.log('WizardData updated:', wizardData.value);
    };

    const nextStep = () => {
      console.log('nextStep called', {
        currentStep: currentStep.value,
        totalSteps,
        canProceed: canProceed.value,
        hasStepRef: !!currentStepRef.value,
        hasHandleNext: !!(currentStepRef.value && currentStepRef.value.handleNext)
      });

      // Проверяем, есть ли у текущего шага собственный handleNext
      if (currentStepRef.value && currentStepRef.value.handleNext) {
        console.log('Calling step component handleNext');
        currentStepRef.value.handleNext();
        // Не возвращаемся, позволяем компоненту обработать логику и затем продолжаем
      }

      // Fallback логика - используется если handleNext не существует или после его выполнения
      // Сохраняем данные текущего шага перед переходом
      if (currentStep.value === 1) {
        // Сохраняем данные канала-черновика
        if (currentStepRef.value && currentStepRef.value.newChannel) {
          const sourceChannelName = currentStepRef.value.newChannel.title.trim();
          if (sourceChannelName && sourceChannelName.length >= 2) {
            console.log('Saving source channel data:', sourceChannelName);
            updateWizardData({
              source_channel_data: {
                title: sourceChannelName,
                description: currentStepRef.value.newChannel.description || `Канал-черновик для ${sourceChannelName}`,
                is_megagroup: currentStepRef.value.newChannel.is_megagroup || false
              }
            });
          }
        }
      }

      // Простая логика - просто переходим к следующему шагу
      if (currentStep.value < totalSteps) {
        currentStep.value++;
        console.log(`Moved to step ${currentStep.value}`);
      } else {
        console.log('Already at last step');
      }
    };

    const finishWizard = () => {
      console.log('🚀 FINISH WIZARD CALLED!');
      console.log('finishWizard called', {
        currentStep: currentStep.value,
        wizardData: wizardData.value
      });
      
      // Специальная логика для второго шага (создание целевого канала)
      if (currentStep.value === 2) {
        console.log('Step 2 - calling handleFinish on step component', {
          hasRef: !!currentStepRef.value,
          hasHandleFinish: !!(currentStepRef.value && currentStepRef.value.handleFinish)
        });
        
        if (currentStepRef.value && currentStepRef.value.handleFinish) {
          currentStepRef.value.handleFinish();
          return;
        } else {
          console.error('currentStepRef not found or no handleFinish method!');
          showError('Ошибка: не удалось найти компонент шага');
          return;
        }
      }
      
      // Обычная логика завершения
      console.log('Using fallback logic - creating rule directly');
      isLoading.value = true;
      emit('save', wizardData.value);
    };

    const prevStep = () => {
      if (currentStep.value > 1) {
        currentStep.value--;
      }
    };

    const goToStep = (step: number) => {
      if (step >= 1 && step <= totalSteps) {
        currentStep.value = step;
      }
    };

    // Initialize with editing data if provided
    onMounted(async () => {
      if (props.editingRule) {
        wizardData.value = { ...wizardData.value, ...props.editingRule };
      } else {
        // Не выбираем канал автоматически - пользователь создаст новый или выберет существующий

        // Get default system prompt from project settings
        const defaultSystemPrompt = await getDefaultSystemPrompt(locale.value);

        // Автоматически устанавливаем оптимальные настройки для новичков
        const defaultModel = props.models.find(m => m.id === 45);
        if (defaultModel) {
          wizardData.value.model_id = 45;
          wizardData.value.system_content = defaultSystemPrompt;
          wizardData.value.max_tokens = defaultModel.max_tokens;
          wizardData.value.temperature = defaultModel.temperature;
          wizardData.value.top_p = defaultModel.top_p;
        } else {
          // Fallback если модель с ID=45 не найдена
          wizardData.value.model_id = 45;
          wizardData.value.system_content = defaultSystemPrompt;
        }

        // Автоматически устанавливаем оптимальное расписание для новичков
        wizardData.value.hour_min = 7;
        wizardData.value.hour_max = 9;
      }

      // Ждем следующий тик и принудительно обновляем состояние
      await nextTick();
      forceUpdate.value++;
      console.log('RuleWizard mounted, forceUpdate triggered');

      // Hide wizard loading overlay after a short delay to show loading effect
      setTimeout(() => {
        wizardLoading.value = false;
      }, 800);
    });

    const closeSuccessModal = () => {
      showSuccessModal.value = false;
      emit('close');
    };

    const handleRuleCreatedSuccessfully = async (channelInfo) => {
      updateProgressStep(2, 'completed');
      
      // Этап 3: Запуск агента
      updateProgressStep(3, 'loading');
      await startWorker();
      updateProgressStep(3, 'completed');
      
      // Этап 4: Финализация
      updateProgressStep(4, 'loading');
      await new Promise(resolve => setTimeout(resolve, 500)); // Небольшая задержка для UX
      updateProgressStep(4, 'completed');
      
      // Скрываем прогресс и показываем модальное окно успеха
      setTimeout(() => {
        showProgress.value = false;
        createdChannels.value = {
          source: channelInfo.sourceChannel,
          target: channelInfo.targetChannel
        };
        showSuccessModal.value = true;
        
        // Передаем событие дальше в ChannelPairs и Dashboard
        emit('rule-created-successfully', channelInfo);
      }, 1000);
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
        
        await axios.post('/api/worker/stop', {}, {
          withCredentials: true,
          headers
        });
        console.log('Worker stopped successfully');
      } catch (error: unknown) {
        console.error('Error stopping worker:', error instanceof Error ? error.message : String(error));
        // Don't throw error - worker stop is not critical for channel creation
      }
    };

    // Function to start worker
    const startWorker = async () => {
      try {
        // Support both cookie-based auth and token-based auth (for TMA)
        const token = localStorage.getItem('auth_token');
        const headers: any = {};
        
        if (token) {
          headers['Authorization'] = 'Bearer ' + token;
        }
        
        await axios.post('/api/worker/start', {}, {
          withCredentials: true,
          headers
        });
        console.log('Worker started successfully');
      } catch (error: unknown) {
        console.error('Error starting worker:', error instanceof Error ? error.message : String(error));
        // Don't throw error - worker start failure shouldn't prevent rule creation
      }
    };

    // Function to update progress step
    const updateProgressStep = (stepId: number, status: 'loading' | 'completed' | 'error') => {
      const step = progressSteps.value.find(s => s.id === stepId);
      if (step) {
        step.status = status;
      }
    };

    const createChannelsAndRule = async () => {
      isLoading.value = true;
      showProgress.value = true;
      
      // Сброс статусов прогресса
      progressSteps.value.forEach(step => step.status = 'pending');
      
      try {
        // Support both cookie-based auth and token-based auth (for TMA)
        const token = localStorage.getItem('auth_token');
        let sourceChannelValue = wizardData.value.source_channel;
        let targetChannelValue = wizardData.value.target_channel;
        
        // Этап 0: Остановка агента
        updateProgressStep(0, 'loading');
        await stopWorker();
        updateProgressStep(0, 'completed');
        
        // Собираем каналы для создания
        const channelsToCreate = [];
        if (wizardData.value.source_channel_data) {
          channelsToCreate.push(wizardData.value.source_channel_data);
        }
        if (wizardData.value.target_channel_data) {
          channelsToCreate.push(wizardData.value.target_channel_data);
        }
        
        // Этап 1: Создание каналов
        if (channelsToCreate.length > 0) {
          updateProgressStep(1, 'loading');
          console.log('Creating channels in batch:', channelsToCreate);
          const headers: any = {};
          
          if (token) {
            headers['Authorization'] = 'Bearer ' + token;
          }
          
          const batchResponse = await axios.post('/api/channel_pairs/create-channels-batch', {
            channels: channelsToCreate
          }, {
            withCredentials: true,
            headers
          });
          
          console.log('Batch response:', batchResponse.data);
          
          // Обрабатываем результаты
          const results = batchResponse.data.results;
          let sourceIndex = 0;
          let targetIndex = wizardData.value.source_channel_data ? 1 : 0;
          
          // Обновляем значения каналов из результатов
          if (wizardData.value.source_channel_data && results[sourceIndex]) {
            const sourceResult = results[sourceIndex];
            if (sourceResult.status === 'success') {
              sourceChannelValue = sourceResult.username ? 
                (sourceResult.username.startsWith('@') ? sourceResult.username : `@${sourceResult.username}`) :
                sourceResult.channel_id.toString();
              console.log('Source channel created:', sourceChannelValue);
            } else {
              throw new Error(`Ошибка создания канала-источника: ${sourceResult.message}`);
            }
          }
          
          if (wizardData.value.target_channel_data && results[targetIndex]) {
            const targetResult = results[targetIndex];
            if (targetResult.status === 'success') {
              targetChannelValue = targetResult.username ? 
                (targetResult.username.startsWith('@') ? targetResult.username : `@${targetResult.username}`) :
                targetResult.channel_id.toString();
              console.log('Target channel created:', targetChannelValue);
            } else {
              throw new Error(`Ошибка создания канала-назначения: ${targetResult.message}`);
            }
          }
          updateProgressStep(1, 'completed');
        } else {
          updateProgressStep(1, 'completed'); // Нет каналов для создания
        }
        
        // Обновляем данные правила с созданными каналами
        const ruleData = {
          ...wizardData.value,
          source_channel: sourceChannelValue,
          target_channel: targetChannelValue
        };
        
        // Удаляем временные данные каналов
        delete ruleData.source_channel_data;
        delete ruleData.target_channel_data;
        
        console.log('Creating rule with data:', ruleData);
        
        // Проверяем, что каналы разные
        if (ruleData.source_channel === ruleData.target_channel) {
          throw new Error('Канал-источник и канал-назначение не могут быть одинаковыми.');
        }
        
        // Обновляем список каналов
        emit('refresh-channels');
        
        // Этап 2: Создание правила
        updateProgressStep(2, 'loading');
        emit('save', ruleData);
        
      } catch (error: unknown) {
        console.error('Error creating channels or rule:', error instanceof Error ? error.message : String(error));
        
        let errorMessage = 'Ошибка при создании каналов или правила';
        
        if (error && typeof error === 'object' && 'response' in error) {
          const errorObj = error as { response?: { data?: any } };
          const data = errorObj.response?.data;
          if (data && data.detail) {
            errorMessage = data.detail;
          } else if (data && data.message) {
            errorMessage = data.message;
          }
        } else if (error instanceof Error && error.message) {
          errorMessage = error.message;
        }
        
        showError(errorMessage);
        isLoading.value = false;
      }
    };

    const createRule = async () => {
      // Ждем немного, чтобы данные точно обновились
      await nextTick();
      
      console.log('Creating rule with data:', {
        source_channel: wizardData.value.source_channel,
        target_channel: wizardData.value.target_channel,
        source_channel_data: wizardData.value.source_channel_data,
        target_channel_data: wizardData.value.target_channel_data,
        fullData: wizardData.value
      });
      
      // Если есть данные для создания каналов, создаем каналы и правило
      if (wizardData.value.source_channel_data || wizardData.value.target_channel_data) {
        await createChannelsAndRule();
        return;
      }
      
      // Проверяем, что все необходимые данные есть
      if (!wizardData.value.source_channel || !wizardData.value.target_channel) {
        console.error('Missing channel data:', {
          source: wizardData.value.source_channel,
          target: wizardData.value.target_channel,
          fullData: wizardData.value
        });
        showError(`Ошибка: не все каналы выбраны.\nИсточник: ${wizardData.value.source_channel || 'не выбран'}\nЦель: ${wizardData.value.target_channel || 'не выбран'}`);
        return;
      }
      
      // Проверяем, что каналы разные
      if (wizardData.value.source_channel === wizardData.value.target_channel) {
        showError('Ошибка: канал-источник и канал-назначение не могут быть одинаковыми.');
        return;
      }
      
      // Создаем правило с существующими каналами
      isLoading.value = true;
      emit('save', wizardData.value);
    };

    return {
      currentStep,
      totalSteps,
      stepTitles,
      wizardData,
      currentStepComponent,
      canProceed,
      isLoading,
      updateWizardData,
      nextStep,
      prevStep,
      goToStep,
      finishWizard,
      showSuccessModal,
      createdChannels,
      closeSuccessModal,
      handleRuleCreatedSuccessfully,
      createRule,
      createChannelsAndRule,
      currentStepRef,
      showProgress,
      progressSteps,
      updateProgressStep,
      wizardLoading,
      $t
    };
  }
});
</script>

<style scoped>

.wizard-loading-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--wizard-surface);
  border-radius: 20px;
  z-index: 10;
}

.wizard-loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: var(--wizard-text);
}

.wizard-loading-content p {
  margin: 0;
  font-size: 16px;
  font-weight: 500;
}

.channel-count {
  font-size: 14px !important;
  color: var(--wizard-muted, #6b7280) !important;
  font-weight: 400 !important;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid rgba(99, 102, 241, 0.2);
  border-top: 3px solid var(--wizard-primary, #6366f1);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.rule-wizard-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 20px;
  background: radial-gradient(circle at top left, rgba(99, 102, 241, 0.28), rgba(17, 24, 39, 0.85)), rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(6px);
  z-index: 10000;
  overflow: hidden;
  --wizard-primary: #6366f1;
  --wizard-primary-light: #818cf8;
  --wizard-secondary: #8b5cf6;
  --wizard-accent: #22d3ee;
  --wizard-success: #34d399;
  --wizard-surface: linear-gradient(145deg, #ffffff 0%, #eef2ff 55%, #fff7ed 100%);
  --wizard-surface-alt: rgba(99, 102, 241, 0.08);
  --wizard-border: rgba(99, 102, 241, 0.22);
  --wizard-shadow: 0 24px 60px rgba(15, 23, 42, 0.35);
  --wizard-text: #1f2937;
  --wizard-muted: #6b7280;
}

.rule-wizard-modal {
  position: relative;
  width: 100%;
  max-width: 880px;
  max-height: 92vh;
  display: flex;
  flex-direction: column;
  background: var(--wizard-surface);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.35);
  box-shadow: var(--wizard-shadow);
  overflow: hidden;
}

.rule-wizard-modal::before {
  content: "";
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.18), transparent 55%),
              radial-gradient(circle at 100% 0%, rgba(34, 211, 238, 0.18), transparent 55%);
  pointer-events: none;
}

.wizard-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 22px 28px;
  background: linear-gradient(120deg, rgba(99, 102, 241, 0.95), rgba(139, 92, 246, 0.9));
  color: #ffffff;
  box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.12);
  z-index: 1;
}

.wizard-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  letter-spacing: 0.01em;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.25);
  color: #ffffff;
  transition: all 0.2s ease;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: scale(1.04);
}

.wizard-content {
  position: relative;
  flex: 1;
  overflow-y: auto;
  padding: 28px;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(6px);
}

/* TMA optimized styles */
@media (max-width: 768px) {
  .rule-wizard-overlay {
    padding: 18px 12px;
  }
  
  
  .rule-wizard-modal {
    max-width: 100%;
    max-height: 95vh;
    border-radius: 16px;
  }
  
  .wizard-header {
    padding: 18px 20px;
  }
  
  .wizard-header h2 {
    font-size: 18px;
  }
  
  .wizard-content {
    padding: 22px;
  }
}

/* TMA specific styles */
@media (max-width: 480px) {
  .rule-wizard-overlay {
    padding: 12px 8px;
  }
  
  .rule-wizard-modal {
    border-radius: 14px;
    max-height: 98vh;
  }
  
  .wizard-header {
    padding: 16px 18px;
  }
  
  .wizard-header h2 {
    font-size: 16px;
  }
  
  .wizard-content {
    padding: 18px;
  }
}
</style>
