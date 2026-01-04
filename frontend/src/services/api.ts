import axios from 'axios';
import { tmaService } from './tma';

// Create axios instance with TMA authentication
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add authentication
api.interceptors.request.use(
  async (config) => {
    console.log('🔍 API Request:', {
      url: config.url,
      method: config.method,
      origin: window.location.origin,
      isTMA: tmaService.isTMA,
      fullUrl: `${config.baseURL || ''}${config.url || ''}`
    });

    // For TMA environment, try to get token from TMA service
    if (tmaService.isTMA) {
      try {
        const authData = await tmaService.authenticateWithBackend();
        if (authData?.access_token) {
          config.headers.Authorization = `Bearer ${authData.access_token}`;
          console.log('🔍 TMA auth successful, token added');
        }
      } catch (error) {
        console.warn('TMA authentication failed, using existing token if available');
        const existingToken = localStorage.getItem('auth_token');
        if (existingToken) {
          config.headers.Authorization = `Bearer ${existingToken}`;
          console.log('🔍 Using existing token from localStorage');
        }
      }
    } else {
      // For web environment, check both localStorage and cookies
      let token = localStorage.getItem('auth_token');

      // If no token in localStorage, try to get from cookies
      if (!token) {
        // Parse cookies to find access_token
        const cookies = document.cookie.split(';');
        for (const cookie of cookies) {
          const [name, value] = cookie.trim().split('=');
          if (name === 'access_token' && value) {
            token = decodeURIComponent(value);
            console.log('🔍 Web environment, token found in cookies');
            break;
          }
        }
      }

      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
        console.log('🔍 Web environment, token added to Authorization header');
      } else {
        console.log('🔍 Web environment, no token found in localStorage or cookies');
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle authentication errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      if (tmaService.isTMA) {
        try {
          const authData = await tmaService.authenticateWithBackend(true);
          if (authData?.access_token) {
            // Retry the original request with new token
            const originalRequest = error.config;
            originalRequest.headers.Authorization = `Bearer ${authData.access_token}`;
            return api(originalRequest);
          }
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError);
          // For TMA, don't redirect - let the app handle authentication state
          localStorage.removeItem('auth_token');
          // Don't redirect, the app will show login form if needed
        }
      } else {
        // For web environment, clear both localStorage and cookies
        localStorage.removeItem('auth_token');
        // Clear the access_token cookie
        document.cookie = 'access_token=; Max-Age=0; path=/; secure; samesite=lax';
        console.log('🔍 Web environment, cleared auth token from localStorage and cookies');
        // Don't redirect, the app will show login form if needed
      }
    }

    return Promise.reject(error);
  }
);

export default api;