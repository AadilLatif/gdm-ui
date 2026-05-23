import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api/health': { target: 'http://localhost:8001', changeOrigin: true },
      '/api/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/projects': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/system': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/equipment': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/network': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/scenarios': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/models': { target: 'http://localhost:8001', changeOrigin: true },
      '/api/simulations': { target: 'http://localhost:8001', changeOrigin: true },
      '/api/jobs': { target: 'http://localhost:8001', changeOrigin: true },
    },
  },
})
