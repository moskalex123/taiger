<template>
  <div class="simple-instructions-step">
    <h3>{{ $t('step_3_ai_instructions') }}</h3>
    
    <div v-if="!wizardData.model_id" style="background: #fff3cd; padding: 15px; border-radius: 8px; border: 1px solid #ffeaa7;">
      <p style="margin: 0;">{{ $t('no_ai_selected_no_instructions') }}</p>
    </div>

    <div v-else>
      <p>{{ $t('describe_ai_processing') }}</p>
      
      <div class="form-group">
        <textarea 
          :value="wizardData.system_content"
          @input="updateInstructions"
          :placeholder="$t('ai_instructions_placeholder')"
          style="width: 100%; height: 120px; padding: 15px; border: 1px solid #ccc; border-radius: 8px; font-family: inherit; resize: vertical;"
        ></textarea>
      </div>

      <div style="margin-top: 20px;">
        <h4>{{ $t('instruction_examples') }}</h4>
        <div class="examples">
          <div 
            v-for="example in examples" 
            :key="example.title"
            @click="useExample(example.content)"
            style="background: #f8f9fa; padding: 12px; margin: 8px 0; border-radius: 6px; cursor: pointer; border: 1px solid #e9ecef;"
          >
            <strong>{{ example.title }}:</strong>
            <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">{{ example.content }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';

export default defineComponent({
  name: 'SimpleInstructionsStep',
  props: {
    wizardData: {
      type: Object,
      required: true
    }
  },
  emits: ['update-data'],
  setup(props, { emit }) {
    const { t: $t } = useI18n();
    
    const examples = computed(() => [
      {
        title: $t('example_text_improvement'),
        content: $t('example_text_improvement_content')
      },
      {
        title: $t('example_summary'),
        content: $t('example_summary_content')
      },
      {
        title: $t('example_telegram_formatting'),
        content: $t('example_telegram_formatting_content')
      }
    ]);

    const updateInstructions = (event: Event) => {
      const target = event.target as HTMLTextAreaElement;
      emit('update-data', { system_content: target.value });
    };

    const useExample = (content: string) => {
      emit('update-data', { system_content: content });
    };

    // Auto-select first example when entering this step if AI is selected
    onMounted(() => {
      if (props.wizardData.model_id) {
        const firstExample = examples.value[0];
        if (firstExample) {
          emit('update-data', { system_content: firstExample.content });
        }
      }
    });

    return {
      examples,
      updateInstructions,
      useExample,
      $t
    };
  }
});
</script>

<style scoped>
.simple-instructions-step {
  padding: 20px;
}

.examples div:hover {
  background: #e9ecef !important;
}

/* Мобильная оптимизация */
@media (max-width: 768px) {
  .simple-instructions-step {
    padding: 15px;
  }
  
  .simple-instructions-step h3 {
    font-size: 18px;
    margin-bottom: 10px;
  }
  
  .simple-instructions-step p {
    font-size: 14px;
    margin-bottom: 15px;
  }
  
  .simple-instructions-step h4 {
    font-size: 16px;
    margin-bottom: 10px;
  }
  
  .form-group label {
    font-size: 13px !important;
    margin-bottom: 8px !important;
  }
  
  .simple-instructions-step textarea {
    font-size: 13px !important;
    padding: 12px !important;
    height: 100px !important;
  }
  
  .examples div {
    padding: 10px !important;
    margin: 6px 0 !important;
  }
  
  .examples div strong {
    font-size: 13px;
  }
  
  .examples div p {
    font-size: 12px !important;
    margin: 4px 0 0 0 !important;
  }
}
</style>