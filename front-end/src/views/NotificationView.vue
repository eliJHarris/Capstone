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

        <v-data-table
          v-else-if="notifications.length > 0"
          :headers="headers"
          :items="notifications"
          item-key="notificationID"
          v-model:sort-by="sortBy"
          :items-per-page="10"
          hover
          density="comfortable"
          class="rounded-lg"
        >
          <template #item.description="{ item }">
            <div class="font-weight-medium">
              {{ item.raw?.description || item.description }}
            </div>
          </template>

          <template #item.isRead="{ item }">
            <v-chip
              size="small"
              :color="(item.raw?.isRead ?? item.isRead) ? 'success' : 'secondary'"
              variant="tonal"
            >
              {{ (item.raw?.isRead ?? item.isRead) ? 'Read' : 'Unread' }}
            </v-chip>
          </template>

          <template #item.createdAt="{ item }">
            <div class="text-caption text-medium-emphasis">
              {{ formatTimestamp(item.raw?.createdAt || item.createdAt) }}
            </div>
          </template>

          <template #item.actions="{ item }">
            <v-btn
              size="small"
              variant="text"
              :color="(item.raw?.isRead ?? item.isRead) ? 'secondary' : 'primary'"
              :loading="updatingId === (item.raw?.notificationID ?? item.notificationID)"
              :disabled="updatingId === (item.raw?.notificationID ?? item.notificationID)"
              @click="
                toggleReadState(
                  item.raw || item,
                  !(item.raw?.isRead ?? item.isRead)
                )
              "
            >
              {{ (item.raw?.isRead ?? item.isRead) ? 'Mark as unread' : 'Mark as read' }}
            </v-btn>
          </template>

          <template #no-data>
            <v-alert type="info" border="start" variant="tonal" class="ma-4">
              No notifications found.
            </v-alert>
          </template>
        </v-data-table>

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
const sortBy = ref([{ key: 'createdAt', order: 'desc' }])
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

const headers = [
  { title: 'Description', key: 'description', sortable: false },
  { title: 'Status', key: 'isRead', sortable: false, width: 140 },
  { title: 'Time', key: 'createdAt' },
  { title: 'Actions', key: 'actions', sortable: false, width: 160 },
]

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
