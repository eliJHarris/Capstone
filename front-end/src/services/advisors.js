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

export async function fetchAdvisors(params = {}) {
  const query = buildQuery({
    advisorID: params.advisorId,
    name: params.name,
    office: params.office,
    skip: params.skip ?? 0,
    limit: params.limit ?? 200,
  })

  return apiFetch(`/advisors/${query}`)
}
