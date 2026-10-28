import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During development the React app (port 5173) forwards /api calls to Django (port 8000).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://127.0.0.1:8000' } },
})
