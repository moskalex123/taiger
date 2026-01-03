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
    // For TMA environment, try to get token from TMA service
    if (tmaService.isTMA) {
      try {
        const authData = await tmaService.authenticateWithBackend();
        if (authData?.access_token) {
          config.headers.Authorization = `Bearer ${authData.access_token}`;
        }
      } catch (error) {
        console.warn('TMA authentication failed, using existing token if available');
        const existingToken = localStorage.getItem('auth_token');
        if (existingToken) {
          config.headers.Authorization = `Bearer ${existingToken}`;
        }
      }
    } else {
      // For web environment, use regular token
      const token = localStorage.getItem('auth_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
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
          // Redirect to login or show error
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
      } else {
        // For web environment, redirect to login
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;