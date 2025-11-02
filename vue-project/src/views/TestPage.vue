<template>
  <div class="test-container">
    <h2>✅ Test Page</h2>
    <p v-if="claims">Welcome, <b>{{ claims.sub || claims.cn }}</b>!</p>
    <p v-else>Logged in, but no claims loaded.</p>

    <div class="buttons">
      <button @click="fetchMe">Fetch /me</button>
      <button @click="fetchDb">Fetch /db</button>
      <button @click="logout">Logout</button>
    </div>

    <pre v-if="output">{{ output }}</pre>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useUserStore } from '@/store'
import { useRouter } from 'vue-router'

const store = useUserStore()
const router = useRouter()
const output = ref('')
const claims = computed(() => store.claims)

const CORE_BASE = import.meta.env.VITE_CORE_API_BASE || 'http://localhost:8081'

async function fetchMe() {
  output.value = 'Fetching /me ...'
  try {
    const r = await fetch(`${CORE_BASE}/me`, { headers: store.authHeader })
    output.value = JSON.stringify(await r.json(), null, 2)
  } catch (e) {
    output.value = `Error: ${e}`
  }
}

async function fetchDb() {
  output.value = 'Fetching /db ...'
  try {
    const r = await fetch(`${CORE_BASE}/db`, { headers: store.authHeader })
    output.value = JSON.stringify(await r.json(), null, 2)
  } catch (e) {
    output.value = `Error: ${e}`
  }
}

function logout() {
  store.logout()
  router.push('/login')
}
</script>

<style scoped>
.test-container {
  max-width: 800px;
  margin: 2rem auto;
  padding: 1rem;
  font-family: Arial, sans-serif;
  text-align: center;
}

.buttons {
  margin: 1.5rem 0;
  display: flex;
  justify-content: center;
  gap: 1rem;
}

button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 5px;
  background-color: #6b73ff;
  color: white;
  cursor: pointer;
  transition: background 0.3s;
}

button:hover {
  background-color: #000dff;
}

pre {
  text-align: left;
  background: #111;
  color: #0f0;
  padding: 1rem;
  border-radius: 8px;
  overflow-x: auto;
  white-space: pre-wrap;
}
</style>
