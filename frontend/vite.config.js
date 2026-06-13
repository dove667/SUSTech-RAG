import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const publicHost = process.env.TUNNEL_PUBLIC_HOST
const publicPort = process.env.TUNNEL_PUBLIC_PORT
const publicProtocol = process.env.TUNNEL_PUBLIC_PROTOCOL

// FRP maps frp-off.com:35380 → localhost:3000 (TCP).
    // Tell the HMR client to connect to the public endpoint so hot reload
    // works through the tunnel.
const hmr = publicHost
  ? {
      host: publicHost,
      clientPort: publicPort ? Number(publicPort) : (publicProtocol === 'https' ? 443 : 80),
      protocol: publicProtocol === 'https' ? 'wss' : 'ws',
    }
  : undefined

// 中继模式：设置 VITE_RELAY_URL 环境变量来将 /api 代理到中继服务
// 例如: VITE_RELAY_URL=http://127.0.0.1:8080 npm run dev
const relayTarget = process.env.VITE_RELAY_URL

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: true,
    //hmr,
    proxy: {
      '/api': {
        target: relayTarget || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
