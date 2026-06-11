import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const backendEnvDir = path.resolve(__dirname, '..')

export default defineConfig(({ mode }) => {
  const backendEnv = loadEnv(mode, backendEnvDir, '')
  const apiAuthToken = backendEnv.API_AUTH_TOKEN

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          configure: (proxy) => {
            if (!apiAuthToken) return
            proxy.on('proxyReq', (proxyReq) => {
              proxyReq.setHeader('Authorization', `Bearer ${apiAuthToken}`)
            })
          },
          rewrite: (requestPath) => requestPath.replace(/^\/api/, ''),
        },
      },
    },
  }
})
