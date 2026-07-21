import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import { fileURLToPath, URL } from 'node:url'
import path from 'node:path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const isElectron = mode === 'electron'
  const isTauri = mode === 'tauri'
  const isMobile = mode === 'mobile' || mode === 'capacitor'
  const isPwa = mode === 'pwa'
  const isProd = env.NODE_ENV === 'production'

  const plugins = [
    vue({
      template: {
        compilerOptions: {
          whitespace: 'condense'
        }
      }
    })
  ]

  if (isPwa) {
    plugins.push(VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico'],
      manifest: {
        name: '宝妈指数',
        short_name: '宝妈指数',
        description: '跨平台金融市场情绪分析系统',
        theme_color: '#007AFF',
        background_color: '#F2F2F7',
        display: 'standalone',
        orientation: 'portrait',
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'any maskable' }
        ]
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg}'],
        runtimeCaching: [
          {
            urlPattern: /\/api\/.*/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              expiration: { maxEntries: 50, maxAgeSeconds: 300 },
              networkTimeoutSeconds: 10
            }
          }
        ]
      }
    }))
  }

  return {
    plugins,

    define: {
      __PLATFORM__: JSON.stringify(
        isElectron ? 'electron' :
        isTauri ? 'tauri' :
        isMobile ? 'mobile' :
        'web'
      ),
      __VERSION__: JSON.stringify('2.0.0')
    },

    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        '@platform': fileURLToPath(new URL('./src/platform', import.meta.url)),
        '@core': fileURLToPath(new URL('./src/core', import.meta.url))
      }
    },

    base: isElectron || isMobile ? './' : '/',

    server: {
      port: isElectron ? 5174 : 5173,
      strictPort: isElectron,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: env.VITE_API_TARGET || 'http://localhost:8000',
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
          target: env.VITE_API_TARGET || 'http://localhost:8000',
          changeOrigin: true,
          ws: true
        }
      }
    },

    css: {
      preprocessorOptions: {
        scss: {
          api: 'modern-compiler',
          additionalData: `@use "@/styles/variables.scss" as *; @use "@/styles/mixins.scss" as *;`
        }
      }
    },

    build: {
      target: 'es2020',
      outDir: isMobile ? 'dist-mobile' : 'dist',
      assetsDir: 'assets',
      cssMinify: true,
      sourcemap: !isProd,
      minify: 'esbuild',
      reportCompressedSize: false,
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        input: { main: path.resolve(__dirname, 'index.html') },
        output: {
          manualChunks(id) {
            if (id.includes('node_modules')) {
              if (id.includes('echarts')) return 'vendor-echarts'
              if (id.includes('vue') || id.includes('pinia') || id.includes('vue-router')) return 'vendor-vue'
              return 'vendor-deps'
            }
          }
        }
      }
    },

    optimizeDeps: {
      include: ['vue', 'vue-router', 'pinia', 'axios', 'dayjs'],
      exclude: isTauri ? ['@tauri-apps/api'] : []
    },

    esbuild: {
      drop: isProd ? ['console', 'debugger'] : [],
      legalComments: 'none'
    }
  }
})
