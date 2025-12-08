import { defineStore } from 'pinia'
import {
  fetchAdviseeSummary,
  requestPlanValidation,
  upsertAdviseeContext,
  saveRequirementSet,
  importDegreePlanPdf,
  fetchDegreeContext,       // <-- NEW SERVICE
} from '@/services/degreePlans'

// Normalize requirement set payload so we always have requirementGroups
// regardless of whether the API returns requirementData (Pydantic alias)
// or the context snapshot uses requirementGroups directly.
const normalizeRequirementSet = (rs) => {
  if (!rs) return null
  const groups = rs.requirementGroups || rs.requirementData || []
  return { ...rs, requirementGroups: groups }
}

export const useDegreePlanStore = defineStore('degreePlan', {
  state: () => ({
    summary: null,
    context: null,          // <-- NEW (stores advisee snapshot like Transcript page)
    requirementSet: null,   // <-- NEW
    completedCourses: [],   // <-- NEW
    latestValidation: null, // <-- NEW cached validation

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
    // --------------------------------------------------
    // NEW — Fetch the full degree plan context
    // Mirrors Transcript behavior
    // --------------------------------------------------
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

    // --------------------------------------------------
    // LOAD SUMMARY (still needed for validation results)
    // --------------------------------------------------
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

        // Keep synced with context
        this.latestValidation = summary.latestValidation ?? this.latestValidation
        this.requirementSet = normalizeRequirementSet(summary.requirementSet) ?? this.requirementSet

      } catch (error) {
        this.error = error.message || 'Failed to load degree plan summary'
        throw error
      } finally {
        this.loading = false
      }
    },

    // --------------------------------------------------
    // CONTEXT UPSERT
    // --------------------------------------------------
    async syncContext(adviseeId, payload, options = {}) {
      this.error = null
      try {
        await upsertAdviseeContext(adviseeId, payload, options)

        // Always refresh context afterwards
        await this.fetchContext(adviseeId)
        await this.loadSummary(adviseeId)

      } catch (error) {
        this.error = error.message || 'Failed to sync degree context'
        throw error
      }
    },

    // --------------------------------------------------
    // TRIGGER VALIDATION
    // --------------------------------------------------
    async triggerValidation(adviseeId, triggeredBy) {
      if (!adviseeId) return
      this.validationLoading = true
      this.error = null

      try {
        await requestPlanValidation(adviseeId, { triggeredBy })

        // Refresh after validator finishes
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

    // --------------------------------------------------
    // IMPORT PDF → attaches requirementSet → triggers validation
    // --------------------------------------------------
    async importDegreePlan(adviseeId, pdfUrl) {
      if (!adviseeId) return
      this.importing = true
      this.error = null

      try {
        await importDegreePlanPdf(adviseeId, pdfUrl)

        // Reload everything
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
