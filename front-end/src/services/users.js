import { apiFetch } from '@/services/apiClient'

const buildQuery = (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    search.append(key, String(value))
  })
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export async function fetchUsers(params = {}) {
  const query = buildQuery({
    user_id: params.userId,
    username: params.username,
    email: params.email,
    role: params.role,
    isActive: params.isActive,
    skip: params.skip ?? 0,
    limit: params.limit ?? 50,
  })

  return apiFetch(`/users${query}`)
}

export async function fetchUserByUsername(username) {
  if (!username) {
    throw new Error('Username is required to fetch a user')
  }
  const results = await fetchUsers({ username, limit: 1 })
  return Array.isArray(results) && results.length ? results[0] : null
}
