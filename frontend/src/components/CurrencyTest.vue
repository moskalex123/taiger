<template>
  <div class="currency-test">
    <h2>Тест отображения валют</h2>
    
    <div class="test-section">
      <h3>Текущая локаль: {{ locale }}</h3>
      <p>Курс USD/RUB: {{ currentRate.toFixed(2) }}</p>
      <p>Последнее обновление: {{ lastUpdated ? new Date(lastUpdated).toLocaleString() : 'Не обновлялось' }}</p>
      <button @click="fetchExchangeRate" :disabled="isLoading">
        {{ isLoading ? 'Обновляется...' : 'Обновить курс' }}
      </button>
    </div>

    <div class="test-section">
      <h3>Примеры цен:</h3>
      <div class="price-examples">
        <div class="price-example">
          <span>$0.008 → </span>
          <PriceDisplay :price="0.008" :decimals="3" />
        </div>
        <div class="price-example">
          <span>$0.039 → </span>
          <PriceDisplay :price="0.039" :decimals="3" />
        </div>
        <div class="price-example">
          <span>$2.968 → </span>
          <PriceDisplay :price="2.968" :decimals="3" :show-exchange-info="true" />
        </div>
        <div class="price-example">
          <span>$0.024 → </span>
          <PriceDisplay :price="0.024" :decimals="3" price-class="model-price" />
        </div>
      </div>
    </div>

    <div class="test-section">
      <h3>Переключение языка:</h3>
      <button @click="switchLocale('en')">English</button>
      <button @click="switchLocale('ru')">Русский</button>
    </div>
  </div>
</template>

<script>
import { defineComponent } from 'vue';
import { useI18n } from 'vue-i18n';
import { useExchangeRate } from '../composables/useExchangeRate';
import PriceDisplay from './PriceDisplay.vue';

export default defineComponent({
  name: 'CurrencyTest',
  components: {
    PriceDisplay
  },
  setup() {
    const { locale } = useI18n();
    const {
      initializeExchangeRate,
      fetchExchangeRate,
      currentRate,
      lastUpdated,
      isLoading
    } = useExchangeRate();

    const switchLocale = (newLocale) => {
      locale.value = newLocale;
    };

    // Инициализируем курс при загрузке
    initializeExchangeRate();

    return {
      locale,
      currentRate,
      lastUpdated,
      isLoading,
      fetchExchangeRate,
      switchLocale
    };
  }
});
</script>

<style scoped>
.currency-test {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.test-section {
  margin: 20px 0;
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 8px;
  background: #f9f9f9;
}

.price-examples {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.price-example {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  background: white;
  border-radius: 4px;
}

button {
  padding: 8px 16px;
  margin: 5px;
  border: 1px solid #007bff;
  background: #007bff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
}

button:hover {
  background: #0056b3;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>