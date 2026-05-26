import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
      '/static': 'http://localhost:5000',
      '/image': 'http://localhost:5000',
    },
  },
  build: {
    outDir: resolve(__dirname, '../static'),
    emptyOutDir: false,
    assetsDir: 'assets',
  },
  base: '/static/',
})
