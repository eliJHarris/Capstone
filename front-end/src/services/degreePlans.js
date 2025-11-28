import { apiFetch } from '@/services/apiClient'

export function saveRequirementSet(body) {
  return apiFetch('/degree-plans/requirements', {
    method: 'POST',
    body,
  })
}

export function listRequirementSets(params = {}) {
  const query = new URLSearchParams(params).toString()
  const suffix = query ? `?${query}` : ''
  return apiFetch(`/degree-plans/requirements${suffix}`)
}

export function upsertAdviseeContext(adviseeId, body, { autoValidate = true } = {}) {
  const query = autoValidate ? '?auto_validate=1' : '?auto_validate=0'
  return apiFetch(`/degree-plans/advisees/${adviseeId}/context${query}`, {
    method: 'POST',
    body,
  })
}

export function fetchAdviseeSummary(adviseeId) {
  return apiFetch(`/degree-plans/advisees/${adviseeId}/summary`)
}

export function listAdviseeValidations(adviseeId) {
  return apiFetch(`/degree-plans/advisees/${adviseeId}/validations`)
}

export function requestPlanValidation(adviseeId, body = {}) {
  return apiFetch(`/degree-plans/advisees/${adviseeId}/validate`, {
    method: 'POST',
    body,
  })
}
