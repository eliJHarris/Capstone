const normalizeBaseUrl = (value) => {
  if (!value) return ''
  return value.endsWith('/') ? value.slice(0, -1) : value
}

const resolveDefaultApiBase = () => {
  if (typeof window !== 'undefined' && window?.location?.origin) {
    const current = new URL(window.location.href)
    current.protocol = 'https:'
    return `${current.origin}/api`
  }
  return 'https://localhost/api'
}

const DEFAULT_API_BASE = resolveDefaultApiBase()

export const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE
)

const getStoredToken = () => {
  if (typeof window === 'undefined' || !window?.localStorage) {
    return null
  }
  return window.localStorage.getItem('auth_token')
}

const ABSOLUTE_URL_REGEX = /^https?:\/\//i

const buildUrl = (path) => {
  if (ABSOLUTE_URL_REGEX.test(path)) {
    return path
  }
  if (!path.startsWith('/')) {
    throw new Error(`API path must start with '/'. Received: ${path}`)
  }
  return `${API_BASE_URL}${path}`
}

export async function apiFetch(path, options = {}) {
  const url = buildUrl(path)
  const token = getStoredToken()
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  }

  const config = {
    credentials: 'omit',
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

export async function apiUpload(path, file) {
  const url = buildUrl(path);

  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(url, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const msg = await response.text();
    throw new Error(msg || "Upload failed");
  }

  return response.json();
}

