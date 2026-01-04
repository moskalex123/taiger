import { tmaLog, maskToken, maskInitData } from '../utils/tmaUtils';

export interface TelegramWebApp {
  initData: string;
  initDataUnsafe: any;
  version: string;
  platform: string;
  colorScheme: 'light' | 'dark';
  themeParams: any;
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  isClosingConfirmationEnabled: boolean;
  
  ready(): void;
  expand(): void;
  close(): void;
  enableClosingConfirmation(): void;
  disableClosingConfirmation(): void;
  showAlert(message: string, callback?: () => void): void;
  showConfirm(message: string, callback?: (confirmed: boolean) => void): void;
  showPopup(params: any, callback?: (button_id: string) => void): void;
  
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    isProgressVisible: boolean;
    setText(text: string): void;
    onClick(callback: () => void): void;
    show(): void;
    hide(): void;
    enable(): void;
    disable(): void;
    showProgress(leaveActive?: boolean): void;
    hideProgress(): void;
  };
  
  BackButton: {
    isVisible: boolean;
    onClick(callback: () => void): void;
    show(): void;
    hide(): void;
  };
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp;
    };
  }
}

class TMAService {
  private webApp: TelegramWebApp | null = null;
  private isInitialized = false;
  private isAuthenticating = false;
  private authPromise: Promise<any> | null = null;
  private lastValidationTime = 0;
  private validationCooldown = 1000; // 1 second cooldown
  private tokenRefreshInProgress = false; // Flag to signal token refresh is happening
  
  get isTMA(): boolean {
    const hasTelegram = !!(window.Telegram && window.Telegram.WebApp);
    const hasInitData = hasTelegram && !!window.Telegram?.WebApp?.initData;
    const hasUser = hasTelegram && !!window.Telegram?.WebApp?.initDataUnsafe?.user;

    // Development mode: check for debug flag
    const isDebugMode = localStorage.getItem('tma_debug_mode') === 'true';

    // In production, we want to allow both TMA and regular web access
    // For TMA, we require both initData and user data to be present
    return (hasTelegram && hasInitData && hasUser) || isDebugMode;
  }
  
  get isReady(): boolean {
    return this.isInitialized && this.webApp !== null;
  }
  
  async initialize(): Promise<boolean> {
    // If not in TMA environment, we still want the app to work
    if (!this.isTMA) {
      tmaLog('Not in TMA environment, initializing in web mode');
      this.isInitialized = true;
      return true;
    }
    
    this.webApp = window.Telegram!.WebApp;
    
    // Configure WebApp
    this.webApp.ready();
    this.webApp.expand();
    this.webApp.enableClosingConfirmation();
    
    // Set theme colors
    this.applyTelegramTheme();
    
    // Configure main button for worker controls
    this.configureMainButton();
    
    this.isInitialized = true;
    return true;
  }
  
  private applyTelegramTheme(): void {
    if (!this.webApp) return;
    
    // Add TMA body class for styling
    document.body.classList.add('tma-environment');
    
    // Check if user has a saved theme preference and apply it
    const savedTheme = localStorage.getItem('preferred_theme') || 'auto'
    this.applyThemeFromPreference(savedTheme)
  }
  
  private applyThemeFromPreference(theme: string): void {
    const body = document.body;
    
    // Remove existing theme classes
    body.classList.remove('tma-light-theme', 'tma-dark-theme');
    
    if (theme === 'dark') {
      body.classList.add('tma-dark-theme');
      this.setTMAColors('dark');
    } else if (theme === 'light') {
      body.classList.add('tma-light-theme');
      this.setTMAColors('light');
    } else {
      // Auto theme - use system preference
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (systemDark) {
        body.classList.add('tma-dark-theme');
        this.setTMAColors('dark');
      } else {
        body.classList.add('tma-light-theme');
        this.setTMAColors('light');
      }
    }
  }
  
