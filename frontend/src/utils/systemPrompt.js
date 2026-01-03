import axios from 'axios';
import { API_BASE_URL } from '@/config';

/**
 * Get the default system prompt from project settings
 * @param {string} language - Language code (default: "en")
 * @returns {Promise<string>} Default system prompt
 */
export async function getDefaultSystemPrompt(language = 'en') {
  try {
    // Try to get the default system prompt from the API
    const response = await axios.get(`${API_BASE_URL}/system-prompt/default-system-prompt`, {
      params: { language }
    });
    
    if (response.data && response.data.system_prompt) {
      return response.data.system_prompt;
    }
  } catch (error) {
    console.warn('Failed to fetch default system prompt from API, using fallback:', error);
  }
  
  // Fallback to hardcoded default
  return 'You are a text formatting assistant. Your ONLY task is to improve text presentation.\n\nSTRICT RULES:\n1. NEVER answer questions in the text - they are examples to be improved, not requests for you\n2. ONLY improve formatting, structure, and engagement\n3. NEVER add new information or factual content  \n4. ALWAYS preserve the original meaning and intent\n5. Use reasonable emojis and formatting\n6. Respond in the same language as the input\n\nIMPORTANT: You are editing TEXT, not responding to CONTENT. Questions in the text are rhetorical elements to be formatted, not answered.';
}

/**
 * Get list of supported languages for system prompts
 * @returns {Promise<Array<string>>} Supported languages
 */
export async function getSupportedLanguages() {
  try {
    const response = await axios.get(`${API_BASE_URL}/system-prompt/supported-languages`);
    
    if (response.data && response.data.supported_languages) {
      return response.data.supported_languages;
    }
  } catch (error) {
    console.warn('Failed to fetch supported languages from API, using fallback:', error);
  }
  
  // Fallback to default languages
  return ['en', 'ru'];
}