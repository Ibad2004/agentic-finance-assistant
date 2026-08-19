import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/auth': 'http://localhost:8000',
      '/accounts': 'http://localhost:8000',
      '/budgets': 'http://localhost:8000',
      '/categories': 'http://localhost:8000',
      '/tax': 'http://localhost:8000',
      '/reports': 'http://localhost:8000',
      '/assistant': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
