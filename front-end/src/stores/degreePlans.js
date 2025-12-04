import { defineStore } from 'pinia'
import {
  fetchAdviseeSummary,
  requestPlanValidation,
  upsertAdviseeContext,
  saveRequirementSet,
  importDegreePlanPdf,
} from '@/services/degreePlans'

export const useDegreePlanStore = defineStore('degreePlan', {
  state: () => ({
    summary: null,
    loading: false,
    validationLoading: false,
    importing: false,     // <-- NEW
    error: null,
  }),

  getters: {
    latestValidation(state) {
      return state.summary?.latestValidation || null
    },
    completionPercent() {
      return this.latestValidation?.completionPercent ?? 0
    },
    validationStatus() {
      return this.latestValidation?.status || 'PENDING'
    },
    requirementSet() {
      return this.summary?.requirementSet || null
    },
    context() {
      return this.summary?.context || null
    },
  },

  actions: {
    // LOAD SUMMARY
    async loadSummary(adviseeId) {
      if (!adviseeId) {
        this.error = 'Missing advisee ID'
        return
      }
      this.loading = true
      this.error = null
      try {
        this.summary = await fetchAdviseeSummary(adviseeId)
      } catch (error) {
        this.error = error.message || 'Failed to load degree plan summary'
        throw error
      } finally {
        this.loading = false
      }
    },

    // CONTEXT SYNC
    async syncContext(adviseeId, payload, options = {}) {
      this.error = null
      try {
        await upsertAdviseeContext(adviseeId, payload, options)
        await this.loadSummary(adviseeId)
      } catch (error) {
        this.error = error.message || 'Failed to sync degree context'
        throw error
      }
    },

    // MANUAL VALIDATION
    async triggerValidation(adviseeId, triggeredBy) {
      if (!adviseeId) return
      this.validationLoading = true
      this.error = null
      try {
        await requestPlanValidation(adviseeId, { triggeredBy })

        // allow background validator a moment to run
        setTimeout(() => this.loadSummary(adviseeId), 1500)
      } catch (error) {
        this.error = error.message || 'Failed to trigger validation'
        throw error
      } finally {
        this.validationLoading = false
      }
    },

    // -------------------------
    // NEW: Degree Audit PDF Import
    // -------------------------
    async importDegreePlan(adviseeId, pdfUrl) {
      if (!adviseeId) return
      this.importing = true
      this.error = null

      try {
        await importDegreePlanPdf(adviseeId, pdfUrl)

        // Refresh summary after ingestion + auto-validation
        await this.loadSummary(adviseeId)
        await this.triggerValidation(adviseeId)

      } catch (error) {
        this.error = error.message || 'PDF import failed'
        throw error
      } finally {
        this.importing = false
      }
    },
  }
})
