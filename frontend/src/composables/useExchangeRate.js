import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

// Глобальное состояние для курса валют
const exchangeRates = ref({
  USD_RUB: 95.0, // Fallback курс
  lastUpdated: null,
  isLoading: false
});

export function useExchangeRate() {
  const { locale } = useI18n();

  // Проверяем, нужно ли обновить курс (раз в день)
  const shouldUpdateRate = () => {
    if (!exchangeRates.value.lastUpdated) return true;
    
    const lastUpdate = new Date(exchangeRates.value.lastUpdated);
    const now = new Date();
    const diffHours = (now - lastUpdate) / (1000 * 60 * 60);
    
    // Обновляем курс каждые 6 часов
    return diffHours >= 6;
  };

  // Получаем курс от ЦБ РФ
  const fetchExchangeRate = async () => {
    if (exchangeRates.value.isLoading) return;
    
    exchangeRates.value.isLoading = true;
    
    try {
      console.log('Fetching exchange rate from CBR...');
      
      // Используем API ЦБ РФ
      const response = await fetch('https://www.cbr-xml-daily.ru/daily_json.js');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.Valute && data.Valute.USD && data.Valute.USD.Value) {
        const rate = data.Valute.USD.Value;
        exchangeRates.value.USD_RUB = rate;
        exchangeRates.value.lastUpdated = new Date().toISOString();
        
        // Сохраняем в localStorage
        localStorage.setItem('exchangeRates', JSON.stringify({
          USD_RUB: rate,
          lastUpdated: exchangeRates.value.lastUpdated
        }));
        
        console.log(`Exchange rate updated: 1 USD = ${rate} RUB`);
      } else {
        throw new Error('Invalid response format from CBR API');
      }
    } catch (error) {
      console.warn('Failed to fetch exchange rate from CBR, trying fallback...', error);
      
      // Пробуем альтернативный API
      try {
        const fallbackResponse = await fetch('https://api.exchangerate-api.com/v4/latest/USD');
        const fallbackData = await fallbackResponse.json();
        
        if (fallbackData.rates && fallbackData.rates.RUB) {
          const rate = fallbackData.rates.RUB;
          exchangeRates.value.USD_RUB = rate;
          exchangeRates.value.lastUpdated = new Date().toISOString();
          
          localStorage.setItem('exchangeRates', JSON.stringify({
            USD_RUB: rate,
            lastUpdated: exchangeRates.value.lastUpdated
          }));
          
          console.log(`Exchange rate updated from fallback API: 1 USD = ${rate} RUB`);
        }
      } catch (fallbackError) {
        console.error('All exchange rate APIs failed, using cached/fallback rate:', fallbackError);
      }
    } finally {
      exchangeRates.value.isLoading = false;
    }
  };

  // Загружаем курс из localStorage при инициализации
  const loadCachedRate = () => {
    try {
      const cached = localStorage.getItem('exchangeRates');
      if (cached) {
        const parsedCache = JSON.parse(cached);
        if (parsedCache.USD_RUB && parsedCache.lastUpdated) {
          exchangeRates.value.USD_RUB = parsedCache.USD_RUB;
          exchangeRates.value.lastUpdated = parsedCache.lastUpdated;
          console.log(`Loaded cached exchange rate: 1 USD = ${parsedCache.USD_RUB} RUB`);
        }
      }
    } catch (error) {
      console.warn('Failed to load cached exchange rate:', error);
    }
  };

  // Инициализация курса
  const initializeExchangeRate = async () => {
    loadCachedRate();
    
    if (shouldUpdateRate()) {
      await fetchExchangeRate();
    }
  };

  // Конвертация USD в RUB
  const convertUsdToRub = (usdAmount) => {
    if (!usdAmount || usdAmount === 0) return 0;
    return usdAmount * exchangeRates.value.USD_RUB;
  };

  // Форматирование цены в зависимости от локали
  const formatPrice = (usdPrice, options = {}) => {
    if (!usdPrice || usdPrice === 0) {
      return locale.value === 'ru' ? '0₽' : '$0';
    }

    const {
      showCurrency = true,
      decimals = null
    } = options;

    if (locale.value === 'ru') {
      const rubPrice = convertUsdToRub(usdPrice);
      const finalDecimals = decimals !== null ? decimals : (rubPrice >= 1 ? 2 : 3);
      const formatted = rubPrice.toFixed(finalDecimals);
      return showCurrency ? `${formatted}₽` : formatted;
    } else {
      const finalDecimals = decimals !== null ? decimals : 3;
      const formatted = usdPrice.toFixed(finalDecimals);
      return showCurrency ? `$${formatted}` : formatted;
    }
  };

  // Получение символа валюты
  const getCurrencySymbol = () => {
    return locale.value === 'ru' ? '₽' : '$';
  };

  // Получение названия валюты
  const getCurrencyName = () => {
    return locale.value === 'ru' ? 'RUB' : 'USD';
  };

  // Computed свойства
  const currentRate = computed(() => exchangeRates.value.USD_RUB);
  const isRussianLocale = computed(() => locale.value === 'ru');
  const lastUpdated = computed(() => exchangeRates.value.lastUpdated);
  const isLoading = computed(() => exchangeRates.value.isLoading);

  return {
    // Методы
    initializeExchangeRate,
    fetchExchangeRate,
    convertUsdToRub,
    formatPrice,
    getCurrencySymbol,
    getCurrencyName,
    
    // Computed свойства
    currentRate,
    isRussianLocale,
    lastUpdated,
    isLoading
  };
}