import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendProxy = {
  target: 'http://127.0.0.1:8000',
  changeOrigin: true,
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': backendProxy,
      '/auth': backendProxy,
      '/users': backendProxy,
    },
  },
})
