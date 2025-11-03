<template>
  <v-app>
    <v-main>
      <router-view />
    </v-main>
    <ChatBubble v-if="showChat" />
  </v-app>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import ChatBubble from '@/components/ChatBubble.vue'


const route = useRoute()
const showChat = computed(() => route.path !== '/' && route.path !== '/login')
</script>

<script>
export default { name: 'App' }
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

html,
body,
#app {
  margin: 0;
  padding: 0;
  font-family: 'Poppins', sans-serif;
  background-color: #e6e5e1;
  color: #1f1f1f;
}

.v-application {
  background-color: #e6e5e1 !important;
  font-family: 'Poppins', sans-serif !important;
}

h1,
h2,
h3,
h4,
h5,
h6,
p,
button {
  font-family: 'Poppins', sans-serif !important;
}


.v-overlay-container {
  z-index: 3000 !important;
}
</style>
