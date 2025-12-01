import { ref, onMounted } from 'vue'

export const AUTH_ROLE_EVENT = 'adviseme-auth-role-changed'

const DEFAULT_ROLE = 'advisor'
const roleRef = ref(DEFAULT_ROLE)
let listenerAttached = false
let changeHandler = null

const normalizeRole = (value) =>
  value && value.toLowerCase() === 'advisee' ? 'advisee' : DEFAULT_ROLE

function decodeRoleFromToken(token) {
  if (typeof window === 'undefined' || !token) return null
  try {
    const [, payload] = token.split('.')
    if (!payload) return null
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '=')
    const decoded = JSON.parse(window.atob(padded))
    return decoded?.role || null
  } catch (error) {
    console.warn('Failed to decode auth token', error)
    return null
  }
}

function readRoleFromStorage() {
  if (typeof window === 'undefined') return DEFAULT_ROLE

  const tokenRole = decodeRoleFromToken(window.localStorage.getItem('auth_token'))
  if (tokenRole) return normalizeRole(tokenRole)

  try {
    const rawUser = window.localStorage.getItem('auth_user')
    if (rawUser) {
      const parsed = JSON.parse(rawUser)
      if (parsed?.role) {
        return normalizeRole(parsed.role)
      }
    }
  } catch (err) {
    console.warn('Failed to parse auth_user from localStorage', err)
  }

  return DEFAULT_ROLE
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
