import api from './api';
import { WebSocketService } from './websocket';

export class LanguageService {
  private static instance: LanguageService;
  private currentLanguage: string = 'en';
  private languageChangeCallbacks: Array<(language: string) => void> = [];

  static getInstance(): LanguageService {
    if (!LanguageService.instance) {
      LanguageService.instance = new LanguageService();
    }
    return LanguageService.instance;
  }

  async getUserLanguage(): Promise<string> {
    try {
      console.log('🎯 LanguageService: Attempting to get user language from API...');
      const response = await api.get('/users/me/language');
      this.currentLanguage = response.data.language_code;
      console.log('🎯 LanguageService: Got user language from API:', this.currentLanguage);
      return this.currentLanguage;
    } catch (error) {
      console.error('Failed to get user language:', error);
      // Fallback to browser language or English
      const browserLang = navigator.language?.split('-')[0] || 'en';
      console.log('🎯 LanguageService: Using browser language as fallback:', browserLang);
      return browserLang; // fallback
    }
  }

  async setUserLanguage(languageCode: string): Promise<void> {
    try {
      await api.post('/users/me/language', { language_code: languageCode });
      this.currentLanguage = languageCode;
      // Update localStorage for persistence
      localStorage.setItem('preferred_language', languageCode);

      // Notify all subscribers about language change
      this.notifyLanguageChange(languageCode);

      // Broadcast language change to other instances via WebSocket
      this.broadcastLanguageChange(languageCode);
    } catch (error) {
      console.error('Failed to set user language:', error);
      throw error;
    }
  }

  getCurrentLanguage(): string {
    return this.currentLanguage;
  }

  subscribeToLanguageChanges(callback: (language: string) => void): () => void {
    this.languageChangeCallbacks.push(callback);
    
    // Return unsubscribe function
    return () => {
      const index = this.languageChangeCallbacks.indexOf(callback);
      if (index > -1) {
        this.languageChangeCallbacks.splice(index, 1);
      }
    };
  }

  private notifyLanguageChange(language: string): void {
    this.languageChangeCallbacks.forEach(callback => {
      try {
        callback(language);
      } catch (error) {
        console.error('Error in language change callback:', error);
      }
    });
  }

  private broadcastLanguageChange(language: string): void {
    try {
      const wsService = WebSocketService.getInstance();
      if (wsService.isConnected()) {
        wsService.send({
          type: 'language_change',
          data: {
            language_code: language,
            timestamp: Date.now()
          }
        });
      }
    } catch (error) {
      console.error('Failed to broadcast language change:', error);
    }
  }

  // Initialize WebSocket listener for language changes
  initWebSocketListener(): void {
    const wsService = WebSocketService.getInstance();
    
    wsService.on('language_change', (data: any) => {
      if (data && data.language_code && data.language_code !== this.currentLanguage) {
        this.currentLanguage = data.language_code;
        this.notifyLanguageChange(data.language_code);
      }
    });
  }
}