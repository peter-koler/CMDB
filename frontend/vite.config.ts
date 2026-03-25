import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const getPackageName = (id: string) => {
  const modulePath = id.split('node_modules/')[1]
  if (!modulePath) {
    return null
  }

  const segments = modulePath.split('/')
  const packageName = segments[0].startsWith('@') ? `${segments[0]}/${segments[1]}` : segments[0]
  return packageName.replace(/[^a-zA-Z0-9]/g, '-')
}

export default defineConfig({
  plugins: [vue()],
  build: {
    chunkSizeWarningLimit: 1700,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return
          }

          const packageName = getPackageName(id)

          if (
            id.includes('/vue/') ||
            id.includes('/vue-router/') ||
            id.includes('/pinia/') ||
            id.includes('/vue-i18n/')
          ) {
            return 'vue-core'
          }

          if (
            id.includes('/@ant-design/') ||
            id.includes('/ant-design-vue/') ||
            id.includes('/@ant-design/icons-vue/') ||
            id.includes('/@ant-design/icons-svg/') ||
            id.includes('/rc-') ||
            id.includes('/@babel/runtime/') ||
            id.includes('/async-validator/') ||
            id.includes('/dayjs/')
          ) {
            return 'vendor'
          }

          if (id.includes('/echarts/')) {
            return 'echarts-vendor'
          }

          if (id.includes('/@antv/')) {
            return packageName ? `graph-${packageName}` : 'graph-vendor'
          }

          if (id.includes('/d3-')) {
            return 'graph-d3'
          }

          if (
            id.includes('/@wangeditor/') ||
            id.includes('/wangeditor/') ||
            id.includes('/slate/') ||
            id.includes('/snabbdom/')
          ) {
            return packageName ? `editor-${packageName}` : 'editor-vendor'
          }

          if (
            id.includes('/codemirror/') ||
            id.includes('/@codemirror/') ||
            id.includes('/@lezer/')
          ) {
            return packageName ? `codemirror-${packageName}` : 'codemirror-vendor'
          }

          if (id.includes('/socket.io-client/') || id.includes('/engine.io-client/')) {
            return 'socket-vendor'
          }

          if (id.includes('/js-yaml/')) {
            return 'yaml-vendor'
          }

          if (
            packageName === 'axios' ||
            packageName === 'lodash' ||
            packageName === 'lodash-es' ||
            packageName === 'html2canvas' ||
            packageName === 'zrender' ||
            packageName === 'dagre' ||
            packageName === 'graphlib' ||
            packageName === 'gl-matrix' ||
            packageName === 'bubblesets-js' ||
            packageName === 'ml-matrix'
          ) {
            return `vendor-${packageName}`
          }

          return 'vendor'
        }
      }
    }
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
})
