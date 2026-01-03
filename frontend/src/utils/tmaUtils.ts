/**
 * TMA (Telegram Mini App) utilities for debugging and logging
 */

/**
 * Check if TMA debug logging is enabled
 */
export const isTmaDebugEnabled = (): boolean => {
  return localStorage.getItem('tma_debug_logs') === 'true';
};

/**
 * Conditional TMA debug logging - only logs when tma_debug_logs flag is enabled
 */
export const tmaLog = (...args: any[]): void => {
  if (isTmaDebugEnabled()) {
    console.debug('[TMA]', ...args);
  }
};

/**
 * Mask sensitive token data for logging
 */
export const maskToken = (token?: string | null): string => {
  return token ? `${token.substring(0, 20)}...` : 'NO TOKEN';
};

/**
 * Mask initData for logging (shows first 50 characters)
 */
export const maskInitData = (initData?: string | null): string => {
  return initData ? `${initData.substring(0, 50)}...` : 'NO INIT DATA';
};