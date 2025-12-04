import { apiFetch } from '@/services/apiClient'

export function fetchTranscriptByAdvisee(adviseeId) {
  if (!adviseeId) {
    return Promise.reject(new Error('adviseeId is required'))
  }
  return apiFetch(`/transcripts/${adviseeId}`)
}

export function fetchMyTranscript() {
  return apiFetch('/transcripts/me')
}
