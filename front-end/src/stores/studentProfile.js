import { defineStore } from 'pinia'
import { apiFetch } from '@/services/apiClient'

const CREDIT_REQUIREMENT = 120
const CORE_REQUIREMENT_TOTAL = 16

const formatDateLabel = (value) => {
  if (!value) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

const buildMilestonesFromNotifications = (notifications = []) =>
  notifications.map((item) => ({
    title: item.description || 'Advising update',
    dueDate: formatDateLabel(item.createdAt),
    description: 'Generated from your latest notifications.',
  }))

async function fetchScheduleSnapshot(adviseeId) {
  if (!adviseeId) return []
  try {
    const list = await apiFetch(`/schedules?advisee_id=${adviseeId}&limit=1`)
    if (!Array.isArray(list) || !list.length) return []

    const scheduleId = list[0].scheduleID
    const detail = await apiFetch(`/schedules/${scheduleId}`)
    const classes = Array.isArray(detail?.classes) ? detail.classes : []
    return classes.map((cls) => ({
      course: cls.courseName || `CRN ${cls.crn}`,
      title: cls.courseDescription || `${cls.credits || 0} credit course`,
      time: cls.professorName ? `Instructor: ${cls.professorName}` : 'Meeting time TBD',
      location: cls.crn ? `CRN ${cls.crn}` : '',
      status: cls.sectionStatus || detail.status || 'Registered',
    }))
  } catch (error) {
    console.warn('Failed to load schedule snapshot', error)
    return []
  }
}

async function fetchNotifications(userId, limit = 3) {
  if (!userId) return []
  try {
    const query = new URLSearchParams({ user_id: String(userId), limit: String(limit) })
    const data = await apiFetch(`/notifications?${query.toString()}`)
    return buildMilestonesFromNotifications(data || [])
  } catch (error) {
    console.warn('Failed to load notifications', error)
    return []
  }
}

async function fetchAdvisorContact(advisorId) {
  if (!advisorId) return { email: '', name: '' }
  try {
    const query = new URLSearchParams({ user_id: String(advisorId), limit: '1' })
    const results = await apiFetch(`/users?${query.toString()}`)
    if (Array.isArray(results) && results.length) {
      const advisorUser = results[0]
      return {
        email: advisorUser.email || '',
        name: advisorUser.username || advisorUser.displayName || '',
      }
    }
  } catch (error) {
    console.warn('Failed to load advisor contact info', error)
  }
  return { email: '', name: '' }
}

export const useStudentProfileStore = defineStore('studentProfile', {
  state: () => ({
    profile: null,
    loading: false,
    error: null,
    loadedAdviseeId: null,
  }),
  getters: {
    studentProfile: (state) => state.profile || {},
  },
  actions: {
    async loadDashboard(context = {}, options = {}) {
      const { advisee, user, identity } = context || {}
      const adviseeId = advisee?.adviseeID
      const { force = false } = options

      if (!adviseeId) {
        this.reset()
        return
      }
      if (!force && this.loadedAdviseeId === adviseeId && this.profile) {
        return
      }

      this.loading = true
      this.error = null
      try {
        const [scheduleItems, milestoneItems, advisorContact] = await Promise.all([
          fetchScheduleSnapshot(adviseeId),
          fetchNotifications(user?.userID),
          fetchAdvisorContact(advisee?.advisorID),
        ])

        const creditsCompleted = Number(advisee?.creditsCompleted ?? 0)
        const coreCompleted = Math.min(
          CORE_REQUIREMENT_TOTAL,
          Math.round((creditsCompleted / CREDIT_REQUIREMENT) * CORE_REQUIREMENT_TOTAL)
        )

        this.profile = {
          student_name: identity?.displayName || advisee?.name || user?.username || 'Student',
          major: advisee?.major || 'Undeclared',
          minor: advisee?.degreePlan || '',
          advisee_id: adviseeId,
          catalog_year: advisee?.catalogYear || 'CAT2024',
          program_code: advisee?.degreePlan || '',
          advisor_name: advisee?.advisorName || '',
          advisor_contact: {
            name: advisee?.advisorName || advisorContact.name || '',
            email: advisorContact.email || '',
          },
          gpa: advisee?.gpa ?? null,
          holds_list: [],
          progress: {
            creditHoursCompleted: creditsCompleted,
            creditHoursRequired: CREDIT_REQUIREMENT,
            coreRequirementsCompleted: coreCompleted,
            coreRequirementsTotal: CORE_REQUIREMENT_TOTAL,
          },
          todaySchedule: scheduleItems,
          upcomingMilestones: milestoneItems,
          degree_plan_summary: `Progress: ${creditsCompleted}/${CREDIT_REQUIREMENT} credit hours completed toward ${
            advisee?.degreePlan || 'your degree'
          }.`,
          policies_summary:
            'Advising policies require meeting with your advisor before registration changes. Maintain a 2.0 GPA and resolve holds promptly.',
        }
        this.loadedAdviseeId = adviseeId
      } catch (error) {
        console.error(error)
        this.error = error.message || 'Failed to load student dashboard'
        throw error
      } finally {
        this.loading = false
      }
    },
    updateProfile(updates = {}) {
      this.profile = {
        ...(this.profile || {}),
        ...updates,
      }
    },
    replaceProfile(newProfile = {}) {
      this.profile = {
        ...newProfile,
      }
    },
    reset() {
      this.profile = null
      this.loadedAdviseeId = null
      this.error = null
      this.loading = false
    },
  },
})
