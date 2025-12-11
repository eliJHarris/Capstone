import { apiFetch } from '@/services/apiClient'

const DEGREE_PLANS_PREFIX = '/degree-plans'

const requireAdviseeId = (adviseeId) => {
  if (!adviseeId && adviseeId !== 0) {
    throw new Error('Missing advisee ID')
  }
  return adviseeId
}

const buildQuery = (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    search.append(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

const adviseePath = (adviseeId, suffix) =>
  `${DEGREE_PLANS_PREFIX}/advisees/${adviseeId}${suffix}`


export async function fetchAdviseeSummary(adviseeId, options = {}) {
  requireAdviseeId(adviseeId)
  const { allowBootstrap } = options
  const query = buildQuery({ allow_bootstrap: allowBootstrap })
  return apiFetch(`${adviseePath(adviseeId, '/summary')}${query}`)
}


export async function upsertAdviseeContext(adviseeId, payload = {}, options = {}) {
  requireAdviseeId(adviseeId)
  const { autoValidate, query: extraQuery = {} } = options

  const query = buildQuery({
    ...extraQuery,
    auto_validate: autoValidate,
  })

  return apiFetch(`${adviseePath(adviseeId, '/context')}${query}`, {
    method: 'POST',
    body: payload,
  })
}


export async function requestPlanValidation(adviseeId, payload = {}, options = {}) {
  requireAdviseeId(adviseeId)
  const query = buildQuery(options.query)
  return apiFetch(`${adviseePath(adviseeId, '/validate')}${query}`, {
    method: 'POST',
    body: payload,
  })
}


export async function saveRequirementSet(payload) {
  if (!payload) {
    throw new Error('Missing requirement set payload')
  }
  return apiFetch(`${DEGREE_PLANS_PREFIX}/requirements`, {
    method: 'POST',
    body: payload,
  })
}

export async function importDegreePlanPdf(adviseeId, pdfUrl) {
  requireAdviseeId(adviseeId)

  if (!pdfUrl) {
    throw new Error('Missing PDF URL')
  }

  return apiFetch(`/import/pdf/${adviseeId}`, {
    method: 'POST',
    body: { pdfUrl },
  })
}


export async function fetchDegreeContext(adviseeId, options = {}) {
  requireAdviseeId(adviseeId)
  const { allowBootstrap } = options
  const query = buildQuery({ allow_bootstrap: allowBootstrap })
  return apiFetch(`${adviseePath(adviseeId, '/context')}${query}`)
}
