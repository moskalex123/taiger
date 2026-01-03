<template>
  <div class="preview-step">
    <div class="step-header">
      <h3>{{ $t('wizard_step_preview_title') }}</h3>
      <p class="step-description">{{ $t('wizard_step_preview_description') }}</p>
    </div>

    <div class="preview-content">
      <div class="rule-summary">
        <h4>{{ $t('rule_summary') }}</h4>
        
        <div class="summary-section">
          <div class="section-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            <h5>{{ $t('channels') }}</h5>
          </div>
          <div class="channel-flow">
            <div class="channel-info source">
              <div class="channel-label">{{ $t('source_channel') }}</div>
              <div class="channel-name">{{ getChannelDisplayName(wizardData.source_channel, 'subscribed') }}</div>
            </div>
            <div class="flow-arrow">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path d="M5 12h14m-7-7 7 7-7 7"/>
              </svg>
            </div>
            <div class="channel-info target">
              <div class="channel-label">{{ $t('target_channel') }}</div>
              <div class="channel-name">{{ getChannelDisplayName(wizardData.target_channel, 'admin') }}</div>
            </div>
          </div>
        </div>

        <div v-if="wizardData.text_to_delete" class="summary-section">
          <div class="section-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M3 6h18m-2 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            <h5>{{ $t('text_deletion') }}</h5>
          </div>
          <div class="deletion-info">
            <span class="deletion-text">"{{ wizardData.text_to_delete }}"</span>
            <span class="deletion-note">{{ $t('will_be_removed_before_processing') }}</span>
          </div>
        </div>

        <div class="summary-section">
          <div class="section-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636-.707.707M21 12h-1M4 12H3m3.343-5.657-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
            <h5>{{ $t('ai_processing') }}</h5>
          </div>
          <div v-if="!wizardData.model_id" class="no-ai-info">
            <span class="no-ai-badge">{{ $t('no_ai_processing') }}</span>
            <span class="no-ai-note">{{ $t('posts_will_be_copied_as_is') }}</span>
          </div>
          <div v-else class="ai-info">
            <div class="ai-model">
              <span class="model-name">{{ getModelName() }}</span>
              <span class="model-cost">${{ getModelCost() }} {{ $t('per_post') }}</span>
            </div>
            <div v-if="wizardData.system_content" class="ai-instructions">
              <div class="instructions-label">{{ $t('instructions') }}:</div>
              <div class="instructions-content">{{ wizardData.system_content }}</div>
            </div>
            <div class="ai-parameters">
              <div class="param-item">
                <span>{{ $t('max_tokens') }}: {{ wizardData.max_tokens || 'Auto' }}</span>
              </div>
              <div class="param-item">
                <span>{{ $t('temperature') }}: {{ wizardData.temperature || 'Auto' }}</span>
              </div>
              <div class="param-item">
                <span>{{ $t('top_p') }}: {{ wizardData.top_p || 'Auto' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="summary-section">
          <div class="section-header">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12,6 12,12 16,14"/>
            </svg>
            <h5>{{ $t('schedule') }}</h5>
          </div>
          <div class="schedule-info">
            <div class="schedule-range">
              <span class="range-label">{{ $t('delay_range') }}:</span>
              <span class="range-value">{{ wizardData.hour_min }}h - {{ wizardData.hour_max }}h</span>
            </div>
            <div class="schedule-note">{{ $t('posts_will_be_delayed_randomly') }}</div>
          </div>
        </div>
      </div>

      <div class="test-section">
        <h4>{{ $t('test_rule') }}</h4>
        <p class="test-description">{{ $t('test_rule_description') }}</p>
        <button 
          @click="testRule" 
          class="test-btn"
          :disabled="isTestingRule"
        >
          <div v-if="isTestingRule" class="button-spinner"></div>
          <span v-if="!isTestingRule">{{ $t('test_rule_button') }}</span>
          <span v-else>{{ $t('testing') }}</span>
        </button>
        
        <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'error'">
          <div class="result-header">
            <svg v-if="testResult.success" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <polyline points="20,6 9,17 4,12"/>
            </svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <circle cx="12" cy="12" r="10"/>
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <span>{{ testResult.success ? $t('test_successful') : $t('test_failed') }}</span>
          </div>
          <div class="result-message">{{ testResult.message }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, ref } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'PreviewStep',
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
    }
  },
  emits: ['test-rule'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();
    
    const isTestingRule = ref(false);
    const testResult = ref<{ success: boolean; message: string } | null>(null);

    const getChannelDisplayName = (channelValue: string | null, type: 'subscribed' | 'admin') => {
      if (!channelValue) return $t('not_selected');
      
      const channelsList = type === 'subscribed' ? props.channels.subscribed : props.channels.admin;
      const channel = channelsList.find((c: { id: number; username?: string; title: string }) => {
        const value = c.username ?
          (c.username.startsWith('@') ? c.username : `@${c.username}`) :
          c.id.toString();
        return value === channelValue;
      });
      
      if (channel) {
        return channel.title + (channel.username ? ` (@${channel.username})` : ` (ID: ${channel.id})`);
      }
      
      return channelValue;
    };

    const getModelName = () => {
      if (!props.wizardData.model_id) return '';
      const models = props.models as Array<{ id: number; model?: string }>;
      const model = models.find(m => m.id === props.wizardData.model_id);
      return model && model.model ? model.model : '';
    };

    const getModelCost = () => {
      if (!props.wizardData.model_id) return '0.000';
      const models = props.models as Array<{ id: number; price_per_post?: number }>;
      const model = models.find(m => m.id === props.wizardData.model_id);
      return model ? (model.price_per_post || 0).toFixed(3) : '0.000';
    };

    const testRule = async () => {
      isTestingRule.value = true;
      testResult.value = null;
      
      try {
        // Validate rule configuration
        const errors = validateRuleConfiguration();
        
        if (errors.length > 0) {
          testResult.value = {
            success: false,
            message: $t('test_rule_error_message') + ':\n\n' + errors.join('\n')
          };
          return;
        }
        
        // Simulate API call for testing
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Mock successful test result
        testResult.value = {
          success: true,
          message: $t('test_rule_success_message')
        };
        
        emit('test-rule', props.wizardData);
      } catch (error: unknown) {
        testResult.value = {
          success: false,
          message: $t('test_rule_network_error')
        };
        console.error('Error testing rule:', error instanceof Error ? error.message : String(error));
      } finally {
        isTestingRule.value = false;
      }
    };

    const validateRuleConfiguration = () => {
      const errors: string[] = [];
      
      // Проверка канала-источника
      if (!props.wizardData.source_channel) {
        errors.push('• ' + $t('source_channel') + ': ' + $t('not_selected'));
      }
      
      // Проверка целевого канала
      if (!props.wizardData.target_channel) {
        errors.push('• ' + $t('target_channel') + ': ' + $t('not_selected'));
      }
      
      // Проверка что каналы разные
      if (props.wizardData.source_channel && props.wizardData.target_channel && 
          props.wizardData.source_channel === props.wizardData.target_channel) {
        errors.push('• Каналы-источник и назначения не могут быть одинаковыми');
      }
      
      // Проверка AI модели и инструкций
      if (props.wizardData.model_id && !props.wizardData.system_content?.trim()) {
        errors.push('• ' + $t('ai_instruction') + ': Не указаны инструкции для ИИ');
      }
      
      // Проверка расписания
      if (props.wizardData.hour_min === null || props.wizardData.hour_max === null) {
        errors.push('• ' + $t('schedule') + ': Не указан диапазон задержки');
      } else if (props.wizardData.hour_min < 0 || props.wizardData.hour_max < 0) {
        errors.push('• ' + $t('schedule') + ': Время задержки не может быть отрицательным');
      } else if (props.wizardData.hour_min > props.wizardData.hour_max) {
        errors.push('• ' + $t('schedule') + ': Минимальная задержка больше максимальной');
      }
      
      // Проверка доступности каналов
      if (props.wizardData.source_channel) {
        const sourceChannel = props.channels.subscribed.find((c: any) => {
          const value = c.username ? 
            (c.username.startsWith('@') ? c.username : `@${c.username}`) : 
            c.id.toString();
          return value === props.wizardData.source_channel;
        });
        if (!sourceChannel) {
          errors.push('• ' + $t('source_channel') + ': Канал не найден или недоступен');
        }
      }
      
      if (props.wizardData.target_channel) {
        const targetChannel = props.channels.admin.find((c: any) => {
          const value = c.username ? 
            (c.username.startsWith('@') ? c.username : `@${c.username}`) : 
            c.id.toString();
          return value === props.wizardData.target_channel;
        });
        if (!targetChannel) {
          errors.push('• ' + $t('target_channel') + ': Канал не найден или у вас нет прав администратора');
        }
      }
      
      return errors;
    };

    return {
      $t,
      isTestingRule,
      testResult,
      getChannelDisplayName,
      getModelName,
      getModelCost,
      testRule,
      validateRuleConfiguration
    };
  }
});
</script>

