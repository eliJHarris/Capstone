import { defineStore } from 'pinia'
import { apiFetch } from '@/services/apiClient'

const createDefaultFilters = () => ({
  adviseeId: '',
  termId: '',
  status: '',
  limit: 50,
})

export const useScheduleStore = defineStore('schedules', {
  state: () => ({
    schedules: [],
    selectedScheduleId: null,
    selectedSchedule: null,
    loadingList: false,
    loadingDetail: false,
    mutationLoading: false,
    sectionSearchLoading: false,
    sectionOptions: [],
    error: null,
    lastSyncedAt: null,
    filters: createDefaultFilters(),
  }),
  getters: {
    hasSelection: (state) => Boolean(state.selectedSchedule),
    statusOptions: () => ['DRAFT', 'APPROVED', 'REJECTED'],
    sourceOptions: () => ['USER', 'ADVISOR', 'SYSTEM'],
    scheduleCount: (state) => state.schedules.length,
  },
  actions: {
    setFilters(updates) {
      this.filters = { ...this.filters, ...updates }
    },
    resetFilters() {
      this.filters = createDefaultFilters()
    },
    clearError() {
      this.error = null
    },
    async fetchSchedules(overrides = {}) {
      this.loadingList = true
      this.error = null

      const params = { ...this.filters, ...overrides }
      const query = new URLSearchParams()

      if (params.adviseeId) query.append('advisee_id', params.adviseeId)
      if (params.termId) query.append('term_id', params.termId)
      if (params.status) query.append('status', params.status)
      if (params.skip !== undefined) query.append('skip', params.skip)
      query.append('limit', params.limit || 50)

      try {
        const qs = query.toString()
        const data = await apiFetch(`/schedules${qs ? `?${qs}` : ''}`)
        this.schedules = data
        this.lastSyncedAt = new Date().toISOString()

        if (this.selectedScheduleId) {
          const stillExists = data.some((item) => item.scheduleID === this.selectedScheduleId)
          if (!stillExists) {
            this.clearSelection()
          }
        }
      } catch (error) {
        this.error = error.message || 'Failed to load schedules'
      } finally {
        this.loadingList = false
      }
    },
    async fetchScheduleById(scheduleId) {
      if (!scheduleId) return
      this.loadingDetail = true
      this.error = null
      try {
        this.selectedSchedule = await apiFetch(`/schedules/${scheduleId}`)
        this.selectedScheduleId = scheduleId
      } catch (error) {
        this.error = error.message || 'Failed to load schedule'
      } finally {
        this.loadingDetail = false
      }
    },
    async selectSchedule(scheduleId) {
      if (!scheduleId) {
        this.clearSelection()
        return
      }
      await this.fetchScheduleById(scheduleId)
      await this.searchSections(scheduleId)
    },
    clearSelection() {
      this.selectedSchedule = null
      this.selectedScheduleId = null
      this.sectionOptions = []
    },
    clearSectionOptions() {
      this.sectionOptions = []
    },
    async createSchedule(payload) {
      this.mutationLoading = true
      this.error = null
      try {
        const created = await apiFetch('/schedules', {
          method: 'POST',
          body: payload,
        })
        this.selectedSchedule = created
        this.selectedScheduleId = created.scheduleID
        await this.fetchSchedules()
        await this.searchSections(created.scheduleID, '')
        return created
      } catch (error) {
        this.error = error.message || 'Failed to create schedule'
        throw error
      } finally {
        this.mutationLoading = false
      }
    },
    async searchSections(scheduleId, search = '') {
      if (!scheduleId) {
        this.clearSectionOptions()
        return
      }
      this.sectionSearchLoading = true
      this.error = null
      try {
        const qs = search ? `?search=${encodeURIComponent(search)}` : ''
        const data = await apiFetch(`/schedules/${scheduleId}/sections${qs}`)
        this.sectionOptions = data.map((item) => ({
          value: item.sectionID,
          title: `${item.courseName} (${item.crn})`,
          subtitle: `${item.professorName || 'TBD'} • ${item.credits} credits`,
          meta: {
            seatsRemaining: item.seatsRemaining,
            enrolled: item.enrolled,
            capacity: item.capacity,
            status: item.status,
          },
        }))
      } catch (error) {
        this.error = error.message || 'Failed to search sections'
        throw error
      } finally {
        this.sectionSearchLoading = false
      }
    },
    async updateSchedule(scheduleId, payload) {
      if (!scheduleId) return
      this.mutationLoading = true
      this.error = null
      try {
        const updated = await apiFetch(`/schedules/${scheduleId}`, {
          method: 'PUT',
          body: payload,
        })
        this.selectedSchedule = updated
        await this.fetchSchedules()
        return updated
      } catch (error) {
        this.error = error.message || 'Failed to update schedule'
        throw error
      } finally {
        this.mutationLoading = false
      }
    },
    async deleteSchedule(scheduleId) {
      if (!scheduleId) return
      this.mutationLoading = true
      this.error = null
      try {
        await apiFetch(`/schedules/${scheduleId}`, { method: 'DELETE' })
        this.schedules = this.schedules.filter((item) => item.scheduleID !== scheduleId)
        if (this.selectedScheduleId === scheduleId) {
          this.clearSelection()
        }
      } catch (error) {
        this.error = error.message || 'Failed to delete schedule'
        throw error
      } finally {
        this.mutationLoading = false
      }
    },
    async addClassToSchedule(scheduleId, sectionId) {
      if (!scheduleId || !sectionId) return
      this.mutationLoading = true
      this.error = null
      try {
        const updated = await apiFetch(`/schedules/${scheduleId}/classes`, {
          method: 'POST',
          body: { sectionID: Number(sectionId) },
        })
        this.selectedSchedule = updated
        await this.fetchSchedules()
        return updated
      } catch (error) {
        this.error = error.message || 'Failed to add class'
        throw error
      } finally {
        this.mutationLoading = false
      }
    },
    async removeClassFromSchedule(scheduleId, classId) {
      if (!scheduleId || !classId) return
      this.mutationLoading = true
      this.error = null
      try {
        const updated = await apiFetch(`/schedules/${scheduleId}/classes/${classId}`, {
          method: 'DELETE',
        })
        this.selectedSchedule = updated
        await this.fetchSchedules()
        return updated
      } catch (error) {
        this.error = error.message || 'Failed to remove class'
        throw error
      } finally {
        this.mutationLoading = false
      }
    },
  },
})
