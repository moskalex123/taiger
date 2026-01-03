// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Telegram Configuration
export const TELEGRAM_BOT_USERNAME = import.meta.env.VITE_TELEGRAM_BOT_USERNAME || 'taiger_bot';

// Export all as default
export default {
  API_BASE_URL,
  TELEGRAM_BOT_USERNAME
};