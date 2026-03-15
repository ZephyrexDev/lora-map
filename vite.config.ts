import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  test: {
    exclude: ['e2e/**', 'node_modules/**'],
  },
  server: {
    proxy: {
      '/predict': 'http://localhost:8080/',
      '/status': 'http://localhost:8080/',
      '/result': 'http://localhost:8080/',
      '/towers': 'http://localhost:8080/',
      '/tower-paths': 'http://localhost:8080/',
      '/deadzones': 'http://localhost:8080/',
      '/auth': 'http://localhost:8080/',
      '/matrix': 'http://localhost:8080/',
      '/simulations': 'http://localhost:8080/',
    },
  },
  build: {
    outDir: 'app/ui',
    emptyOutDir: true,
  },
})
