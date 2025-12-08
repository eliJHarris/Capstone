<template>
  <v-app>
    <AppNavbar />
    <v-main class="d-flex">
      <AppSidebar :role="role" />
      <v-container fluid style="flex:1; padding-top: 24px;">
        <div class="d-flex align-center justify-space-between mb-4 flex-wrap ga-4">
          <div class="d-flex align-center ga-4">
            <h2 class="text-h4 mb-0">You're in the {{ tabName }} tab</h2>
            <v-chip
              size="small"
              color="primary"
              variant="tonal"
            >
              {{ unreadCount }} unread
            </v-chip>
          </div>
          <v-btn
            variant="text"
            color="primary"
            prepend-icon="mdi-refresh"
            @click="loadNotifications(true)"
            :loading="loading"
          >
            Refresh
          </v-btn>
        </div>

        <v-alert
          v-if="errorMsg"
          type="error"
          class="mb-4"
          variant="tonal"
        >
          {{ errorMsg }}
        </v-alert>

        <v-alert
          v-else-if="loading"
          type="info"
          variant="tonal"
          class="mb-4"
        >
          Loading notifications...
        </v-alert>

        <v-table v-else-if="notifications.length > 0">
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

        <v-alert v-else type="info">No notifications found.</v-alert>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import AppNavbar from '@/components/AppNavbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { apiFetch } from '@/services/apiClient'

const notifications = ref([])
const loading = ref(false)
const errorMsg = ref('')
const { role, user, loadUserContext } = useCurrentUser()

defineProps({
  tabName: String
})

const unreadCount = computed(() =>
  notifications.value.filter((n) => n && n.read === false).length || 0
)

const loadNotifications = async () => {
  loading.value = true
  errorMsg.value = ''
  try {
    const userId = user.value?.userID
    if (!userId) {
      throw new Error('Unable to resolve user for notifications.')
    }
    const data = await apiFetch(`/notifications/?user_id=${encodeURIComponent(userId)}&skip=0&limit=100`)
    notifications.value = data
  } catch (error) {
    console.error('Error fetching data:', error)
    if (error?.status === 404) {
      notifications.value = []
      errorMsg.value = ''
    } else {
      errorMsg.value = error.message || 'Failed to load notifications'
    }
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    await loadUserContext()
  } catch (error) {
    errorMsg.value = error.message || 'Failed to load user'
    return
  }
  await loadNotifications()
})
</script>
