import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path' // Add this import

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src') // Add alias configuration
    }
  },
  server: {
    host: true, // Allow external connections
    port: 5173, // Standard Vite dev port
    allowedHosts: [
      'tactically-healing-parrotfish.cloudpub.ru',
      'mpc.tailf35c26.ts.net'  
    ],
    proxy: {
      // Requests starting with /api will be forwarded
      '/api': {
        target: 'http://localhost:8000', // Your FastAPI backend address
        changeOrigin: true, // Recommended for virtual hosted sites
        // secure: false, // Uncomment if your backend uses http
        // rewrite: (path) => path.replace(/^\/api/, '') // Use if your backend doesn't expect /api prefix
      },
      // Add new proxy rule for /auth
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // secure: false, // Uncomment if your backend uses http
        // No rewrite needed as the backend expects /auth prefix
      }
    }
  }
})