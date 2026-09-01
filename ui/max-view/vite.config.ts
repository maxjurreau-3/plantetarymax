import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// VITE_API_BASE will be injected at build time via GitHub Actions secrets
export default defineConfig({
  plugins: [react()],
  define: {
    // no-op; use import.meta.env.VITE_API_BASE at runtime/build-time
  }
})
