<template>
  <v-app>
    <AppNavbar />
    <v-main class="d-flex">
      <AppSidebar :role="role" />
      <v-container fluid style="flex:1; padding-top: 24px;">
        <h2 class="text-h4 mb-4">You're in the {{ tabName }} tab</h2>

        <!-- Table rendering notifications -->
        <v-table v-if="notifications.length > 0">
          <thead>
            <tr>
              <th class="text-left">From</th>
              <th class="text-left">Description</th>
              <th class="text-left">Time</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="notification in notifications" :key="notification.notificationID">
              <td>{{ notification.userID }}</td>
              <td>{{ notification.description }}</td>
              <td>{{ notification.createdAt }}</td>
            </tr>
          </tbody>
        </v-table>

        <!-- Optional loading state when there are no notifications -->
        <v-alert v-else type="info">Loading notifications...</v-alert>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { apiFetch } from '@/services/apiClient'
import AppNavbar from '@/components/AppNavbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import DashboardCard from '@/components/DashboardCard.vue'

// Define reactive variables with Composition API
const notifications = ref([]) // Store notifications array
const role = 'advisor' // Static value for role
defineProps({
  tabName: String
})

// Fetch data when component is mounted
onMounted(async () => {
  try {
    const data = await apiFetch('/notifications?skip=0&limit=100')
    notifications.value = data
  } catch (error) {
    console.error("Error fetching data:", error)
  }
})
</script>
