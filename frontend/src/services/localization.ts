import en from '../locales/en.json';
import ru from '../locales/ru.json';
import { LanguageService } from './language';

const translations: Record<string, any> = { en, ru };

export class LocalizationService {
  private static instance: LocalizationService;
  private languageService: LanguageService;
  private currentLanguage: string = 'en';
  private fallbackLanguage: string = 'en';
  private loadingLanguages: Set<string> = new Set();

  static getInstance(): LocalizationService {
    if (!LocalizationService.instance) {
      LocalizationService.instance = new LocalizationService();
    }
    return LocalizationService.instance;
  }

  constructor() {
    this.languageService = LanguageService.getInstance();
  }

  async init(): Promise<void> {
    try {
      // Initialize with current user language
      const userLanguage = await this.languageService.getUserLanguage();
      this.currentLanguage = userLanguage || this.fallbackLanguage;
      console.log('🎯 LocalizationService: Initialized with language:', this.currentLanguage);
      
      // Listen for language changes
      // Language changes will be handled by LanguageService automatically
      // We just need to update our current language when it changes
      this.currentLanguage = await this.languageService.getUserLanguage() || this.fallbackLanguage;
      console.log('🎯 LocalizationService: Final language after init:', this.currentLanguage);
    } catch (error) {
      console.error('Error initializing localization service:', error);
      // Fallback to English
      this.currentLanguage = this.fallbackLanguage;
    }
  }

  private async handleLanguageChange(newLanguage: string): Promise<void> {
    try {
      this.currentLanguage = newLanguage;
      
      // Update UI theme if needed
      this.updateUITheme(newLanguage);
    } catch (error) {
      console.error('Error handling language change:', error);
      // Fallback to current language
      this.currentLanguage = this.fallbackLanguage;
    }
  }

  t(key: string, params?: Record<string, any>): string {
    try {
      let translation = this.getTranslation(key);
      
      if (!translation) {
        console.warn(`Translation not found for key: ${key}`);
        return this.getFallbackTranslation(key);
      }
      
      // Replace parameters
      if (params) {
        translation = this.replaceParams(translation, params);
      }
      
      return translation;
    } catch (error) {
      console.error('Error translating key:', key, error);
      return this.getFallbackTranslation(key);
    }
  }

  private getTranslation(key: string): string | null {
    // Try current language first
    let translation = translations[this.currentLanguage as keyof typeof translations]?.[key];
    
    if (!translation) {
      // Try nested structure
      const keys = key.split('.');
      let current = translations[this.currentLanguage as keyof typeof translations];
      
      for (const k of keys) {
        if (current && typeof current === 'object' && k in current) {
          current = current[k];
        } else {
          current = null;
          break;
        }
      }
      
      translation = current;
    }
    
    return translation || null;
  }

  private getFallbackTranslation(key: string): string {
    // Try fallback language
    let translation = translations[this.fallbackLanguage as keyof typeof translations]?.[key];
    
    if (!translation) {
      // Try nested structure in fallback language
      const keys = key.split('.');
      let current = translations[this.fallbackLanguage as keyof typeof translations];
      
      for (const k of keys) {
        if (current && typeof current === 'object' && k in current) {
          current = current[k];
        } else {
          current = null;
          break;
        }
      }
      
      translation = current;
    }
    
    // Final fallback - return key
    return translation || key;
  }

  private replaceParams(translation: string, params: Record<string, any>): string {
    let result = translation;
    
    Object.keys(params).forEach(param => {
      const value = String(params[param] || '');
      result = result.replace(new RegExp(`{{${param}}}`, 'g'), value);
    });
    
    return result;
  }

  private updateUITheme(language: string): void {
    // Update theme based on language if needed
    const body = document.body;
    
    // Remove existing theme classes
    body.classList.remove('tma-light-theme', 'tma-dark-theme');
    
    // Apply appropriate theme class
    if (language === 'ru') {
      body.classList.add('tma-light-theme');
    } else {
      body.classList.add('tma-dark-theme');
    }
  }

  getCurrentLanguage(): string {
    return this.currentLanguage;
  }

  getAvailableLanguages(): string[] {
    return ['en', 'ru'];
  }

  setLanguage(language: string): void {
    if (this.getAvailableLanguages().includes(language)) {
      this.currentLanguage = language;
      this.updateUITheme(language);
    } else {
      console.warn(`Unsupported language: ${language}, falling back to ${this.fallbackLanguage}`);
      this.currentLanguage = this.fallbackLanguage;
    }
  }

  // Error handling methods
  async reloadTranslations(): Promise<void> {
    try {
      // Force reload by reinitializing
      await this.init();
    } catch (error) {
      console.error('Error reloading translations:', error);
      // Force fallback to English
      this.currentLanguage = this.fallbackLanguage;
    }
  }

  isTranslationLoaded(language: string): boolean {
    return !!translations[language as keyof typeof translations];
  }

  getTranslationStats(): { loaded: string[], loading: string[], current: string } {
    return {
      loaded: Object.keys(translations),
      loading: Array.from(this.loadingLanguages),
      current: this.currentLanguage
    };
  }
}