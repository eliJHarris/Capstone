import { apiFetch } from './apiClient'

export async function fetchNotificationsForUser(userId, { skip = 0, limit = 100, isRead } = {}) {
  if (!userId) throw new Error('User ID is required to fetch notifications')

  const params = new URLSearchParams({
    user_id: String(userId),
    skip: String(skip),
    limit: String(limit),
  })

  if (typeof isRead === 'boolean') {
    params.append('is_read', String(isRead))
  }

  return apiFetch(`/notifications?${params.toString()}`)
}

export async function updateNotificationStatus(notificationId, payload) {
  if (!notificationId) throw new Error('Notification ID is required')
  return apiFetch(`/notifications/${notificationId}`, {
    method: 'PUT',
    body: payload,
  })
}
