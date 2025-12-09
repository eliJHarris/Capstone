<template>
  <div class="py-6 transcripts-page">
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Transcripts</h2>
        <p class="text-body-2 text-medium-emphasis">
          Advisors and admins can browse any student. Students can only view their own record.
        </p>
      </div>
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        variant="text"
        :loading="loadingTranscript"
        :disabled="loadingTranscript"
        @click="refreshTranscript"
      />
    </div>

    <v-alert
      v-if="userContextError"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ userContextError }}
    </v-alert>

    <v-alert
      v-if="error"
      type="error"
      class="mb-4"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

    <v-row dense class="mb-4">
      <v-col cols="12" md="6">
        <v-card rounded="xl">
          <v-card-text>
            <div class="text-subtitle-2 text-medium-emphasis mb-2">Student</div>

            <template v-if="isStudent">
              <div class="text-h5 font-weight-medium mb-1">
                {{ transcript?.studentName || 'Your transcript' }}
              </div>
              <div class="text-body-2 text-medium-emphasis mb-3">
                Advisee #{{ selectedAdviseeId || '—' }} • {{ transcript?.major || 'Major not set' }} • GPA {{ formatGpa(selectedAdviseeGpa) }}
              </div>
              <v-alert
                density="compact"
                color="primary"
                variant="tonal"
                class="mb-0"
              >
                You are limited to your own transcript.
              </v-alert>
            </template>

            <template v-else>
              <v-autocomplete
                v-model="selectedAdviseeId"
                :items="adviseeOptions"
                :loading="adviseeLoading"
                item-title="title"
                item-value="value"
                clearable
                density="comfortable"
                label="Select a student"
                prepend-inner-icon="mdi-account-search"
                hide-details="auto"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props">
                    <v-list-item-title>{{ item?.raw?.title }}</v-list-item-title>
                    <v-list-item-subtitle>{{ item?.raw?.subtitle }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-autocomplete>

              <div class="text-caption text-medium-emphasis mt-2">
                Advisors and admins can view all advisees. Students cannot be selected from this list.
              </div>
            </template>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card rounded="xl">
          <v-card-text>
            <div class="d-flex align-center mb-2">
              <div class="text-subtitle-2 text-medium-emphasis">Snapshot</div>
              <v-spacer />
              <v-chip size="small" color="primary" variant="tonal">
                {{ transcript?.catalogYear || 'CAT2024' }}
              </v-chip>
            </div>

            <div class="text-h6 font-weight-medium mb-1">
              {{ transcript?.studentName || 'Transcript not loaded' }}
            </div>
            <div class="text-body-2 text-medium-emphasis mb-2">
              {{ transcript?.major || '—' }} • {{ transcript?.classification || '—' }}
            </div>

            <div class="d-flex align-center text-caption text-medium-emphasis">
              <v-icon size="18" class="mr-1" icon="mdi-clock-outline" />
              Updated {{ formattedUpdatedAt }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row dense class="mb-4">
      <v-col cols="12" md="4">
        <v-card rounded="xl" class="stat-card">
          <v-card-text>
            <div class="text-subtitle-2 text-medium-emphasis mb-1">Cumulative GPA</div>
            <div class="text-h4 font-weight-medium">{{ formatGpa(transcript?.cumulativeGpa) }}</div>
            <div class="text-caption text-medium-emphasis">
              Weighted by completed credit hours
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="xl" class="stat-card">
          <v-card-text>
            <div class="text-subtitle-2 text-medium-emphasis mb-1">Credits Earned</div>
            <div class="text-h4 font-weight-medium">{{ transcript?.totalCredits ?? '—' }}</div>
            <div class="text-caption text-medium-emphasis">
              Across {{ transcript?.terms?.length || 0 }} terms
            </div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card rounded="xl" class="stat-card">
          <v-card-text>
            <div class="text-subtitle-2 text-medium-emphasis mb-1">Status</div>
            <div class="d-flex align-center">
              <v-chip color="success" size="small" class="mr-2" variant="tonal">
                In Good Standing
              </v-chip>
              <span class="text-body-2 text-medium-emphasis">Based on GPA & completion</span>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card
      v-if="loadingTranscript"
      class="pa-6"
      rounded="xl"
    >
      <div class="d-flex align-center justify-center">
        <v-progress-circular indeterminate color="primary" />
        <span class="ml-3 text-body-2 text-medium-emphasis">Loading transcript…</span>
      </div>
    </v-card>

    <v-card
      v-else-if="transcript && transcript.terms?.length"
      rounded="xl"
    >
      <v-card-title>Term History</v-card-title>
      <v-card-text>
        <v-expansion-panels multiple>
          <v-expansion-panel
            v-for="term in transcript.terms"
            :key="term.term"
          >
            <v-expansion-panel-title>
              <div class="d-flex align-center justify-space-between w-100">
                <div>
                  <div class="text-subtitle-1">{{ term.term }}</div>
                  <div class="text-caption text-medium-emphasis">
                    GPA {{ formatGpa(term.termGpa) }} • Credits {{ term.creditsEarned }}/{{ term.creditsAttempted }}
                  </div>
                </div>
                <v-chip size="small" color="primary" variant="tonal">
                  {{ term.courses?.length || 0 }} courses
                </v-chip>
              </div>
            </v-expansion-panel-title>

            <v-expansion-panel-text>
              <v-table density="comfortable">
                <thead>
                  <tr>
                    <th class="text-left">Course</th>
                    <th class="text-left">Title</th>
                    <th class="text-left">Credits</th>
                    <th class="text-left">Grade</th>
                    <th class="text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="course in term.courses" :key="`${term.term}-${course.courseCode}`">
                    <td>{{ course.courseCode }}</td>
                    <td>{{ course.courseTitle }}</td>
                    <td>{{ course.credits }}</td>
                    <td>{{ course.grade }}</td>
                    <td>
                      <v-chip
                        size="small"
                        :color="statusColor(course)"
                        variant="tonal"
                      >
                        {{ course.status }}
                      </v-chip>
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </v-card-text>
    </v-card>

    <v-card
      v-else-if="transcript && !transcript.terms?.length"
      class="pa-4"
      rounded="xl"
    >
      <div class="d-flex align-center">
        <v-icon color="primary" class="mr-2" icon="mdi-information" />
        <div>
          <div class="text-subtitle-1">No transcript data found</div>
          <div class="text-body-2 text-medium-emphasis">
            This student does not have any enrollments or completed courses yet.
          </div>
        </div>
      </div>
    </v-card>

    <v-alert
      v-else
      type="info"
      variant="tonal"
      class="mt-4"
    >
      Select a student to load transcript details.
    </v-alert>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useUserRole } from '@/composables/useUserRole'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { fetchAdvisees } from '@/services/advisees'
import { fetchMyTranscript, fetchTranscriptByAdvisee } from '@/services/transcripts'
import { NORMALIZED_ROLES } from '@/utils/auth'

const transcript = ref(null)
const loadingTranscript = ref(false)
const adviseeOptions = ref([])
const adviseeLoading = ref(false)
const selectedAdviseeId = ref(null)
const error = ref(null)
const userContextError = ref(null)

const { role } = useUserRole()
const { advisee: currentAdvisee, loadUserContext, error: currentUserError } = useCurrentUser()

const isStudent = computed(() => role.value === NORMALIZED_ROLES.STUDENT)
const canBrowseAll = computed(
  () => role.value === NORMALIZED_ROLES.ADVISOR || role.value === NORMALIZED_ROLES.ADMIN
)

const formattedUpdatedAt = computed(() => {
  if (!transcript.value?.updatedAt) return '—'
  const dt = new Date(transcript.value.updatedAt)
  if (Number.isNaN(dt.getTime())) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(dt)
})

const statusColor = (course) => {
  if (course?.grade === 'F') return 'error'
  if (course?.status === 'In Progress' || course?.grade === 'IP') return 'warning'
  return 'success'
}

const formatGpa = (value) => {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  if (Number.isNaN(num)) return '—'
  return num.toFixed(2)
}

const selectedAdviseeProfile = computed(() => {
  if (isStudent.value) {
    return currentAdvisee.value
  }
  return adviseeOptions.value.find((item) => item.value === selectedAdviseeId.value)?.raw || null
})

const selectedAdviseeGpa = computed(() => {
  const profile = selectedAdviseeProfile.value
  if (profile && profile.gpa !== null && profile.gpa !== undefined) {
    return profile.gpa
  }
  if (transcript.value?.cumulativeGpa !== null && transcript.value?.cumulativeGpa !== undefined) {
    return transcript.value.cumulativeGpa
  }
  return null
})

const loadAdvisees = async () => {
  if (!canBrowseAll.value) return
  adviseeLoading.value = true
  try {
    const records = await fetchAdvisees({ limit: 200 })
    adviseeOptions.value = records.map((item) => ({
      title: item.name || `Advisee #${item.adviseeID}`,
      subtitle: [
        item.major || 'Major not set',
        item.classification || '—',
        item.gpa !== null && item.gpa !== undefined ? `GPA ${formatGpa(item.gpa)}` : null,
      ]
        .filter(Boolean)
        .join(' • '),
      value: item.adviseeID,
      raw: item,
    }))
  } catch (err) {
    error.value = err.message || 'Failed to load advisees'
  } finally {
    adviseeLoading.value = false
  }
}

const loadTranscript = async () => {
  loadingTranscript.value = true
  error.value = null
  try {
    let result = null
    if (isStudent.value) {
      result = await fetchMyTranscript()
      selectedAdviseeId.value = result?.adviseeID || currentAdvisee.value?.adviseeID || null
    } else if (selectedAdviseeId.value) {
      result = await fetchTranscriptByAdvisee(selectedAdviseeId.value)
    }
    transcript.value = result
  } catch (err) {
    error.value = err.message || 'Unable to load transcript'
    transcript.value = null
  } finally {
    loadingTranscript.value = false
  }
}

const refreshTranscript = async () => {
  if (loadingTranscript.value) return
  await loadTranscript()
}

watch(
  () => selectedAdviseeId.value,
  async (next, prev) => {
    if (next === prev || !next || isStudent.value) return
    await loadTranscript()
  }
)

onMounted(async () => {
  try {
    await loadUserContext()
  } catch (err) {
    userContextError.value = currentUserError.value || err?.message || 'Failed to load user context'
  }

  if (isStudent.value) {
    selectedAdviseeId.value = currentAdvisee.value?.adviseeID || null
    await loadTranscript()
  } else {
    await loadAdvisees()
  }
})
</script>

<style scoped>
.transcripts-page .stat-card {
  height: 100%;
}
</style>
