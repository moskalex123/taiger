import { LanguageService } from './language';
import { WebSocketService } from './websocket';

export class LanguageSyncService {
  private static instance: LanguageSyncService;
  private languageService: LanguageService;
  private wsService: WebSocketService;
  private syncInterval: number | null = null;

  static getInstance(): LanguageSyncService {
    if (!LanguageSyncService.instance) {
      LanguageSyncService.instance = new LanguageSyncService();
    }
    return LanguageSyncService.instance;
  }

  constructor() {
    this.languageService = LanguageService.getInstance();
    this.wsService = WebSocketService.getInstance();
  }

  // Initialize language synchronization
  init(): void {
    // Initialize WebSocket listener for language changes
    this.languageService.initWebSocketListener();
    
    // Start periodic sync check
    this.startPeriodicSync();
    
    // Listen for language changes in TMA
    this.setupTMAListener();
  }

  private startPeriodicSync(): void {
    // Check for language changes every 30 seconds
    this.syncInterval = setInterval(async () => {
      try {
        const currentLanguage = await this.languageService.getUserLanguage();
        const storedLanguage = localStorage.getItem('preferred_language');
        
        // If stored language differs from server language, update
        if (storedLanguage && storedLanguage !== currentLanguage) {
          console.log('Language mismatch detected, syncing...');
          await this.languageService.setUserLanguage(storedLanguage);
        }
      } catch (error) {
        console.error('Error during periodic language sync:', error);
      }
    }, 30000);
  }

  private setupTMAListener(): void {
    // Listen for language changes in TMA environment
    if (window.Telegram?.WebApp) {
      const webApp = window.Telegram.WebApp;
      
      // Simple periodic check for language changes
      setInterval(() => {
        this.syncLanguageFromTMA();
      }, 10000); // Check every 10 seconds
    }
  }

  private async syncLanguageFromTMA(): Promise<void> {
    try {
      // Get current language from server
      const serverLanguage = await this.languageService.getUserLanguage();
      const storedLanguage = localStorage.getItem('preferred_language');
      
      // If we have a stored language preference, sync it to server
      if (storedLanguage && storedLanguage !== serverLanguage) {
        console.log('Syncing TMA language preference to server:', storedLanguage);
        await this.languageService.setUserLanguage(storedLanguage);
      }
    } catch (error) {
      console.error('Error syncing language from TMA:', error);
    }
  }

  // Sync language from bot to TMA
  syncFromBot(languageCode: string): void {
    try {
      console.log('Syncing language from bot to TMA:', languageCode);
      this.languageService.setUserLanguage(languageCode);
      
      // Update UI theme if needed
      this.updateUITheme(languageCode);
    } catch (error) {
      console.error('Error syncing language from bot:', error);
    }
  }

  private updateUITheme(languageCode: string): void {
    // Update theme based on language if needed
    const body = document.body;
    
    // Remove existing theme classes
    body.classList.remove('tma-light-theme', 'tma-dark-theme');
    
    // Apply appropriate theme class
    if (languageCode === 'ru') {
      body.classList.add('tma-light-theme');
    } else {
      body.classList.add('tma-dark-theme');
    }
  }

  // Cleanup
  destroy(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }
}

// Auto-initialize when imported
const languageSyncService = LanguageSyncService.getInstance();
languageSyncService.init();

export default languageSyncService;