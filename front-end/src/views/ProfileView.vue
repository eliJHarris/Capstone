<template>
  <div class="py-6">
    <h2 class="text-h4 mb-4">Student Profile</h2>

    <v-alert v-if="!isStudent" type="info" variant="tonal" class="mb-4">
      Profile details are currently available for student accounts only.
    </v-alert>

    <v-alert v-else-if="loadingProfile" type="info" variant="tonal" class="mb-4">
      Loading your profile information...
    </v-alert>

    <template v-else>
      <v-row dense class="profile-row" align="stretch">
        <!-- AT A GLANCE -->
        <v-col cols="12" md="6">
          <v-card elevation="2" class="profile-card at-a-glance-card">
            <v-card-title class="text-h6">At a Glance</v-card-title>
            <v-card-text>
              <v-list density="compact">

                <v-list-item>
                  <v-list-item-title class="text-caption">Name</v-list-item-title>
                  <v-list-item-subtitle>{{ profile.student_name || 'Student' }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <v-list-item-title class="text-caption">Major</v-list-item-title>
                  <v-list-item-subtitle>{{ profile.major || 'Undeclared' }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <v-list-item-title class="text-caption">Minor</v-list-item-title>
                  <v-list-item-subtitle>{{ profile.minor || 'Not declared' }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <v-list-item-title class="text-caption">Catalog</v-list-item-title>
                  <v-list-item-subtitle>{{ profile.catalog_year || 'CAT2024' }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <v-list-item-title class="text-caption">GPA</v-list-item-title>
                  <v-list-item-subtitle>{{ formattedGpa }}</v-list-item-subtitle>
                </v-list-item>

              </v-list>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- ADVISOR -->
        <v-col cols="12" md="6">
          <v-card elevation="2" class="profile-card advisor-card">
            <v-card-title class="text-h6">Advisor</v-card-title>
            <v-card-text>
              <div class="text-subtitle-1 mb-1">{{ advisorContact.name || profile.advisor_name || 'Advisor' }}</div>
              <div class="text-body-2 mb-3">{{ advisorContact.email || 'Contact info not available' }}</div>
              <div class="text-body-2 text-medium-emphasis">
                If you need to update your plan or have questions, reach out directly to your assigned advisor.
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- CURRENT CLASSES -->
      <v-row dense class="profile-row" align="stretch">
        <v-col cols="12">
          <v-card elevation="2" class="profile-card">
            <v-card-title class="text-h6">Current Classes</v-card-title>
            <v-card-text>
              <div v-if="!currentClasses.length" class="text-medium-emphasis">
                No current enrollment information is available.
              </div>

              <v-list v-else density="comfortable">
                <v-list-item v-for="item in currentClasses" :key="item.course + item.title">
                  <v-list-item-title>{{ item.course }} • {{ item.title }}</v-list-item-title>
                  <v-list-item-subtitle>
                    {{ item.time }}
                    <span v-if="item.location"> • {{ item.location }}</span>
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>

            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useStudentProfileStore } from '@/stores/studentProfile'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { NORMALIZED_ROLES } from '@/utils/auth'

const studentStore = useStudentProfileStore()
const { role, loadUserContext } = useCurrentUser()

const profile = computed(() => studentStore.studentProfile || {})
const currentClasses = computed(() => profile.value.todaySchedule || [])
const advisorContact = computed(() => profile.value.advisor_contact || {})
const loadingProfile = computed(() => studentStore.loading)

const formattedGpa = computed(() => {
  if (!profile.value?.gpa && profile.value?.gpa !== 0) return 'N/A'
  return typeof profile.value.gpa === 'number'
    ? profile.value.gpa.toFixed(2)
    : profile.value.gpa
})

const isStudent = computed(() => role.value === NORMALIZED_ROLES.STUDENT)

const maybeLoadProfile = async () => {
  if (!isStudent.value) {
    studentStore.reset()
    return
  }
  try {
    await loadUserContext()
  } catch (error) {
    console.error(error)
  }
}

watch(isStudent, () => {
  void maybeLoadProfile()
}, { immediate: true })
</script>

<style scoped>
/* Ensure equal card height across columns */
.profile-row > .v-col {
  display: flex;
}

.profile-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.profile-card :deep(.v-card-text) {
  flex: 1;
}

.at-a-glance-card :deep(.text-medium-emphasis),
.at-a-glance-card :deep(.text-high-emphasis),
.at-a-glance-card :deep(.v-list-item-title),
.at-a-glance-card :deep(.v-list-item-subtitle),
.at-a-glance-card :deep(*),
.at-a-glance-card {
  color: #000 !important;
  --v-theme-on-surface: #000 !important;
}

</style>
