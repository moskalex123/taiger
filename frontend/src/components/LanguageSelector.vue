<template>
  <div class="language-selector">
    <select
      v-model="selectedLanguage"
      @change="changeLanguage"
      class="language-select"
    >
      <option value="en">EN</option>
      <option value="ru">RU</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { LanguageService } from '@/services/language';

const languageService = LanguageService.getInstance();
const selectedLanguage = ref('en');

onMounted(async () => {
  selectedLanguage.value = await languageService.getUserLanguage();
});

const changeLanguage = async () => {
  try {
    await languageService.setUserLanguage(selectedLanguage.value);
    // Reload the application to apply the new language
    window.location.reload();
  } catch (error) {
    console.error('Failed to change language:', error);
    // Revert selection on error
    selectedLanguage.value = await languageService.getUserLanguage();
  }
};
</script>

<style scoped>
.language-selector {
  display: flex;
  align-items: center;
}

.language-select {
  background: transparent;
  border: 1px solid var(--tg-theme-hint-color, #666);
  color: var(--tg-theme-text-color, #000);
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  min-width: 60px;
}

.language-select:focus {
  outline: none;
  border-color: var(--tg-theme-link-color, #0088cc);
}

.language-select option {
  background: var(--tg-theme-bg-color, #fff);
  color: var(--tg-theme-text-color, #000);
}
</style>