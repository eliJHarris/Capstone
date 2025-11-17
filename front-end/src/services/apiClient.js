const normalizeBaseUrl = (value) => {
  if (!value) return ''
  return value.endsWith('/') ? value.slice(0, -1) : value
}

export const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
)

const buildUrl = (path) => {
  if (!path.startsWith('/')) {
    throw new Error(`API path must start with '/'. Received: ${path}`)
  }
  return `${API_BASE_URL}${path}`
}

export async function apiFetch(path, options = {}) {
  const url = buildUrl(path)
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  }

  const config = {
    credentials: 'include',
    ...options,
    headers,
  }

  if (config.body && typeof config.body !== 'string' && !(config.body instanceof FormData)) {
    config.body = JSON.stringify(config.body)
  }

  const response = await fetch(url, config)
  const contentType = response.headers.get('content-type') || ''
  let payload = null

  if (contentType.includes('application/json')) {
    payload = await response.json()
  } else if (contentType) {
    payload = await response.text()
  }

  if (!response.ok) {
    const detail = typeof payload === 'string' ? payload : payload?.detail
    throw new Error(detail || `API request failed with status ${response.status}`)
  }

  return payload
}
