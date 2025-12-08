import { apiFetch } from '@/services/apiClient'

const DEGREE_PLANS_PREFIX = '/degree-plans'

/** Ensure an adviseeId is provided */
const requireAdviseeId = (adviseeId) => {
  if (!adviseeId && adviseeId !== 0) {
    throw new Error('Missing advisee ID')
  }
  return adviseeId
}

/** Convert a JS object into ?query=params */
const buildQuery = (params = {}) => {
  const search = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return
    search.append(key, String(value))
  })
  const query = search.toString()
  return query ? `?${query}` : ''
}

/** Standard prefix for API paths */
const adviseePath = (adviseeId, suffix) =>
  `${DEGREE_PLANS_PREFIX}/advisees/${adviseeId}${suffix}`

/* -------------------------------------------------------
   FETCH SUMMARY (old behavior, used by validator results)
-------------------------------------------------------- */
export async function fetchAdviseeSummary(adviseeId) {
  requireAdviseeId(adviseeId)
  return apiFetch(adviseePath(adviseeId, '/summary'))
}

/* -------------------------------------------------------
   UPSERT CONTEXT (completedCourses, requirementSet link, etc.)
-------------------------------------------------------- */
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

/* -------------------------------------------------------
   MANUAL VALIDATION
-------------------------------------------------------- */
export async function requestPlanValidation(adviseeId, payload = {}, options = {}) {
  requireAdviseeId(adviseeId)
  const query = buildQuery(options.query)
  return apiFetch(`${adviseePath(adviseeId, '/validate')}${query}`, {
    method: 'POST',
    body: payload,
  })
}

/* -------------------------------------------------------
   SAVE REQUIREMENT SET
-------------------------------------------------------- */
export async function saveRequirementSet(payload) {
  if (!payload) {
    throw new Error('Missing requirement set payload')
  }
  return apiFetch(`${DEGREE_PLANS_PREFIX}/requirements`, {
    method: 'POST',
    body: payload,
  })
}

/* -------------------------------------------------------
   IMPORT DEGREE AUDIT PDF
-------------------------------------------------------- */
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

/* -------------------------------------------------------
   NEW: FETCH DEGREE PLAN CONTEXT (matches Transcript page)
   Returns:
   {
     adviseeID,
     name,
     major,
     classification,
     catalogYear,
     requirementSet,
     completedCourses,
     validation
   }
-------------------------------------------------------- */
export async function fetchDegreeContext(adviseeId) {
  requireAdviseeId(adviseeId)
  return apiFetch(`${adviseePath(adviseeId, '/context')}`)
}
