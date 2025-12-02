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

export async function fetchAdvisees(params = {}) {
  const query = buildQuery({
    advisor_id: params.advisorId,
    classification: params.classification,
    status: params.status,
    major: params.major,
    degree_plan: params.degreePlan,
    search: params.search,
    skip: params.skip ?? 0,
    limit: params.limit ?? 100,
  })
  return apiFetch(`/advisees${query}`)
}

export async function updateAdvisee(adviseeId, payload) {
  if (!adviseeId) {
    throw new Error('adviseeId is required to update an advisee')
  }
  return apiFetch(`/advisees/${adviseeId}`, {
    method: 'PUT',
    body: payload,
  })
}
