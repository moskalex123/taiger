import { createApp } from 'vue'
import { createI18n } from 'vue-i18n'
import App from './App.vue'
import './style.css'
import './mobile.css'
import './tma.css'  // Add TMA styles
import './redesign.css'  // Add redesigned UI styles
import Cookies from 'js-cookie'
import { tmaService } from './services/tma'

// Import translations
import en from './locales/en.json'
import ru from './locales/ru.json'
import { LocalizationService } from './services/localization'
import { LanguageService } from './services/language'

// Wait for Telegram WebApp script to load (used only in TMA mode)
function waitForTelegramWebApp(): Promise<void> {
  return new Promise((resolve) => {
    if (window.Telegram && window.Telegram.WebApp) {
      resolve();
      return;
    }

    const checkTelegram = () => {
      if (window.Telegram && window.Telegram.WebApp) {
        resolve();
      } else {
        setTimeout(checkTelegram, 100);
      }
    };

    setTimeout(checkTelegram, 100);
  });
}

// Initialize TMA service only when in TMA environment
async function initializeTMA() {
  if (!tmaService.isTMA) {
    return;
  }
  try {
    await waitForTelegramWebApp();
    await tmaService.initialize();
  } catch (error) {
    console.error('TMA initialization failed:', error);
  }
}

// Get saved language from localStorage, cookies, or default to Russian
let savedLanguage = localStorage.getItem('preferred_language') || Cookies.get('language');

let appInitialized = false;

// Initialize the app; don't block web-mode on Telegram availability
async function initializeApp() {
  // Prevent double-mount (this was causing inconsistent UI state in production)
  if (appInitialized) {
    return;
  }
  appInitialized = true;

  // In TMA mode, try to get language from multiple sources
  if (tmaService.isTMA) {
    // Don't hang forever if Telegram script is slow/broken
    await Promise.race([
      waitForTelegramWebApp(),
      new Promise<void>((resolve) => setTimeout(resolve, 3000))
    ]);
    
    // Try to get language from multiple sources, but prioritize API response
    let detectedLanguage = null;
    
    // 1. Try browser language first (more reliable than Telegram)
    if (navigator.language) {
      detectedLanguage = navigator.language.split('-')[0];
      console.log('🎯 TMA: Detected language from browser:', detectedLanguage);
    }
    
    // 2. Try system language
    if (!detectedLanguage && navigator.languages && navigator.languages.length > 0) {
      detectedLanguage = navigator.languages[0].split('-')[0];
      console.log('🎯 TMA: Detected language from system:', detectedLanguage);
    }
    
    // 3. Try Telegram WebApp user language (less reliable)
    if (!detectedLanguage && window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code) {
      detectedLanguage = window.Telegram.WebApp.initDataUnsafe.user.language_code;
      console.log('🎯 TMA: Detected language from Telegram user:', detectedLanguage);
    }
    
    // 4. Try Telegram WebApp language
    if (!detectedLanguage && window.Telegram?.WebApp?.initDataUnsafe?.language_code) {
      detectedLanguage = window.Telegram.WebApp.initDataUnsafe.language_code;
      console.log('🎯 TMA: Detected language from Telegram initData:', detectedLanguage);
    }
    
    if (detectedLanguage) {
      savedLanguage = detectedLanguage;
    }
  }

  // Fallback to English if no language detected
  savedLanguage = savedLanguage || 'en';
  console.log('🎯 main.ts: Final savedLanguage before creating i18n:', savedLanguage);

  // Create i18n instance
  const i18n = createI18n({
    legacy: false,
    locale: savedLanguage,
    fallbackLocale: 'en',
    messages: {
      en,
      ru
    }
  });
  
  console.log('🎯 main.ts: Created i18n instance with locale:', savedLanguage);

  // Initialize localization service
  const localizationService = LocalizationService.getInstance();
  localizationService.setLanguage(savedLanguage);
  console.log('🎯 main.ts: Set localization service language to:', savedLanguage);

  // Initialize language service
  const languageService = LanguageService.getInstance();
  console.log('🎯 main.ts: Language service instance created');

  const app = createApp(App);
  app.use(i18n);

  // Initialize TMA (no-op in web mode)
  await initializeTMA();

  // Initialize language service after TMA is ready
  try {
    const apiLanguage = await languageService.getUserLanguage();
    console.log('🎯 main.ts: Language service initialized successfully with language:', apiLanguage);
    
    // If API returned a different language than what we detected, update i18n
    if (apiLanguage && apiLanguage !== savedLanguage) {
      console.log('🎯 main.ts: API language differs from detected language, updating i18n...');
      // Type assertion to handle TypeScript error
      i18n.global.locale.value = apiLanguage as 'en' | 'ru';
      localizationService.setLanguage(apiLanguage);
      savedLanguage = apiLanguage;
      console.log('🎯 main.ts: Updated i18n locale to:', apiLanguage);
    }
  } catch (error) {
    console.error('🎯 main.ts: Error initializing language service:', error);
  }

  app.mount('#app');
}

// Start the application
initializeApp().catch(console.error);
