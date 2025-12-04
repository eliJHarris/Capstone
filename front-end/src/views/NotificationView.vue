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
              <th class="text-left">Description</th>
              <th class="text-left">Status</th>
              <th class="text-left">Time</th>
              <th class="text-left">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="notification in notifications" :key="notification.notificationID">
              <td>{{ notification.description }}</td>
              <td>
                <v-chip
                  size="small"
                  :color="notification.isRead ? 'success' : 'secondary'"
                  variant="tonal"
                >
                  {{ notification.isRead ? 'Read' : 'Unread' }}
                </v-chip>
              </td>
              <td>{{ formatTimestamp(notification.createdAt) }}</td>
              <td>
                <v-btn
                  size="small"
                  variant="text"
                  :color="notification.isRead ? 'secondary' : 'primary'"
                  :loading="updatingId === notification.notificationID"
                  :disabled="updatingId === notification.notificationID"
                  @click="toggleReadState(notification, !notification.isRead)"
                >
                  {{ notification.isRead ? 'Mark as unread' : 'Mark as read' }}
                </v-btn>
              </td>
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
import { useNotificationsStore } from '@/stores/notifications'

const errorMsg = ref('')
const updatingId = ref(null)
const notificationsStore = useNotificationsStore()
const notifications = computed(() => notificationsStore.notifications)
const unreadCount = computed(() => notificationsStore.unreadCount)
const loading = computed(() => notificationsStore.loading)
const { role, user, loadUserContext } = useCurrentUser()

defineProps({
  tabName: String
})

const formatTimestamp = (value) => {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString()
}

const loadNotifications = async (force = false) => {
  errorMsg.value = ''
  try {
    let userId = user.value?.userID
    if (!userId) {
      await loadUserContext()
      userId = user.value?.userID
    }
    if (!userId) {
      throw new Error('Unable to resolve user for notifications.')
    }
    await notificationsStore.loadForUser(userId, { force })
  } catch (error) {
    console.error('Error fetching data:', error)
    if (error?.status === 404) {
      errorMsg.value = ''
    } else {
      errorMsg.value = error.message || 'Failed to load notifications'
    }
  }
}

const toggleReadState = async (notification, isRead) => {
  if (!notification?.notificationID) return
  updatingId.value = notification.notificationID
  errorMsg.value = ''
  try {
    await notificationsStore.setReadState(notification.notificationID, isRead)
  } catch (error) {
    console.error('Error updating notification:', error)
    errorMsg.value = error.message || 'Failed to update notification status'
  } finally {
    updatingId.value = null
  }
}

onMounted(async () => {
  try {
    await loadUserContext()
  } catch (error) {
    errorMsg.value = error.message || 'Failed to load user'
    return
  }
  await loadNotifications(true)
})
</script>
