import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  fetchNotificationsForUser,
  updateNotificationStatus,
} from '@/services/notifications'

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref([])
  const loading = ref(false)
  const error = ref('')
  const lastLoadedUserId = ref(null)

  const unreadCount = computed(
    () => notifications.value.filter((item) => !item.isRead).length
  )

  const loadForUser = async (userId, { force = false } = {}) => {
    if (!userId) throw new Error('User ID is required to load notifications')
    if (
      !force &&
      lastLoadedUserId.value === userId &&
      notifications.value.length > 0
    ) {
      return notifications.value
    }

    loading.value = true
    error.value = ''
    try {
      const data = await fetchNotificationsForUser(userId)
      notifications.value = Array.isArray(data) ? data : []
      lastLoadedUserId.value = userId
      return notifications.value
    } catch (err) {
      error.value = err.message || 'Failed to load notifications'
      throw err
    } finally {
      loading.value = false
    }
  }

  const setReadState = async (notificationId, isRead) => {
    if (typeof isRead !== 'boolean') {
      throw new Error('isRead flag is required')
    }
    const updated = await updateNotificationStatus(notificationId, { isRead })
    const idx = notifications.value.findIndex(
      (n) => n.notificationID === notificationId
    )
    if (idx !== -1) {
      notifications.value[idx] = updated
    } else {
      notifications.value.push(updated)
    }
    return updated
  }

  return {
    notifications,
    loading,
    error,
    unreadCount,
    lastLoadedUserId,
    loadForUser,
    setReadState,
  }
})