<style scoped>
.preview-step {
  max-width: 800px;
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

.preview-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.rule-summary {
  background: #f8f9fa;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.rule-summary h4 {
  margin: 0 0 24px 0;
  color: #333;
  font-size: 20px;
}

.summary-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e9ecef;
}

.summary-section:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}

.section-header svg {
  color: #007bff;
}

.section-header h5 {
  margin: 0;
  color: #333;
  font-size: 16px;
  font-weight: 500;
}

.channel-flow {
  display: flex;
  align-items: center;
  gap: 20px;
}

.channel-info {
  flex: 1;
  text-align: center;
}

.channel-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
  text-transform: uppercase;
  font-weight: 500;
}

.channel-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  background: white;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.flow-arrow {
  color: #007bff;
}

.deletion-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.deletion-text {
  font-size: 14px;
  color: #333;
  font-weight: 500;
  background: white;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  display: inline-block;
}

.deletion-note {
  font-size: 12px;
  color: #666;
}

.no-ai-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.no-ai-badge {
  background: #28a745;
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  display: inline-block;
  width: fit-content;
}

.no-ai-note {
  font-size: 12px;
  color: #666;
}

.ai-info {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ai-model {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.model-name {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.model-cost {
  font-size: 12px;
  color: #007bff;
  font-weight: 500;
}

.ai-instructions {
  background: white;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.instructions-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 6px;
  font-weight: 500;
}

.instructions-content {
  font-size: 13px;
  color: #333;
  line-height: 1.4;
}

.ai-parameters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.param-item {
  background: white;
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  font-size: 12px;
  color: #333;
}

.schedule-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.schedule-range {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 12px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
}

.range-label {
  font-size: 14px;
  color: #666;
}

.range-value {
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.schedule-note {
  font-size: 12px;
  color: #666;
}

.test-section {
  background: white;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
  text-align: center;
}

.test-section h4 {
  margin: 0 0 12px 0;
  color: #333;
  font-size: 18px;
}

.test-description {
  color: #666;
  font-size: 14px;
  line-height: 1.5;
  margin: 0 0 20px 0;
}

.test-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: #007bff;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease;
  margin: 0 auto 20px auto;
}

.test-btn:hover:not(:disabled) {
  background: #0056b3;
}

.test-btn:disabled {
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

.test-result {
  padding: 16px;
  border-radius: 6px;
  text-align: left;
}

.test-result.success {
  background: #d4edda;
  border: 1px solid #c3e6cb;
  color: #155724;
}

.test-result.error {
  background: #f8d7da;
  border: 1px solid #f5c6cb;
  color: #721c24;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  margin-bottom: 8px;
}

.result-message {
  font-size: 14px;
  line-height: 1.4;
  white-space: pre-line;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .channel-flow {
    flex-direction: column;
    gap: 12px;
  }
  
  .flow-arrow {
    transform: rotate(90deg);
  }
  
  .ai-parameters {
    grid-template-columns: 1fr;
  }
}
</style>