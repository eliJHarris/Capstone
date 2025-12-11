<template>
  <div class="py-6">
    <h2 class="text-h4 mb-4">Welcome back, {{ studentDisplay }}</h2>

    <v-row v-if="isStudent" class="mb-4 dashboard-row" dense align="stretch">
      <v-col cols="12" md="6">
        <v-card elevation="2" class="student-profile-card dashboard-card">
          <v-card-title class="text-h6">Your Academic Summary</v-card-title>
          <v-card-text>
            <div class="text-h5 font-weight-medium mb-2">{{ studentDisplay }}</div>
            <p class="mb-1">Major: {{ studentMajor }}</p>
            <p v-if="studentMinor">Minor: {{ studentMinor }}</p>
            <p v-else class="text-caption text-medium-emphasis">Minor not declared</p>
            <p class="mt-3 mb-0">GPA: {{ studentGpa }}</p>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card elevation="2" class="dashboard-card">
          <v-card-title class="text-h6">Progress Meters</v-card-title>
          <v-card-text>
            <div class="mb-3">
              <div class="d-flex justify-space-between text-caption mb-1">
                <span>Credits</span>
                <span>{{ progress.creditHoursCompleted }}/{{ progress.creditHoursRequired }}</span>
              </div>
              <v-progress-linear :model-value="creditProgressPercent" color="primary" height="10" rounded />
            </div>
            <div>
              <div class="d-flex justify-space-between text-caption mb-1">
                <span>Core Requirements</span>
                <span>{{ progress.coreRequirementsCompleted }}/{{ progress.coreRequirementsTotal }}</span>
              </div>
              <v-progress-linear :model-value="coreProgressPercent" color="deep-orange" height="10" rounded />
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="isStudent" dense class="mb-6 dashboard-row" align="stretch">

      <v-col cols="12" md="6">
        <v-card elevation="2" class="dashboard-card">
          <v-card-title class="text-h6">Notification Preview</v-card-title>
          <v-card-text>
            <div v-if="upcomingMilestones.length">
              <div v-for="milestone in upcomingMilestones" :key="milestone.title" class="milestone-item">
                <div class="d-flex justify-space-between align-center">
                  <span class="font-weight-medium">{{ milestone.title }}</span>
                  <span class="text-caption text-medium-emphasis">{{ milestone.dueDate }}</span>
                </div>
                <div class="text-caption">{{ milestone.description }}</div>
              </div>
            </div>
            <div v-else class="text-caption text-medium-emphasis">No notifications.</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row v-if="isAdvisor" dense class="dashboard-row" align="stretch">
      <v-col cols="12" md="6">
        <v-card elevation="2" class="dashboard-card">
          <v-card-title class="text-h6">Your Advisees</v-card-title>
          <v-card-text>
            <div v-if="advisorAdviseesLoading" class="text-caption text-medium-emphasis">
              Loading advisees...
            </div>
            <div v-else-if="advisorAdviseesError" class="text-caption text-error">
              {{ advisorAdviseesError }}
            </div>
            <v-list v-else-if="advisorAdvisees.length" density="comfortable">
              <v-list-item
                v-for="advisee in advisorAdvisees"
                :key="advisee.adviseeID || advisee.name"
              >
                <v-list-item-title class="font-weight-medium">
                  {{ advisee.name || `Advisee #${advisee.adviseeID}` }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  {{ advisee.major || 'Undeclared' }}
                  <span v-if="advisee.classification"> • {{ advisee.classification }}</span>
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
            <div v-else class="text-caption text-medium-emphasis">
              No advisees assigned yet.
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card elevation="2" class="dashboard-card">
          <v-card-title class="text-h6">Notification Preview</v-card-title>
          <v-card-text>
            <div v-if="notificationsLoading" class="text-caption text-medium-emphasis">
              Loading notifications...
            </div>
            <div v-else-if="notificationsError" class="text-caption text-error">
              {{ notificationsError }}
            </div>
            <div v-else-if="advisorNotifications.length">
              <div
                v-for="notice in advisorNotifications"
                :key="notice.notificationID || notice.title"
                class="milestone-item"
              >
                <div class="d-flex justify-space-between align-center">
                  <span class="font-weight-medium">{{ notice.title || notice.type || 'Notification' }}</span>
                  <span class="text-caption text-medium-emphasis">{{ notice.createdAt || notice.created_at || '' }}</span>
                </div>
                <div class="text-caption">{{ notice.message || notice.body || '—' }}</div>
              </div>
            </div>
            <div v-else class="text-caption text-medium-emphasis">No notifications.</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { NORMALIZED_ROLES } from '@/utils/auth'
import { useStudentProfileStore } from '@/stores/studentProfile'
import { fetchAdvisees } from '@/services/advisees'
import { useNotificationsStore } from '@/stores/notifications'

const { displayName, role, loadUserContext, user } = useCurrentUser()
const studentStore = useStudentProfileStore()
const notificationsStore = useNotificationsStore()

const advisorAdvisees = ref([])
const advisorAdviseesLoading = ref(false)
const advisorAdviseesError = ref('')
const notificationsError = ref('')

const studentProfile = computed(() => studentStore.studentProfile || {})
const studentDisplay = computed(() => displayName.value || studentProfile.value.student_name || 'Student')
const studentMajor = computed(() => studentProfile.value.major || 'Undeclared')
const studentMinor = computed(() => studentProfile.value.minor || '')
const studentGpa = computed(() => {
  const gpa = studentProfile.value.gpa
  if (gpa === undefined || gpa === null || gpa === '') return 'N/A'
  return typeof gpa === 'number' ? gpa.toFixed(2) : gpa
})
const progress = computed(() => studentProfile.value.progress || {})
const upcomingMilestones = computed(() => studentProfile.value.upcomingMilestones || [])
const creditProgressPercent = computed(() => {
  const completed = progress.value.creditHoursCompleted || 0
  const required = progress.value.creditHoursRequired || 1
  return Math.min(100, Math.round((completed / required) * 100))
})
const coreProgressPercent = computed(() => {
  const completed = progress.value.coreRequirementsCompleted || 0
  const total = progress.value.coreRequirementsTotal || 1
  return Math.min(100, Math.round((completed / total) * 100))
})
const isStudent = computed(() => role.value === NORMALIZED_ROLES.STUDENT)
const isAdvisor = computed(() => role.value === NORMALIZED_ROLES.ADVISOR)
const advisorNotifications = computed(() => notificationsStore.notifications.slice(0, 3))
const notificationsLoading = computed(() => notificationsStore.loading)

const loadAdvisorData = async () => {
  advisorAdviseesLoading.value = true
  advisorAdviseesError.value = ''
  notificationsError.value = ''

  try {
    const advisorId = user.value?.userID
    if (!advisorId) {
      advisorAdviseesError.value = 'Missing advisor id'
      advisorAdviseesLoading.value = false
      return
    }

    const data = await fetchAdvisees({ advisorId, limit: 5 })
    advisorAdvisees.value = Array.isArray(data) ? data : []
  } catch (err) {
    advisorAdviseesError.value = err?.message || 'Failed to load advisees'
  } finally {
    advisorAdviseesLoading.value = false
  }

  try {
    const advisorId = user.value?.userID
    if (advisorId) {
      await notificationsStore.loadForUser(advisorId, { force: true })
    }
  } catch (err) {
    notificationsError.value = err?.message || 'Failed to load notifications'
  }
}

onMounted(async () => {
  try {
    await loadUserContext()
  } catch (error) {
    console.error(error)
  }
  if (isAdvisor.value) {
    await loadAdvisorData()
  }
})
</script>

<style scoped>
.student-profile-card {
  background-color: #fff;
}
.dashboard-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  font-family: 'Poppins', sans-serif !important;
}
.dashboard-card :deep(.v-card-title) {
  font-family: 'Poppins', sans-serif !important;
}
.dashboard-row > .v-col {
  display: flex;
}
.dashboard-row > .v-col > .v-card {
  flex: 1;
}
.dashboard-card :deep(.v-card-text) {
  font-family: 'Poppins', sans-serif !important;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.schedule-item,
.milestone-item {
  padding: 12px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.08);
}
.schedule-item:last-child,
.milestone-item:last-child {
  border-bottom: none;
}
</style>
