import { defineStore } from 'pinia'
import {
  fetchAdviseeSummary,
  requestPlanValidation,
  upsertAdviseeContext,
} from '@/services/degreePlans'

export const useDegreePlanStore = defineStore('degreePlan', {
  state: () => ({
    summary: null,
    loading: false,
    validationLoading: false,
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
    async triggerValidation(adviseeId, triggeredBy) {
      if (!adviseeId) return
      this.validationLoading = true
      this.error = null
      try {
        await requestPlanValidation(adviseeId, {
          triggeredBy,
        })
        // allow background task to run before reloading
        setTimeout(() => {
          this.loadSummary(adviseeId)
        }, 1500)
      } catch (error) {
        this.error = error.message || 'Failed to trigger validation'
        throw error
      } finally {
        this.validationLoading = false
      }
    },
  },
})
