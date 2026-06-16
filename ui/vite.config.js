import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Built into ui/dist, which the Azure Functions app serves as static files.
// During `npm run dev`, API calls are proxied to the local Functions host (func host start).
export default defineConfig({
  plugins: [vue()],
  base: './',
  build: { outDir: 'dist', emptyOutDir: true },
  server: {
    proxy: Object.fromEntries(
      ['/calculate', '/models', '/car', '/photo'].map((p) => [
        p,
        { target: 'http://localhost:7071', changeOrigin: true },
      ])
    ),
  },
})
