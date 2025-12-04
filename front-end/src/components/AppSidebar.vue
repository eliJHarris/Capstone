<template>
  <v-navigation-drawer
    model-value="true"
    width="260"
    variant="permanent"
    class="pa-2"
    style="background-color:#ccccc6;"
  >
    <div class="pa-2">
      <v-avatar size="48" class="mb-2">
        <img src=/src/assets/mockup/Avatar.png style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />
      </v-avatar>
      <div class="subtitle-1 font-weight-medium">{{ userLabel }}</div>
      <div class="caption">{{ roleLabel }}</div>
    </div>

    <v-divider class="my-2" />

    <v-list nav>
      <v-list-item
        v-for="item in navItems"
        :key="item.title"
        :to="item.to"
        router
      >
        <v-list-item-title>{{ item.title }}</v-list-item-title>
        <template #append v-if="item.badge && item.badge > 0">
          <v-badge
            :content="item.badge"
            color="red"
            inline
            size="small"
          />
        </template>
      </v-list-item>
    </v-list>
  </v-navigation-drawer>
</template>

<script>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { normalizeRole, NORMALIZED_ROLES } from '@/utils/auth'
import { AUTH_ROLE_EVENT } from '@/composables/useUserRole'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { useNotificationsStore } from '@/stores/notifications'

export default {
  name: 'AppSidebar',
  props: {
    role: { type: String, default: NORMALIZED_ROLES.STUDENT }
  },
  setup() {
    const { displayName, username, refreshIdentity, user, loadUserContext } = useCurrentUser()
    const notificationsStore = useNotificationsStore()
    const userLabel = computed(() => displayName.value || username.value || 'User')
    const unreadCount = computed(() => notificationsStore.unreadCount)

    const loadNotificationsForSidebar = async () => {
      try {
        let userId = user.value?.userID
        if (!userId) {
          await loadUserContext()
          userId = user.value?.userID
        }
        if (userId) {
          await notificationsStore.loadForUser(userId)
        }
      } catch (error) {
        console.error('Failed to load notifications for sidebar', error)
      }
    }

    const handleIdentityChange = (event) => {
      if (
        event?.type === 'storage' &&
        event?.key &&
        event.key !== 'auth_user' &&
        event.key !== 'auth_token'
      ) {
        return
      }
      refreshIdentity()
    }

    onMounted(() => {
      refreshIdentity()
      if (typeof window !== 'undefined') {
        window.addEventListener('storage', handleIdentityChange)
        window.addEventListener(AUTH_ROLE_EVENT, handleIdentityChange)
      }
      loadNotificationsForSidebar()
    })

    onBeforeUnmount(() => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('storage', handleIdentityChange)
        window.removeEventListener(AUTH_ROLE_EVENT, handleIdentityChange)
      }
    })

    watch(user, (next, prev) => {
      if (next?.userID && next.userID !== prev?.userID) {
        loadNotificationsForSidebar()
      }
    })

    return {
      userLabel,
      unreadCount,
    }
  },
  computed: {
    normalizedRole() {
      return normalizeRole(this.role)
    },
    roleLabel() {
      if (this.normalizedRole === NORMALIZED_ROLES.ADMIN) return 'Admin'
      if (this.normalizedRole === NORMALIZED_ROLES.ADVISOR) return 'Advisor'
      return 'Student'
    },
    navItems() {
      if (this.normalizedRole === NORMALIZED_ROLES.STUDENT) {
        return [
          { title: 'Dashboard', to: '/dashboard' },
          { title: 'Notifications', to: '/notifications', badge: this.unreadCount },
          { title: 'Transcripts', to: '/transcripts' },
          { title: 'Degree Plan', to: '/degree-plan' },
          { title: 'Schedules / Appointments', to: '/schedules' },
          { title: 'PDF Scraper', to: '/pdf-scraper' },
        ]
      }
      return [
        { title: 'Dashboard', to: '/dashboard' },
        { title: 'Notifications', to: '/notifications', badge: this.unreadCount },
        { title: 'Student List', to: '/student-list' },
        { title: 'Security', to: '/security' },
        { title: 'Transcripts', to: '/transcripts' },
        { title: 'Degree Plan', to: '/degree-plan' },
        { title: 'Schedules / Appointments', to: '/schedules' },
        { title: 'PDF Scraper', to: '/pdf-scraper' },
      ]
    },
  }
}
</script>
