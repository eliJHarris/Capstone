<template>
  <div>
    <v-btn @click="callApi" :disabled="loading">
      {{ loading ? 'Loading...' : 'Call API' }}
    </v-btn>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="response" class="success">{{ response }}</div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const loading = ref(false)
const response = ref(null)
const error = ref(null)

async function callApi() {
  loading.value = true
  response.value = null
  try {
    response.value = null
    error.value = null

    // adjust URL/path to match your API endpoint
    const res = await fetch('http://localhost:8000/api/schedules/1')
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
.success { color: green; margin-top: 8px; }
</style>