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
          <v-card-title class="text-h6">Today's Schedule</v-card-title>
          <v-card-text>
            <div v-if="scheduleToday.length">
              <div v-for="item in scheduleToday" :key="item.course" class="schedule-item">
                <div class="font-weight-medium">{{ item.course }} · {{ item.title }}</div>
                <div class="text-caption">{{ item.time }} · {{ item.location }}</div>
              </div>
            </div>
            <div v-else class="text-caption text-medium-emphasis">No classes scheduled today.</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card elevation="2" class="dashboard-card">
          <v-card-title class="text-h6">Upcoming Milestones</v-card-title>
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
            <div v-else class="text-caption text-medium-emphasis">No upcoming milestones.</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row dense>
      <v-col
        v-for="card in cards"
        :key="card.title"
        cols="12"
        sm="6"
        md="4"
      >
        <DashboardCard
          :title="card.title"
          :value="card.value"
          :icon="card.icon"
          :footer="card.footer"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import DashboardCard from '@/components/DashboardCard.vue'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { NORMALIZED_ROLES } from '@/utils/auth'
import { useStudentProfileStore } from '@/stores/studentProfile'

const { displayName, role, loadUserContext } = useCurrentUser()
const studentStore = useStudentProfileStore()

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
const scheduleToday = computed(() => studentProfile.value.todaySchedule || [])
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

const cards = [
  { title: 'Active Schedules', value: 8, icon: 'mdi-calendar-check', footer: 'Across all advisees' },
  { title: 'Pending Approvals', value: 3, icon: 'mdi-alert-circle', footer: 'Awaiting advisor review' },
  { title: 'Completed Scrapes', value: 14, icon: 'mdi-file-document', footer: 'Last updated today' },
]

onMounted(async () => {
  if (role.value !== NORMALIZED_ROLES.STUDENT) return
  try {
    await loadUserContext()
  } catch (error) {
    console.error(error)
  }
})
</script>

<style scoped>
.student-profile-card {
  background-color: #f9f6ef;
}
.dashboard-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.dashboard-row > .v-col {
  display: flex;
}
.dashboard-row > .v-col > .v-card {
  flex: 1;
}
.dashboard-card :deep(.v-card-text) {
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
