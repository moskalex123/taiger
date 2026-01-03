<template>
  <span 
    :class="['price-display', priceClass]"
  >
    {{ formattedPrice }}
  </span>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  // Цена в USD (базовая валюта)
  price: {
    type: Number,
    required: true,
    default: 0
  },
  
  // Количество знаков после запятой
  decimals: {
    type: Number,
    default: null
  },
  
  // CSS класс для стилизации
  priceClass: {
    type: String,
    default: ''
  }
});

// Форматированная цена без конвертации валют
const formattedPrice = computed(() => {
  const finalDecimals = props.decimals !== null ? props.decimals : 3;
  const formatted = (props.price || 0).toFixed(finalDecimals);
  return `${formatted}`;
});
</script>

<style scoped>
.price-display {
  font-weight: 500;
  white-space: nowrap;
}

.price-display.small {
  font-size: 0.875rem;
}

.price-display.normal {
  font-size: 1rem;
}

.price-display.large {
  font-size: 1.25rem;
}

/* Цветовые классы для разных типов цен */
.price-display.balance-positive {
  color: #28a745;
}

.price-display.balance-negative {
  color: #dc3545;
}

.price-display.balance-warning {
  color: #ffc107;
}

.price-display.model-price {
  color: #007bff;
}

.price-display.muted {
  color: #6c757d;
}

/* Анимация при обновлении */
.price-display.updated {
  animation: priceUpdate 0.5s ease-in-out;
}

@keyframes priceUpdate {
  0% { 
    background-color: rgba(40, 167, 69, 0.2);
    transform: scale(1);
  }
  50% { 
    background-color: rgba(40, 167, 69, 0.4);
    transform: scale(1.05);
  }
  100% { 
    background-color: transparent;
    transform: scale(1);
  }
}
</style>