import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [vue()],
    server: {
        port: 3000,
        host: '127.0.0.1',
        // 开发环境将 API 与文档请求代理到后端，前端无需关心后端地址
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true
            },
            '/docs': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true
            },
            '/redoc': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true
            }
        }
    },
    build: {
        outDir: 'dist',
        chunkSizeWarningLimit: 1500
    }
})
