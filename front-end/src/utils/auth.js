const padBase64 = (value) => {
  const remainder = value.length % 4
  if (!remainder) return value
  return value.padEnd(value.length + (4 - remainder), '=')
}

const safeAtob = (value) => {
  if (typeof atob === 'function') return atob(value)
  if (typeof Buffer !== 'undefined') {
    return Buffer.from(value, 'base64').toString('binary')
  }
  throw new Error('Base64 decoding is not supported in this environment')
}

export const NORMALIZED_ROLES = {
  STUDENT: 'student',
  ADVISOR: 'advisor',
  ADMIN: 'admin',
}

export function normalizeRole(value, fallback = NORMALIZED_ROLES.STUDENT) {
  const normalized = (value || '').toString().trim().toLowerCase()
  if (!normalized) return fallback

  if (normalized === 'admin') return NORMALIZED_ROLES.ADMIN
  if (normalized === 'advisor' || normalized === 'adviser') return NORMALIZED_ROLES.ADVISOR
  if (normalized === 'advisee' || normalized === 'student') return NORMALIZED_ROLES.STUDENT

  return fallback
}

export function decodeTokenPayload(token) {
  if (!token || typeof token !== 'string') return null
  try {
    const [, payload] = token.split('.')
    if (!payload) return null
    const normalized = padBase64(payload.replace(/-/g, '+').replace(/_/g, '/'))
    const decoded = safeAtob(normalized)
    return JSON.parse(decoded)
  } catch (error) {
    console.warn('Failed to decode auth token payload', error)
    return null
  }
}

export function readStoredAuth() {
  if (typeof window === 'undefined') {
    return { token: null, user: null, payload: null }
  }

  const token = window.localStorage.getItem('auth_token')
  const payload = decodeTokenPayload(token)

  let user = null
  try {
    const rawUser = window.localStorage.getItem('auth_user')
    if (rawUser) {
      user = JSON.parse(rawUser)
    }
  } catch (error) {
    console.warn('Failed to parse auth_user from localStorage', error)
  }

  return { token, user, payload }
}

export function resolveStoredIdentity(fallbackRole = NORMALIZED_ROLES.STUDENT) {
  const { user, payload } = readStoredAuth()
  const role = normalizeRole(user?.role || payload?.role, fallbackRole)

  const username =
    user?.uid ||
    user?.username ||
    payload?.uid ||
    payload?.sub ||
    payload?.cn ||
    ''

  const email = user?.mail || user?.email || payload?.mail || payload?.email || ''

  const displayName = user?.cn || user?.name || payload?.cn || username || ''

  return {
    role,
    username,
    email,
    displayName,
    rawUser: user,
    tokenPayload: payload,
  }
}
