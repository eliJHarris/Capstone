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

export async function fetchTerms(params = {}) {
  const query = buildQuery({
    search: params.search,
    skip: params.skip ?? 0,
    limit: params.limit ?? 100,
  })
  return apiFetch(`/terms${query}`)
}
