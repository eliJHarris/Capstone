import { createApp } from 'vue'
import App from './App.vue'
import router from "./router/index.js";
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'

const vuetify = createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'customLight',
    themes: {
      customLight: {
        dark: false,
        colors: {
          background: '#e6e5e1',
          surface: '#ffffff',
          primary: '#4A4A48',
          secondary: '#6C6B67',
          text: '#1f1f1f'
        },
      },
    },
  },
})

createApp(App).use(router).use(vuetify).mount('#app')
