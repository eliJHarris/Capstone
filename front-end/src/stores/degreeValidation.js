import { defineStore } from 'pinia'
import { apiFetch } from '@/services/apiClient'

export const useDegreeValidationStore = defineStore('degreeValidation', {
  state: () => ({
    loading: false,
    error: null,
    report: null,
  }),
  actions: {
    clearError() {
      this.error = null
    },
    resetReport() {
      this.report = null
    },
    async fetchReport({ adviseeId, documentTitle, pdfPath } = {}) {
      if (!adviseeId && adviseeId !== 0) {
        throw new Error('Advisee ID is required')
      }

      this.loading = true
      this.error = null

      try {
        const query = new URLSearchParams()
        if (documentTitle) query.append('document_title', documentTitle)
        if (pdfPath) query.append('pdf_path', pdfPath)

        const qs = query.toString()
        const payload = await apiFetch(
          `/advisees/${adviseeId}/degree-progress${qs ? `?${qs}` : ''}`
        )
        this.report = payload
        return payload
      } catch (error) {
        this.error = error.message || 'Failed to validate degree plan'
        throw error
      } finally {
        this.loading = false
      }
    },
  },
})
