<template>
  <div class="py-6">
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Degree Plan Validation</h2>
        <p class="text-body-2 text-medium-emphasis">
          Compare an advisee's completed and planned coursework against the parsed PDF degree plan.
        </p>
      </div>
      <v-spacer />
      <v-btn
        variant="text"
        :disabled="store.loading"
        @click="prefillExample"
      >
        Use sample values
      </v-btn>
    </div>

    <v-alert
      v-if="store.error"
      type="error"
      class="mb-4"
      closable
      @click:close="store.clearError()"
    >
      {{ store.error }}
    </v-alert>

    <v-row dense>
      <v-col cols="12" md="4">
        <v-card rounded="xl" variant="flat" class="mb-4">
          <v-card-title>Validation input</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="handleSubmit">
              <v-text-field
                v-model="form.adviseeId"
                label="Advisee ID"
                type="number"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                :disabled="store.loading"
                required
              />
              <v-text-field
                v-model="form.documentTitle"
                label="Document title filter"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                :disabled="store.loading"
                hint="Optional substring from the PDF title"
                persistent-hint
              />
              <v-text-field
                v-model="form.pdfPath"
                label="Specific PDF output path"
                density="comfortable"
                variant="outlined"
                class="mb-5"
                :disabled="store.loading"
                hint="Optional relative path inside pdf_results/"
                persistent-hint
              />
              <v-btn
                type="submit"
                color="primary"
                block
                class="mb-2"
                :loading="store.loading"
              >
                Validate plan
              </v-btn>
              <v-btn
                type="button"
                variant="tonal"
                block
                :disabled="store.loading"
                @click="handleReset"
              >
                Reset
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>

        <v-card
          v-if="advisee"
          rounded="xl"
          variant="flat"
        >
          <v-card-title>Advisee snapshot</v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item>
                <v-list-item-title>Name</v-list-item-title>
                <v-list-item-subtitle>{{ advisee.studentName || 'n/a' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Major / Plan</v-list-item-title>
                <v-list-item-subtitle>
                  {{ advisee.major || 'n/a' }} • {{ advisee.degreePlan || 'n/a' }}
                </v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Credits completed</v-list-item-title>
                <v-list-item-subtitle>{{ advisee.creditsCompleted ?? 'n/a' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Classification</v-list-item-title>
                <v-list-item-subtitle>{{ advisee.classification || 'n/a' }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>GPA</v-list-item-title>
                <v-list-item-subtitle>{{ advisee.gpa ?? 'n/a' }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card rounded="xl" variant="flat" class="mb-4">
          <v-card-title class="d-flex align-center">
            <span>Progress summary</span>
            <v-spacer />
            <v-chip
              v-if="summary"
              :color="statusColor(summary.overallStatus)"
              variant="tonal"
            >
              {{ summary.overallStatus }}
            </v-chip>
          </v-card-title>
          <v-card-text v-if="store.loading">
            <v-skeleton-loader type="heading, image" />
          </v-card-text>
          <v-card-text v-else-if="!report">
            Provide an advisee ID to load the latest PDF-derived requirements.
          </v-card-text>
          <v-card-text v-else>
            <div class="d-flex flex-wrap mb-4" style="gap: 16px;">
              <div
                v-for="tile in summaryTiles"
                :key="tile.title"
                class="summary-tile"
              >
                <div class="text-caption text-medium-emphasis">{{ tile.title }}</div>
                <div class="text-h5">{{ tile.value }}</div>
              </div>
            </div>

            <v-alert
              v-if="documentInfo"
              type="info"
              variant="tonal"
              class="mb-4"
            >
              Parsed from <strong>{{ documentInfo.title }}</strong>
              ({{ documentInfo.sourcePath }})
            </v-alert>

            <v-expansion-panels multiple>
              <v-expansion-panel
                v-for="requirement in requirements"
                :key="requirement.key"
              >
                <v-expansion-panel-title>
                  <div class="d-flex align-center flex-wrap w-100">
                    <div class="mr-3">
                      <div class="text-subtitle-1 font-weight-medium">
                        {{ requirement.displayName }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        {{ formatHours(requirement.completedHours) }} / {{ formatHours(requirement.requiredHours) }} hrs
                      </div>
                    </div>
                    <v-chip :color="statusColor(requirement.status)" variant="flat">
                      {{ requirement.status }}
                    </v-chip>
                    <v-spacer />
                    <v-progress-linear
                      :model-value="progressPercent(requirement)"
                      height="6"
                      color="primary"
                      class="flex-grow-1 ml-4"
                    />
                  </div>
                </v-expansion-panel-title>
                <v-expansion-panel-text>
                  <v-row dense>
                    <v-col cols="12" md="6">
                      <v-list density="compact">
                        <v-list-item>
                          <v-list-item-title>Required hours</v-list-item-title>
                          <v-list-item-subtitle>{{ formatHours(requirement.requiredHours) }}</v-list-item-subtitle>
                        </v-list-item>
                        <v-list-item>
                          <v-list-item-title>Completed hours</v-list-item-title>
                          <v-list-item-subtitle>{{ formatHours(requirement.completedHours) }}</v-list-item-subtitle>
                        </v-list-item>
                        <v-list-item>
                          <v-list-item-title>In progress</v-list-item-title>
                          <v-list-item-subtitle>{{ formatHours(requirement.inProgressHours) }}</v-list-item-subtitle>
                        </v-list-item>
                        <v-list-item>
                          <v-list-item-title>Remaining</v-list-item-title>
                          <v-list-item-subtitle>{{ formatHours(requirement.remainingHours) }}</v-list-item-subtitle>
                        </v-list-item>
                      </v-list>
                    </v-col>
                    <v-col cols="12" md="6">
                      <div class="text-subtitle-2 mb-2">Matched courses</div>
                      <div
                        v-if="!requirement.matchedCourses.length"
                        class="text-caption text-medium-emphasis"
                      >
                        No coursework mapped yet.
                      </div>
                      <v-chip
                        v-for="course in requirement.matchedCourses"
                        :key="`${requirement.key}-${course.courseID ?? course.sectionID ?? course.courseName}-${course.source}`"
                        class="mb-2 mr-2"
                        :color="statusColor(course.source === 'COMPLETED' ? 'COMPLETED' : 'IN_PROGRESS')"
                        variant="tonal"
                      >
                        {{ course.courseName }} • {{ formatHours(course.credits) }} hrs
                      </v-chip>
                    </v-col>
                  </v-row>
                  <div v-if="requirement.notes" class="text-caption text-medium-emphasis mt-2">
                    Source: {{ requirement.notes }}
                  </div>
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
        </v-card>

        <v-card
          v-if="unmatchedCourses.length"
          rounded="xl"
          variant="flat"
        >
          <v-card-title>Unmatched coursework</v-card-title>
          <v-card-text>
            <v-table density="compact">
              <thead>
                <tr>
                  <th class="text-left">Course</th>
                  <th class="text-left">Credits</th>
                  <th class="text-left">Source</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="course in unmatchedCourses"
                  :key="`${course.courseID ?? course.sectionID ?? course.courseName}-${course.source}`"
                >
                  <td>{{ course.courseName }}</td>
                  <td>{{ formatHours(course.credits) }}</td>
                  <td>{{ course.source }}</td>
                </tr>
              </tbody>
            </v-table>
            <p class="text-caption text-medium-emphasis mt-2">
              These classes did not match any parsed requirement keywords. They still count toward overall hours.
            </p>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      timeout="2500"
      location="bottom right"
    >
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useDegreeValidationStore } from '@/stores/degreeValidation'

const store = useDegreeValidationStore()

const form = reactive({
  adviseeId: '',
  documentTitle: '',
  pdfPath: '',
})

const snackbar = ref({ show: false, text: '', color: 'success' })

const report = computed(() => store.report)
const summary = computed(() => report.value?.summary || null)
const requirements = computed(() => report.value?.requirements || [])
const documentInfo = computed(() => report.value?.document || null)
const advisee = computed(() => report.value?.advisee || null)
const unmatchedCourses = computed(() => report.value?.unmatchedCourses || [])

const summaryTiles = computed(() => [
  { title: 'Required hours', value: formatHours(summary.value?.totalRequiredHours) },
  { title: 'Completed hours', value: formatHours(summary.value?.totalCompletedHours) },
  { title: 'In progress', value: formatHours(summary.value?.totalInProgressHours) },
  { title: 'Projected total', value: formatHours(summary.value?.totalProjectedHours) },
])

const showSnackbar = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}

const handleSubmit = async () => {
  if (!form.adviseeId) {
    showSnackbar('Please provide an advisee ID', 'error')
    return
  }

  try {
    await store.fetchReport({
      adviseeId: Number(form.adviseeId),
      documentTitle: form.documentTitle || undefined,
      pdfPath: form.pdfPath || undefined,
    })
    showSnackbar('Validation updated')
  } catch (err) {
    showSnackbar(err.message || 'Failed to validate degree plan', 'error')
  }
}

const handleReset = () => {
  form.adviseeId = ''
  form.documentTitle = ''
  form.pdfPath = ''
  store.resetReport()
  store.clearError()
}

const prefillExample = () => {
  form.adviseeId = '1'
  form.documentTitle = 'Associate of Arts'
  form.pdfPath = ''
}

const statusColor = (status) => {
  switch (status) {
    case 'COMPLETED':
      return 'success'
    case 'IN_PROGRESS':
      return 'warning'
    default:
      return 'grey'
  }
}

const formatHours = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return '—'
  }
  return Number(value).toFixed(1)
}

const progressPercent = (requirement) => {
  if (!requirement?.requiredHours) return 0
  const value = (requirement.completedHours / requirement.requiredHours) * 100
  return Math.max(0, Math.min(100, value))
}
</script>

<style scoped>
.summary-tile {
  min-width: 140px;
}
</style>
