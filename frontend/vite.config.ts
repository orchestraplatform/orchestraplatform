import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    include: ['src/**/*.{test,spec}.{ts,tsx}', 'tests/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['tests/e2e/**'],
  },
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    port: 3000,
    // VITE_API_URL is set in .env.local (see .env.local.example).
    // No proxy needed — the generated client calls the API directly.
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
