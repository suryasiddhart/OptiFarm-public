import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    // Unit tests only; Playwright e2e specs (tests/e2e) run separately
    include: ['tests/unit/**/*.test.{ts,tsx}'],
  },
  server: {
    // Mirror the ingress: /api/* → backend (prefix stripped)
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
