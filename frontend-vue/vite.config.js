import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        ws: true
      }
    }
  },
  preview: {
    port: 4173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        ws: true
      }
    }
  },
  css: {
    preprocessorOptions: {
      scss: {
        // 使用现代 Sass API，避免 legacy-js-api 弃用警告
        api: 'modern',
        // 使用 @use 替代已弃用的 @import，并将变量注入全局命名空间
        additionalData: `@use "@/styles/variables.scss" as *;`
      }
    }
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'element-plus-vendor': ['element-plus', '@element-plus/icons-vue'],
          'echarts-vendor': ['echarts', 'echarts-gl'],
          'utils-vendor': ['axios', 'dayjs']
        }
      }
    }
  }
})
