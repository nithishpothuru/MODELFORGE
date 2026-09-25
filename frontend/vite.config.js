import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      ignored: ['**/MODELFORGE_FRAMES1/**', '**/MODELFORGE_FRAMES2/**'],
    },
  },
})
