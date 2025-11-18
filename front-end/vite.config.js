import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import vuetify from 'vite-plugin-vuetify'
import fs from 'fs'

const ENABLE_DEV_HTTPS = (process.env.VITE_DEV_HTTPS || '').toLowerCase() === 'true'
const CERT_DIR = process.env.VITE_DEV_CERT_DIR || '/certs'
const KEY_PATH = path.join(CERT_DIR, 'localhost.key')
const CERT_PATH = path.join(CERT_DIR, 'localhost.crt')

let httpsConfig = false
if (ENABLE_DEV_HTTPS) {
  if (fs.existsSync(KEY_PATH) && fs.existsSync(CERT_PATH)) {
    httpsConfig = {
      key: fs.readFileSync(KEY_PATH),
      cert: fs.readFileSync(CERT_PATH),
    }
  } else {
    console.warn(
      `[vite] VITE_DEV_HTTPS is enabled but certs missing in ${CERT_DIR}. Falling back to HTTP.`
    )
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
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    https: httpsConfig,
  },
})
