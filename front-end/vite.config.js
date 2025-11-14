import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'fs'


import vuetify from 'vite-plugin-vuetify'

const certPath = path.resolve(__dirname, '../reverse-proxy/certs/localhost.crt')
const keyPath = path.resolve(__dirname, '../reverse-proxy/certs/localhost.key')

let httpsConfig = true
if (fs.existsSync(certPath) && fs.existsSync(keyPath)) {
  httpsConfig = {
    cert: fs.readFileSync(certPath),
    key: fs.readFileSync(keyPath),
  }
}

export default defineConfig({
  plugins: [
    vue(),
    vuetify({ autoImport: true }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    https: httpsConfig,
  },
})