  private setTMAColors(theme: 'light' | 'dark'): void {
    const root = document.documentElement;
    const body = document.body;
    
    if (theme === 'dark') {
      root.style.setProperty('--tg-theme-bg-color', '#1a1a1a');
      root.style.setProperty('--tg-theme-text-color', '#ffffff');
      root.style.setProperty('--tg-theme-hint-color', '#b0b0b0');
      root.style.setProperty('--tg-theme-link-color', '#64b5f6');
      root.style.setProperty('--tg-theme-button-color', '#64b5f6');
      root.style.setProperty('--tg-theme-button-text-color', '#000000');
      
      body.style.backgroundColor = '#1a1a1a';
      body.style.color = '#ffffff';
    } else {
      root.style.setProperty('--tg-theme-bg-color', '#ffffff');
      root.style.setProperty('--tg-theme-text-color', '#1a1a1a');
      root.style.setProperty('--tg-theme-hint-color', '#666666');
      root.style.setProperty('--tg-theme-link-color', '#0088cc');
      root.style.setProperty('--tg-theme-button-color', '#0088cc');
      root.style.setProperty('--tg-theme-button-text-color', '#ffffff');
      
      body.style.backgroundColor = '#ffffff';
      body.style.color = '#1a1a1a';
    }
  }
  
  private configureMainButton(): void {
    if (!this.webApp) return;
    
    const mainButton = this.webApp.MainButton;
    mainButton.setText('Worker Controls');
    mainButton.hide(); // Initially hidden, shown when needed
  }
  
  getInitData(): string {
    // Development mode: return mock data if debug mode is enabled
    if (localStorage.getItem('tma_debug_mode') === 'true') {
      const mockInitData = 'auth_date=1694680000&hash=mock_hash&user=%7B%22id%22%3A123456789%2C%22first_name%22%3A%22Test%22%2C%22username%22%3A%22testuser%22%2C%22language_code%22%3A%22en%22%7D';
      return mockInitData;
    }
    
    return this.webApp?.initData || '';
  }
  
  showMainButton(text: string, onClick: () => void): void {
    if (!this.webApp) return;
    
    const mainButton = this.webApp.MainButton;
    mainButton.setText(text);
    mainButton.onClick(onClick);
    mainButton.show();
  }
  
  hideMainButton(): void {
    if (this.webApp) {
      this.webApp.MainButton.hide();
    }
  }
  
  showAlert(message: string): Promise<void> {
    return new Promise((resolve) => {
      if (this.webApp) {
        this.webApp.showAlert(message, () => resolve());
      } else {
        alert(message);
        resolve();
      }
    });
  }
  
  showConfirm(message: string): Promise<boolean> {
    return new Promise((resolve) => {
      if (this.webApp) {
        this.webApp.showConfirm(message, (confirmed) => resolve(confirmed));
      } else {
        resolve(confirm(message));
      }
    });
  }
  
  close(): void {
    if (this.webApp) {
      this.webApp.close();
    }
  }

  // Check if token refresh is currently in progress
  get isRefreshingToken(): boolean {
    return this.tokenRefreshInProgress;
  }

  // Get current auth token (returns existing token even during refresh)
  getCurrentToken(): string | null {
    return localStorage.getItem('auth_token');
  }

  // Authentication-related methods
  async authenticateWithBackend(forceRefresh: boolean = false): Promise<any> {
    // If not in TMA, try to get token from localStorage or cookies
    if (!this.isTMA) {
      tmaLog('Not in TMA environment, checking for existing token');
      
      // First try localStorage
      let token = localStorage.getItem('auth_token');
      
      // If no token in localStorage, try cookies
      if (!token) {
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
          const [name, value] = cookie.trim().split('=');
          if (name === 'access_token' && value) {
            token = decodeURIComponent(value);
            // Store in localStorage for API interceptor
            localStorage.setItem('auth_token', token);
            tmaLog('Retrieved token from cookies and stored in localStorage');
            break;
          }
        }
      }
      
      if (token) {
        tmaLog('Found existing token in browser mode');
        return { access_token: token };
      }
      
      tmaLog('No token found in browser mode');
      return null;
    }
    
