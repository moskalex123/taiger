<template>
  <div class="instructions-step">
    <div class="step-header">
      <h3>{{ $t('wizard_step_instructions_title') }}</h3>
      <p class="step-description">{{ $t('wizard_step_instructions_description') }}</p>
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
        <p>{{ $t('no_ai_instructions_notice') }}</p>
      </div>
    </div>

    <div v-else class="instructions-form">
      <div class="form-group">
        <label for="system_content">
          <div class="label-with-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10,9 9,9 8,9"/>
            </svg>
            {{ $t('ai_instructions') }}
          </div>
        </label>
        <textarea 
          id="system_content"
          :value="wizardData.system_content"
          @input="updateInstructions"
          :placeholder="$t('instructions_placeholder')"
          rows="8"
        ></textarea>
        <div class="field-help">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <circle cx="12" cy="12" r="10"/>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          {{ $t('instructions_help') }}
        </div>
      </div>

      <div class="examples-section">
        <h4>{{ $t('instruction_examples') }}</h4>
        <div class="examples-grid">
          <div 
            v-for="example in instructionExamples" 
            :key="example.title"
            class="example-card"
            @click="useExample(example.content)"
          >
            <div class="example-header">
              <h5>{{ example.title }}</h5>
              <button class="use-example-btn">{{ $t('use_example') }}</button>
            </div>
            <p class="example-content">{{ example.content }}</p>
          </div>
        </div>
      </div>

      <div class="tips-section">
        <h4>{{ $t('writing_tips') }}</h4>
        <ul class="tips-list">
          <li>{{ $t('tip_be_specific') }}</li>
          <li>{{ $t('tip_use_examples') }}</li>
          <li>{{ $t('tip_set_tone') }}</li>
          <li>{{ $t('tip_mention_format') }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'InstructionsStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    }
  },
  emits: ['update-data'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();

    const instructionExamples = computed(() => [
      {
        title: $t('example_improve_text'),
        content: $t('example_improve_text_content')
      },
      {
        title: $t('example_summarize'),
        content: $t('example_summarize_content')
      },
      {
        title: $t('example_translate'),
        content: $t('example_translate_content')
      },
      {
        title: $t('example_format'),
        content: $t('example_format_content')
      }
    ]);

    const updateInstructions = (event: Event) => {
      const target = event.target as HTMLTextAreaElement;
      emit('update-data', { system_content: target.value });
    };

    const useExample = (content: string) => {
      emit('update-data', { system_content: content });
    };

    return {
      $t,
      instructionExamples,
      updateInstructions,
      useExample
    };
  }
});
</script>

<style scoped>
.instructions-step {
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

.instructions-form {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.label-with-icon {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-group textarea {
  width: 100%;
  padding: 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  line-height: 1.5;
  resize: vertical;
  transition: border-color 0.2s ease;
}

.form-group textarea:focus {
  outline: none;
  border-color: #007bff;
}

.field-help {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  margin-top: 8px;
  line-height: 1.4;
}

.examples-section h4,
.tips-section h4 {
  margin: 0 0 16px 0;
  color: #333;
  font-size: 18px;
}

.examples-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 16px;
}

.example-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.example-card:hover {
  border-color: #007bff;
  background: #f8f9ff;
}

.example-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.example-header h5 {
  margin: 0;
  color: #333;
  font-size: 14px;
  font-weight: 500;
}

.use-example-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.use-example-btn:hover {
  background: #0056b3;
}

.example-content {
  font-size: 13px;
  color: #666;
  line-height: 1.4;
  margin: 0;
}

.tips-section {
  background: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.tips-list {
  margin: 0;
  padding-left: 20px;
}

.tips-list li {
  font-size: 14px;
  color: #666;
  line-height: 1.5;
  margin-bottom: 8px;
}

.tips-list li:last-child {
  margin-bottom: 0;
}
</style>