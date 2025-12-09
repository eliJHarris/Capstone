import { defineStore } from 'pinia'
import {
  fetchAdviseeSummary,
  requestPlanValidation,
  upsertAdviseeContext,
  saveRequirementSet,
  importDegreePlanPdf,
  fetchDegreeContext,       
} from '@/services/degreePlans'

// normalize requirement set payload so we always have requirementGroups just in case api fails

const normalizeRequirementSet = (rs) => {
  if (!rs) return null
  const groups = rs.requirementGroups || rs.requirementData || []
  return { ...rs, requirementGroups: groups }
}

export const useDegreePlanStore = defineStore('degreePlan', {
  state: () => ({
    summary: null,
    context: null,          
    requirementSet: null,   
    completedCourses: [],   
    latestValidation: null, 

    loading: false,
    validationLoading: false,
    importing: false,
    error: null,
  }),

  getters: {
    completionPercent(state) {
      return state.latestValidation?.completionPercent ?? 0
    },
    validationStatus(state) {
      return state.latestValidation?.status || 'PENDING'
    },
    generalEducation(state) {
      return state.latestValidation?.generalEducation || []
    },
    generalEducationCompletionPercent(state) {
      return state.latestValidation?.generalEducationCompletionPercent ?? 0
    },
    concentrations(state) {
      return state.latestValidation?.concentrations || []
    },
    concentrationCompletionPercent(state) {
      return state.latestValidation?.concentrationCompletionPercent ?? 0
    }
  },

  actions: {
    async fetchContext(adviseeId, options = {}) {
      if (!adviseeId) {
        this.error = "Missing advisee ID"
        throw new Error("Missing advisee ID")
      }
      const { allowBootstrap } = options

      this.loading = true
      this.error = null

      try {
        const ctx = await fetchDegreeContext(adviseeId, { allowBootstrap })

        this.context = ctx
        this.requirementSet = normalizeRequirementSet(ctx.requirementSet)
        this.completedCourses = ctx.completedCourses || []
        this.latestValidation = ctx.validation || null

      } catch (err) {
        this.error = err.message || "Failed to load degree context"
        throw err
      } finally {
        this.loading = false
      }
    },


    async loadSummary(adviseeId, options = {}) {
      if (!adviseeId) {
        this.error = 'Missing advisee ID'
        return
      }
      const { allowBootstrap } = options
      this.loading = true
      this.error = null

      try {
        const summary = await fetchAdviseeSummary(adviseeId, { allowBootstrap })
        this.summary = summary

  
        this.latestValidation = summary.latestValidation ?? this.latestValidation
        this.requirementSet = normalizeRequirementSet(summary.requirementSet) ?? this.requirementSet

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

        await this.fetchContext(adviseeId)
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
        await requestPlanValidation(adviseeId, { triggeredBy })

        setTimeout(() => {
          this.loadSummary(adviseeId)
          this.fetchContext(adviseeId)
        }, 1500)

      } catch (error) {
        this.error = error.message || 'Failed to trigger validation'
        throw error
      } finally {
        this.validationLoading = false
      }
    },

    async runLlmValidation(adviseeId) {
      if (!adviseeId) {
        this.error = 'Missing advisee ID'
        throw new Error('Missing advisee ID')
      }
      this.error = null

      try {
        await requestPlanValidation(adviseeId)
        setTimeout(() => {
          this.loadSummary(adviseeId)
          this.fetchContext(adviseeId)
        }, 1500)

      } catch (error) {
        this.error = error.message || 'LLM validation failed'
        throw error
      }
    },


    async importDegreePlan(adviseeId, pdfUrl) {
      if (!adviseeId) return
      this.importing = true
      this.error = null

      try {
        await importDegreePlanPdf(adviseeId, pdfUrl)

        await this.fetchContext(adviseeId)
        await this.loadSummary(adviseeId)

      } catch (error) {
        this.error = error.message || 'PDF import failed'
        throw error
      } finally {
        this.importing = false
      }
    },
  }
})
