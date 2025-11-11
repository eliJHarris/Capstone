import { defineStore } from 'pinia'
import { apiFetch } from '@/services/apiClient'

const defaultForm = () => ({
  startUrl: '',
  outputPath: '',
  maxPages: 200,
  delay: 1,
  timeout: 20,
  verbose: false,
  requireKeywords: '',
})

const normalizeKeywords = (value) => {
  if (!value) return []
  if (Array.isArray(value)) {
    return value.map((item) => item.trim()).filter(Boolean)
  }
  return value
    .split(',')
    .map((word) => word.trim())
    .filter(Boolean)
}

export const usePdfScraperStore = defineStore('pdfScraper', {
  state: () => ({
    form: defaultForm(),
    loading: false,
    error: null,
    lastResult: null,
  }),
  actions: {
    setForm(updates) {
      this.form = { ...this.form, ...updates }
    },
    resetForm() {
      this.form = defaultForm()
    },
    clearError() {
      this.error = null
    },
    async runScraper(overrides = {}) {
      this.loading = true
      this.error = null
      try {
        const payload = { ...this.form, ...overrides }
        if (!payload.startUrl) {
          throw new Error('Start URL is required')
        }

        const body = {
          start_url: payload.startUrl,
          output_path: payload.outputPath || undefined,
          max_pages: Number(payload.maxPages) || 1,
          delay: Number(payload.delay) || 0,
          timeout: Number(payload.timeout) || 1,
          verbose: Boolean(payload.verbose),
          require_keywords: normalizeKeywords(payload.requireKeywords),
        }

        const result = await apiFetch('/pdf-scraper', {
          method: 'POST',
          body,
        })
        this.lastResult = result
        return result
      } catch (error) {
        this.error = error.message || 'Failed to run PDF scraper'
        throw error
      } finally {
        this.loading = false
      }
    },
  },
})
