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
    allowedHosts: true,   //允許所有 host（包含 ngrok 隨機網址）連線
    proxy: {
      '/api': backendProxy,
      '/auth': backendProxy,
      '/users': backendProxy,
    },
  },
})
