import { ref, onMounted } from 'vue'
import { resolveStoredIdentity, NORMALIZED_ROLES } from '@/utils/auth'

export const AUTH_ROLE_EVENT = 'adviseme-auth-role-changed'

const DEFAULT_ROLE = NORMALIZED_ROLES.STUDENT
const roleRef = ref(DEFAULT_ROLE)
let listenerAttached = false
let changeHandler = null

function readRoleFromStorage() {
  if (typeof window === 'undefined') return DEFAULT_ROLE

  const identity = resolveStoredIdentity(DEFAULT_ROLE)
  return identity.role || DEFAULT_ROLE
}

function syncRole() {
  roleRef.value = readRoleFromStorage()
}

function ensureListeners() {
  if (listenerAttached || typeof window === 'undefined') return
  changeHandler = (event) => {
    if (
      event.type === 'storage' &&
      event.key !== 'auth_user' &&
      event.key !== 'auth_token'
    ) {
      return
    }
    syncRole()
  }
  window.addEventListener('storage', changeHandler)
  window.addEventListener(AUTH_ROLE_EVENT, changeHandler)
  listenerAttached = true
}

export function useUserRole() {
  if (typeof window !== 'undefined') {
    syncRole()
    ensureListeners()
  }

  onMounted(syncRole)

  return {
    role: roleRef,
    refreshRole: syncRole,
  }
}
