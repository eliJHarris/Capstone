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
          closable
          @click:close="clearError"
        >
          {{ errorMsg }}
        </v-alert>

        <v-card rounded="xl" class="notification-card">
          <v-data-table
            :headers="headers"
            :items="tableItems"
            :sort-by="sortBy"
            :loading="loading"
            item-value="notificationID"
            hover
            density="comfortable"
            class="notification-table"
          >
            <template #item.isRead="{ item }">
              <v-chip
                size="small"
                :color="asRow(item).isRead ? 'success' : 'error'"
                variant="tonal"
              >
                {{ asRow(item).isRead ? 'Read' : 'Unread' }}
              </v-chip>
            </template>

            <template #item.description="{ item }">
              <div class="text-body-2">{{ asRow(item).description }}</div>
              <div class="text-caption text-medium-emphasis">
                ID: {{ asRow(item).notificationID }}
              </div>
            </template>

            <template #item.createdAt="{ item }">
              {{ formatDate(asRow(item).createdAt) }}
            </template>

            <template #item.actions="{ item }">
              <div class="text-right">
                <v-btn
                  size="small"
                  variant="text"
                  color="primary"
                  :loading="updatingId === asRow(item).notificationID"
                  @click="toggleRead(asRow(item))"
                >
                  Mark {{ asRow(item).isRead ? 'unread' : 'read' }}
                </v-btn>
              </div>
            </template>

            <template #loading>
              <tr>
                <td :colspan="headers.length">
                  <v-progress-linear indeterminate color="primary" class="ma-4" />
                </td>
              </tr>
            </template>

            <template #no-data>
              <v-alert type="info" variant="tonal" class="ma-4">
                No notifications found.
                <v-btn
                  class="ml-2"
                  size="small"
                  variant="text"
                  @click="loadNotifications(true)"
                >
                  Reload
                </v-btn>
              </v-alert>
            </template>
          </v-data-table>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import AppNavbar from '@/components/AppNavbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { useNotificationsStore } from '@/stores/notifications'

const localError = ref('')
const updatingId = ref(null)

defineProps({
  tabName: String
})

const { role, user, loadUserContext } = useCurrentUser()
const notificationsStore = useNotificationsStore()
const { notifications, unreadCount, loading, error } = storeToRefs(notificationsStore)
const sortBy = ref([{ key: 'createdAt', order: 'desc' }])
const headers = [
  { title: 'Status', key: 'isRead', sortable: false, width: '120px' },
  { title: 'Description', key: 'description', sortable: false, minWidth: '280px' },
  { title: 'Time', key: 'createdAt', sortable: true, width: '220px' },
  { title: 'Action', key: 'actions', sortable: false, align: 'end', width: '160px' },
]

const errorMsg = computed(() => localError.value || error.value || '')
const tableItems = computed(() => notifications.value || [])
const clearError = () => {
  localError.value = ''
  error.value = ''
}

// Vuetify 3 passes slot items slightly differently depending on version;
// this helper normalizes to the raw row object.
const asRow = (slotItem) => slotItem?.raw ?? slotItem ?? {}

const formatDate = (value) => {
  if (!value) return '—'
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

const loadNotifications = async (force = false) => {
  localError.value = ''
  try {
    const userId = user.value?.userID
    if (!userId) {
      throw new Error('Unable to resolve user for notifications.')
    }
    await notificationsStore.loadForUser(userId, { force })
  } catch (err) {
    console.error('Error fetching data:', err)
    localError.value = err.message || 'Failed to load notifications'
  }
}

const toggleRead = async (notification) => {
  if (!notification?.notificationID) return
  updatingId.value = notification.notificationID
  localError.value = ''
  try {
    await notificationsStore.setReadState(
      notification.notificationID,
      !notification.isRead
    )
  } catch (err) {
    console.error('Failed to update notification', err)
    localError.value = err.message || 'Failed to update notification status'
  } finally {
    updatingId.value = null
  }
}

onMounted(async () => {
  try {
    await loadUserContext()
  } catch (err) {
    localError.value = err.message || 'Failed to load user'
    return
  }
  await loadNotifications(true)
})
</script>