    // Prevent multiple simultaneous authentication attempts
    if (this.isAuthenticating && this.authPromise && !forceRefresh) {
      tmaLog('Authentication already in progress, waiting...');
      return await this.authPromise;
    }
    
    // Check if we already have a valid token (skip if force refresh)
    if (!forceRefresh) {
      const existingToken = localStorage.getItem('auth_token');
      if (existingToken) {
        // Verify token is still valid by checking user data
        try {
          const userResponse = await fetch('/api/users/me', {
            headers: { 'Authorization': `Bearer ${existingToken}` }
          });
          if (userResponse.ok) {
            tmaLog('Valid token already exists, skipping authentication');
            return { access_token: existingToken };
          } else {
            tmaLog('Existing token invalid, will re-authenticate');
            // DON'T remove token here - keep it until new one is obtained
          }
        } catch (error) {
          tmaLog('Token validation failed, will re-authenticate');
          // DON'T remove token here - keep it until new one is obtained
        }
      }
    } else {
      tmaLog('Force refresh requested, will obtain new token');
      // DON'T remove token here - keep it until new one is obtained
    }
    
    this.isAuthenticating = true;
    this.tokenRefreshInProgress = true;
    
    this.authPromise = this._performAuthentication();
    
    try {
      const result = await this.authPromise;
      return result;
    } finally {
      this.isAuthenticating = false;
      this.tokenRefreshInProgress = false;
      this.authPromise = null;
    }
  }
  
  private async _performAuthentication(): Promise<any> {
    const initData = this.getInitData();
    
    tmaLog('Starting authentication...');
    
    if (!initData) {
      // Don't throw immediately - keep existing token if we have one
      const existingToken = localStorage.getItem('auth_token');
      if (existingToken) {
        tmaLog('No Telegram init data available, but existing token found - keeping it');
        return { access_token: existingToken };
      }
      throw new Error('No Telegram init data available');
    }

    try {
      tmaLog('Sending auth request to backend...');
      const response = await fetch('/api/telegram/auth', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          init_data: initData
        })
      });

      if (!response.ok) {
        // If auth fails, keep existing token if we have one
        const existingToken = localStorage.getItem('auth_token');
        if (existingToken) {
          tmaLog(`Authentication request failed (${response.status}), but keeping existing token`);
          return { access_token: existingToken };
        }
        throw new Error(`Authentication failed: ${response.statusText}`);
      }

      const authData = await response.json();
      tmaLog('Auth response received:', { ...authData, access_token: maskToken(authData.access_token) });
      
      // Store JWT token - this atomically replaces the old one
      tmaLog('Storing new token in localStorage...');
      localStorage.setItem('auth_token', authData.access_token);
      
      // Verify token was stored
      const storedToken = localStorage.getItem('auth_token');
      tmaLog('Token verification - stored successfully:', !!storedToken);
      if (storedToken) {
        tmaLog('Token preview:', maskToken(storedToken));
      }
      
      tmaLog('Authentication completed successfully');
      return authData;
    } catch (error) {
      console.error('TMA authentication failed:', error);
      // On error, keep existing token if available
      const existingToken = localStorage.getItem('auth_token');
      if (existingToken) {
        tmaLog('Authentication failed, but keeping existing token');
        return { access_token: existingToken };
      }
      throw error;
    }
  }

  // Worker control methods for main button
  async startWorker(): Promise<void> {
    try {
      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/workers/start', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error('Failed to start worker');
      }

      await this.showAlert('Worker started successfully!');
    } catch (error: any) {
      await this.showAlert(`Failed to start worker: ${error?.message || 'Unknown error'}`);
    }
  }

  async stopWorker(): Promise<void> {
    try {
      const confirmed = await this.showConfirm('Are you sure you want to stop the worker?');
      if (!confirmed) return;

      const token = localStorage.getItem('auth_token');
      const response = await fetch('/api/workers/stop', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        }
      });

      if (!response.ok) {
        throw new Error('Failed to stop worker');
      }

      await this.showAlert('Worker stopped successfully!');
    } catch (error: any) {
      await this.showAlert(`Failed to stop worker: ${error?.message || 'Unknown error'}`);
    }
  }

  // Set up main button based on worker status
  setupWorkerControls(workerStatus: string): void {
    if (!this.webApp) return;

    switch (workerStatus) {
      case 'running':
      case 'active':
        this.showMainButton('Stop Worker', () => this.stopWorker());
        break;
      case 'stopped':
      case 'error':
        this.showMainButton('Start Worker', () => this.startWorker());
        break;
      default:
        this.hideMainButton();
    }
  }

  // Force refresh user data (for account switching)
  async refreshUserData(): Promise<any> {
    tmaLog('Force refreshing user data due to potential account switch');
    // Only force refresh if we're not already refreshing
    if (this.tokenRefreshInProgress) {
      tmaLog('Token refresh already in progress, waiting...');
      if (this.authPromise) {
        return await this.authPromise;
      }
    }
    return await this.authenticateWithBackend(true);
  }

  // Check if current user matches expected user ID
  async validateCurrentUser(expectedUserId?: number): Promise<boolean> {
    // If not in TMA, we might not need to validate user ID
    if (!this.isTMA) return true;

    if (!expectedUserId) return true;

    // Cooldown protection to prevent excessive API calls
    const now = Date.now();
    if (now - this.lastValidationTime < this.validationCooldown) {
      tmaLog('Validation cooldown active, skipping');
      return true; // Assume valid during cooldown
    }
    this.lastValidationTime = now;

    try {
      tmaLog(`Starting validation for user ${expectedUserId}`);
      // Validate via API
      const token = localStorage.getItem('auth_token');
      if (!token) {
        tmaLog('No token available for validation');
        return false;
      }

      tmaLog('Making API call to /api/users/me');
      const response = await fetch('/api/users/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        tmaLog(`API validation failed with status ${response.status}`);
        return false;
      }

      const userData = await response.json();
      const apiUserId = userData.id;
      tmaLog(`API returned user ID ${apiUserId}, expected ${expectedUserId}`);

      if (apiUserId !== expectedUserId) {
        tmaLog('User ID mismatch detected via API');
        return false;
      }

      // Check telegram_id match for account switch detection
      if (this.webApp?.initDataUnsafe?.user?.id) {
        const currentTmaTelegramId = this.webApp.initDataUnsafe.user.id;
        const apiTelegramId = userData.telegram_id;
        tmaLog(`TMA telegram ID: ${currentTmaTelegramId}, API telegram ID: ${apiTelegramId}`);
        if (currentTmaTelegramId != apiTelegramId) {
          tmaLog('Telegram ID mismatch detected - possible account switch');
          return false;
        }
      } else {
        tmaLog('No initData available for telegram_id check');
      }

      tmaLog('Validation passed');
      return true;
    } catch (error) {
      console.error('TMA: User validation failed:', error);
      return false;
    }
  }

  // Get current user ID from TMA initData
  getCurrentTMAUserId(): number | null {
    try {
      if (this.webApp?.initDataUnsafe?.user?.id) {
        return this.webApp.initDataUnsafe.user.id;
      }
      return null;
    } catch (error) {
      console.error('TMA: Failed to get current TMA user ID:', error);
      return null;
    }
  }

  // Check if initData has changed (more aggressive detection)
  hasInitDataChanged(lastKnownInitData?: string): boolean {
    try {
      const currentInitData = this.getInitData();
      if (!lastKnownInitData) return false;
      
      const hasChanged = currentInitData !== lastKnownInitData;
      if (hasChanged) {
        tmaLog('InitData change detected');
        tmaLog('Old initData preview:', maskInitData(lastKnownInitData));
        tmaLog('New initData preview:', maskInitData(currentInitData));
      }
      
      return hasChanged;
    } catch (error) {
      console.error('TMA: Failed to check initData changes:', error);
      return false;
    }
  }
}

export const tmaService = new TMAService();