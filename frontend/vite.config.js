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

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    allowedHosts: true,
    hmr,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
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
