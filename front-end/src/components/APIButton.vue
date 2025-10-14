<template>
  <div>
    <v-btn @click="callApi" :disabled="loading">
      {{ loading ? 'Loading...' : 'Call API' }}
    </v-btn>

    <div v-if="error" class="error">{{ error }}</div>
    <pre v-if="response">{{ response }}</pre>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const loading = ref(false)
const response = ref(null)
const error = ref(null)

async function callApi() {
  loading.value = true
  error.value = null
  response.value = null
  try {
    // adjust URL/path to match your API endpoint
    const res = await fetch('http://localhost:8000')
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
    const data = await res.json()
    response.value = JSON.stringify(data, null, 2)
  } catch (e) {
    error.value = e.message ?? String(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.error { color: red; margin-top: 8px; }
pre { margin-top: 8px; background:#f6f8fa; padding:8px; }
</style>