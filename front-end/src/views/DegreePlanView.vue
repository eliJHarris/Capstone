<template>
  <div class="py-6">
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Degree Plan Validation</h2>
        <p class="text-body-2 text-medium-emphasis">
          Track validation runs for {{ currentAdviseeName }} ({{ currentAdviseeMajor }})
        </p>
      </div>

      <v-spacer />

      <!-- IMPORT PDF -->
      <v-btn
        color="primary"
        class="mr-3"
        variant="tonal"
        :loading="degreePlanStore.importing"
        @click="showImportDialog = true"
      >
        Import Degree Audit PDF
      </v-btn>

      <!-- SAMPLE -->
      <v-btn
        color="primary"
        class="mr-3"
        :loading="seeding"
        variant="tonal"
        @click="seedDegreePlan"
      >
        Load Sample Plan
      </v-btn>
    </div>

    <!-- ADVISEE SELECTOR CARD -->
    <v-card rounded="xl" class="mb-4">
      <v-card-text>
        <div class="d-flex flex-column flex-md-row align-start" style="gap: 24px;">
          <div class="flex-grow-1" style="min-width: 260px;">
            <div class="text-subtitle-2 text-medium-emphasis mb-2">Select Advisee</div>

            <v-autocomplete
              v-model="selectedAdviseeId"
              :items="adviseeSelectItems"
              item-title="label"
              item-value="value"
              :loading="adviseeListLoading"
              :disabled="isStudent || adviseeListLoading || !adviseeSelectItems.length"
              density="comfortable"
              hide-details
              prepend-inner-icon="mdi-account-search"
              placeholder="Search by name or ID"
              :clearable="!isStudent"
            >
              <template #no-data>
                <v-list-item
                  title="No advisees found"
                  subtitle="Adjust filters or try again."
                />
              </template>

              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <v-list-item-title>{{ item.raw.label }}</v-list-item-title>
                  <v-list-item-subtitle v-if="item.raw.subtitle">
                    {{ item.raw.subtitle }}
                  </v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-autocomplete>
          </div>

          <div v-if="selectedAdvisee" class="flex-grow-1">
            <div class="text-subtitle-2 text-medium-emphasis mb-1">Snapshot</div>
            <div class="text-h5 font-weight-medium mb-1">{{ selectedAdvisee.name }}</div>
            <div class="text-body-2 text-medium-emphasis mb-2">
              Advisee #{{ selectedAdvisee.adviseeID }} • {{ selectedAdvisee.status || 'Active' }}
            </div>
            <div class="text-body-2">Major: {{ selectedAdvisee.major || 'Not provided' }}</div>
            <div class="text-body-2">Classification: {{ selectedAdvisee.classification || 'n/a' }}</div>
          </div>

          <div v-else class="flex-grow-1 text-medium-emphasis">
            Select an advisee to load their degree plan summary and completion status.
          </div>
        </div>

        <v-alert
          v-if="adviseeListError"
          type="warning"
          variant="tonal"
          class="mt-4"
        >
          {{ adviseeListError }}
        </v-alert>
      </v-card-text>
    </v-card>

    <!-- IMPORT PDF DIALOG -->
    <v-dialog v-model="showImportDialog" max-width="500">
      <v-card>
        <v-card-title>Import Degree Audit PDF</v-card-title>

        <v-card-text>
          <v-text-field
            v-model="pdfURL"
            clearable
            label="Enter PDF URL"
          />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn text @click="showImportDialog = false">Cancel</v-btn>

          <v-btn
            color="primary"
            :loading="degreePlanStore.importing"
            @click="importPdfUrl"
          >
            Import
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ERRORS -->
    <v-alert v-if="userContextError" type="error" class="mb-4" variant="tonal">
      {{ userContextError }}
    </v-alert>

    <v-alert v-if="isStudent" type="info" class="mb-4" variant="tonal">
      You are viewing your own degree plan.
    </v-alert>

    <v-alert
      v-if="degreePlanStore.error"
      type="error"
      class="mb-4"
      closable
      @click:close="degreePlanStore.error = null"
    >
      {{ degreePlanStore.error }}
    </v-alert>

    <!-- MAIN GRID -->
    <v-row dense>
      <!-- COMPLETION CARD -->
      <v-col cols="12" md="4" v-if="requirementInfo && !degreePlanStore.loading">
        <v-card rounded="xl" class="mb-4">
          <v-card-text class="text-center">
            <div class="text-subtitle-2 text-medium-emphasis mb-2">Completion</div>

            <v-progress-circular
              :model-value="degreePlanStore.completionPercent"
              :color="statusColor"
              size="160"
              width="16"
            >
              <div class="text-h5 font-weight-medium">
                {{ degreePlanStore.completionPercent.toFixed(1) }}%
              </div>
            </v-progress-circular>

            <div class="mt-4 text-body-2">
              Status:
              <span :class="`text-${statusColor}`">
                {{ degreePlanStore.validationStatus }}
              </span>
            </div>

            <div class="text-caption text-medium-emphasis">
              Last run: {{ lastValidationRun || 'n/a' }}
            </div>
          </v-card-text>

          <v-divider />

          <v-list density="comfortable">
            <v-list-item>
              <v-list-item-title>Program</v-list-item-title>
              <v-list-item-subtitle>
                {{ requirementInfo?.programName || 'Not linked' }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Catalog Year</v-list-item-title>
              <v-list-item-subtitle>
                {{ requirementInfo?.catalogYear || 'Unknown' }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Total Credits</v-list-item-title>
              <v-list-item-subtitle>
                {{ totalCreditsDisplay ?? requirementInfo?.totalCredits ?? '—' }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <v-divider />

          <v-card-text class="pt-4">
            <div class="text-subtitle-2 text-medium-emphasis mb-3">Category Completion</div>
            <div class="mb-4">
              <div class="text-body-2 font-weight-medium mb-1">Major</div>
              <v-progress-linear
                :model-value="majorCompletionPercent"
                height="6"
                rounded
                color="primary"
                class="mb-1"
              />
              <div class="text-caption text-medium-emphasis">
                {{ majorCompletionPercent.toFixed(1) }}% complete
              </div>
            </div>
            <div v-if="hasMinorCategoryData">
              <div class="text-body-2 font-weight-medium mb-1">Minor</div>
              <v-progress-linear
                :model-value="minorCompletionPercent"
                height="6"
                rounded
                color="secondary"
                class="mb-1"
              />
              <div class="text-caption text-medium-emphasis">
                {{ minorCompletionPercent.toFixed(1) }}% complete
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- RIGHT SIDE -->
      <v-col cols="12" md="8">
        <!-- GENERAL EDUCATION -->
        <v-card
          v-if="generalEducationSummary.length"
          rounded="xl"
          class="mb-4"
        >
          <v-card-title class="d-flex align-center">
            General Education Progress
            <v-spacer />

            <v-chip
              size="small"
              color="secondary"
              variant="tonal"
              class="mr-2"
            >
              {{ degreePlanStore.generalEducationCompletionPercent.toFixed(1) }}% complete
            </v-chip>
          </v-card-title>

          <v-card-text>
            <div
              v-for="group in generalEducationSummary"
              :key="group.groupId || group.title"
              class="mb-6"
            >
              <div class="d-flex align-center justify-space-between mb-2">
                <div>
                  <div class="text-subtitle-1">
                    {{ group.title || 'General Education Requirement' }}
                  </div>

                  <div class="text-caption text-medium-emphasis">
                    {{ group.description ||
                      `Complete ${group.requiredSelections} selection(s) from this area.` }}
                  </div>
                </div>

                <v-chip
                  size="small"
                  :color="
                    group.satisfiedSelections >= group.requiredSelections
                      ? 'success'
                      : 'warning'
                  "
                >
                  {{ group.satisfiedSelections }} /
                  {{ group.requiredSelections }}
                </v-chip>
              </div>

              <v-progress-linear
                :model-value="generalEducationProgress(group)"
                height="6"
                rounded
                color="primary"
                class="mb-3"
              />
              
              <!-- completed -->
              <div class="text-caption text-medium-emphasis mb-1">
                Completed Courses
              </div>
              <div>
                <v-chip
                  v-for="course in group.takenCourses"
                  :key="course"
                  size="x-small"
                  class="ma-1"
                  color="success"
                  variant="tonal"
                >
                  {{ course }}
                </v-chip>
                <div v-if="!group.takenCourses.length"
                  class="text-caption text-medium-emphasis">
                  No courses completed yet.
                </div>
              </div>

              <!-- available -->
              <div class="text-caption text-medium-emphasis mt-3 mb-1">
                Available Options
              </div>
              <div>
                <v-chip
                  v-for="course in group.remainingCourses"
                  :key="course"
                  size="x-small"
                  class="ma-1"
                  color="info"
                  variant="outlined"
                >
                  {{ course }}
                </v-chip>
              </div>
            </div>
          </v-card-text>
        </v-card>

        <!-- CONCENTRATIONS / MINORS -->
        <v-card
          v-if="hasConcentrationSection"
          rounded="xl"
          class="mb-4"
        >
          <v-card-title class="d-flex align-center flex-wrap" style="gap: 8px;">
            Focus Areas
            <v-spacer />
            <div class="d-flex align-center flex-wrap" style="gap: 8px;">
              <v-chip
                v-if="concentrationSummary.length || concentrationRequirementCount > 0"
                size="small"
                color="primary"
                variant="tonal"
              >
                Concentrations {{ degreePlanStore.concentrationCompletionPercent.toFixed(1) }}%
              </v-chip>
              <v-chip
                v-if="minorSummary.length || minorRequirementCount > 0"
                size="small"
                color="secondary"
                variant="tonal"
              >
                Minors {{ minorCompletionPercent.toFixed(1) }}%
              </v-chip>
            </div>
            <span class="text-caption text-medium-emphasis">
              Updated with most recent validation
            </span>
          </v-card-title>

          <v-card-text>
            <template v-if="hasFocusGroups">
              <template
                v-for="(section, sectionIndex) in focusSections"
                :key="section.key"
              >
                <div class="d-flex align-center justify-space-between mb-3">
                  <div>
                    <div class="text-subtitle-1">{{ section.title }}</div>
                    <div class="text-caption text-medium-emphasis">
                      Tracking specialized selections from this area.
                    </div>
                  </div>

                  <v-chip
                    size="small"
                    :color="section.key === 'MINOR' ? 'secondary' : 'primary'"
                    variant="tonal"
                  >
                    {{ section.completion.toFixed(1) }}% complete
                  </v-chip>
                </div>

                <div
                  v-for="group in section.groups"
                  :key="`${section.key}-${group.groupId || group.title}`"
                  class="mb-6"
                >
                  <div class="d-flex align-center justify-space-between mb-2">
                    <div>
                      <div class="text-subtitle-2">
                        {{ group.title || (section.key === 'MINOR' ? 'Minor Option' : 'Concentration') }}
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        Tracking {{ group.requiredSelections }} selection{{ group.requiredSelections === 1 ? '' : 's' }}
                      </div>
                    </div>

                    <v-chip
                      size="small"
                      :color="group.satisfiedSelections === group.requiredSelections ? 'primary' : 'warning'"
                      variant="tonal"
                    >
                      {{ group.satisfiedSelections }} / {{ group.requiredSelections }} met
                    </v-chip>
                  </div>

                  <v-row dense>
                    <v-col
                      v-for="option in group.options"
                      :key="`${section.key}-${group.groupId || group.title}-${option.name}`"
                      cols="12"
                      md="6"
                    >
                      <v-sheet class="pa-3 requirement-option" rounded="lg">
                        <div class="d-flex align-center justify-space-between mb-1">
                          <div class="text-subtitle-2">{{ option.name }}</div>
                          <v-chip
                            size="x-small"
                            :color="option.satisfied ? 'primary' : 'warning'"
                            variant="tonal"
                          >
                            {{ option.completedHours }} / {{ option.requiredHours }} hrs
                          </v-chip>
                        </div>

                        <v-progress-linear
                          :model-value="concentrationProgress(option)"
                          height="6"
                          rounded
                          color="primary"
                          class="mb-2"
                        />

                        <div class="text-caption text-medium-emphasis mb-1">
                          Outstanding Courses
                        </div>
                        <div>
                          <v-chip
                            v-for="course in option.missingCourses"
                            :key="`${option.name}-${course}`"
                            size="x-small"
                            class="ma-1"
                            color="primary"
                            variant="outlined"
                          >
                            {{ course }}
                          </v-chip>
                          <div
                            v-if="!option.missingCourses.length"
                            class="text-caption text-medium-emphasis"
                          >
                            No outstanding courses for this {{ section.key === 'MINOR' ? 'minor' : 'concentration' }}.
                          </div>
                        </div>

                        <div v-if="option.takenCourses?.length">
                          <div class="text-caption text-medium-emphasis mt-3 mb-1">
                            Completed Courses
                          </div>
                          <div>
                            <v-chip
                              v-for="taken in option.takenCourses"
                              :key="`${option.name}-taken-${taken}`"
                              size="x-small"
                              class="ma-1"
                              color="success"
                              variant="tonal"
                            >
                              {{ taken }}
                            </v-chip>
                          </div>
                        </div>
                      </v-sheet>
                    </v-col>
                  </v-row>
                </div>

                <v-divider
                  v-if="sectionIndex < focusSections.length - 1"
                  class="my-6"
                />
              </template>
            </template>

            <v-alert
              v-else
              type="info"
              variant="tonal"
              class="mb-0"
            >
              Concentration and minor details will appear after the imported PDF includes
              structured options for those requirements. Re-run validation once the plan finishes importing.
            </v-alert>
          </v-card-text>
        </v-card>

        <!-- OUTSTANDING REQUIREMENTS -->
        <v-card rounded="xl">
          <v-card-title class="d-flex align-center">
            Outstanding Requirements

            <v-chip
              v-if="issues.length"
              size="small"
              class="ml-2"
              color="warning"
            >
              {{ issues.length }} issue(s)
            </v-chip>

            <v-spacer />

            <span class="text-caption text-medium-emphasis">
              Auto validations run whenever the plan changes
            </span>
          </v-card-title>

          <v-card-text>
            <v-skeleton-loader
              v-if="degreePlanStore.loading"
              type="list-item-two-line"
            />

            <template v-else>
              <v-alert
                v-if="!requirementInfo"
                type="info"
                variant="tonal"
              >
                No requirement set linked. Import a degree audit PDF or load sample data.
              </v-alert>

              <v-alert
                v-else-if="!issues.length"
                type="success"
                variant="tonal"
              >
                All tracked requirements are satisfied.
              </v-alert>

              <template v-else>
                <div
                  v-for="section in issueSections"
                  :key="section.key"
                  class="mb-6"
                >
                  <div class="text-subtitle-1 mb-2">
                    {{ section.title }}
                    <span class="text-caption text-medium-emphasis">
                      ({{ section.items.length }} issue{{ section.items.length === 1 ? '' : 's' }})
                    </span>
                  </div>
                  <v-timeline density="compact">
                    <v-timeline-item
                      v-for="issue in section.items"
                      :key="`${section.key}-${issue.requirementId || issue.message}`"
                      dot-color="warning"
                    >
                      <v-card variant="tonal" color="warning">
                        <v-card-title>{{ issue.requirementId }}</v-card-title>

                        <v-card-text>
                          <p class="mb-2">{{ issue.message }}</p>

                          <div class="text-body-2">
                            Missing:
                            <v-chip
                              v-for="c in issue.missingCourses"
                              :key="`${issue.requirementId}-${c}`"
                              size="small"
                              class="ma-1"
                            >
                              {{ c }}
                            </v-chip>
                          </div>
                        </v-card-text>
                      </v-card>
                    </v-timeline-item>
                  </v-timeline>
                </div>
              </template>
            </template>
          </v-card-text>
        </v-card>

      </v-col>
    </v-row>
  </div>
</template>
<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useStudentProfileStore } from '@/stores/studentProfile'
import { useDegreePlanStore } from '@/stores/degreePlans'
import { saveRequirementSet } from '@/services/degreePlans'
import { fetchAdvisees } from '@/services/advisees'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { NORMALIZED_ROLES } from '@/utils/auth'

const CONCENTRATION_CONTAINER_KEYS = [
  'concentrations',
  'concentrationOptions',
  'concentration_groups',
  'concentrationTracks',
  'tracks',
]
const CONCENTRATION_NESTED_KEYS = [
  'groups',
  'children',
  'sections',
  'subsections',
  'subSections',
  'requirementGroups',
  'areas',
]

/* ---------------------------------
   STORES & USER CONTEXT
----------------------------------*/
const studentStore = useStudentProfileStore()
const degreePlanStore = useDegreePlanStore()
const {
  role: userRole,
  advisee: currentAdvisee,
  loadUserContext,
  error: userContextError,
} = useCurrentUser()

const isStudent = computed(() => userRole.value === NORMALIZED_ROLES.STUDENT)

/* ---------------------------------
   UI STATE
----------------------------------*/
const seeding = ref(false)
const showImportDialog = ref(false)
const pdfURL = ref("")

/* ---------------------------------
   ADVISEE LIST MANAGEMENT
----------------------------------*/
const advisees = ref([])
const selectedAdviseeId = ref(null)
const adviseeListLoading = ref(false)
const adviseeListError = ref(null)

const FALLBACK_ADVISEES = [
  { adviseeID: 1, name: 'Jordan Casey', email: 'jcasey@college.edu', major: 'B.S. Computer Science', classification: 'Senior', status: 'Active' },
  { adviseeID: 2, name: 'Ariel Summers', email: 'asummers@college.edu', major: 'B.S. Mathematics', classification: 'Junior', status: 'Active' },
  { adviseeID: 3, name: 'Priya Patel', email: 'ppatel@college.edu', major: 'B.S. Information Systems', classification: 'Senior', status: 'Active' },
]

/* ---------------------------------
   PROFILE + ADVISEE SELECTION
----------------------------------*/
const profile = computed(() => studentStore.studentProfile)

const studentAdviseeId = computed(() =>
  currentAdvisee.value?.adviseeID
    ? Number(currentAdvisee.value.adviseeID)
    : profile.value?.advisee_id
)

const adviseeId = computed(() =>
  selectedAdviseeId.value || studentAdviseeId.value || profile.value?.advisee_id
)

const activeAdviseeId = computed(() => {
  const value = adviseeId.value
  return value ? Number(value) : null
})

const selectedAdvisee = computed(() =>
  advisees.value.find((a) => a.adviseeID === selectedAdviseeId.value) || null
)

const currentAdviseeName = computed(() =>
  selectedAdvisee.value?.name ||
  profile.value?.student_name ||
  'Advisee'
)

const currentAdviseeMajor = computed(() =>
  selectedAdvisee.value?.major ||
  profile.value?.major ||
  'Major TBD'
)

const adviseeSelectItems = computed(() =>
  advisees.value.map((item) => ({
    value: item.adviseeID,
    label: `${item.name} (#${item.adviseeID})`,
    subtitle: item.email || item.major,
  }))
)

/* ---------------------------------
   FORMATTER
----------------------------------*/
function formatDate(value) {
  if (!value) return null
  return new Date(value).toLocaleString()
}

const lastValidationRun = computed(() => {
  const validation = degreePlanStore.latestValidation
  if (!validation) return null
  return formatDate(validation.finishedAt || validation.createdAt)
})

/* ---------------------------------
   STATUS COLORS
----------------------------------*/
const statusColor = computed(() => {
  switch (degreePlanStore.validationStatus) {
    case 'PASSED': return 'success'
    case 'FAILED': return 'error'
    case 'RUNNING': return 'warning'
    default: return 'primary'
  }
})

/* ---------------------------------
   REQUIREMENT & PROGRESS DATA
----------------------------------*/
const requirementInfo = computed(() => degreePlanStore.requirementSet)
const requirementData = computed(() => {
  const raw = requirementInfo.value?.requirementData
  if (!raw) return []
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
})

const totalCreditsDisplay = computed(() => {
  const sel = selectedAdvisee.value
  if (sel?.creditsCompleted != null) return Number(sel.creditsCompleted)
  const prog = profile.value?.progress?.creditHoursCompleted
  if (prog != null) return Number(prog)
  return null
})

const issues = computed(() => degreePlanStore.latestValidation?.issues || [])
const generalEducationSummary = computed(() => degreePlanStore.latestValidation?.generalEducation || [])
const concentrationSummary = computed(() => degreePlanStore.latestValidation?.concentrations || [])
const concentrationIssues = computed(() => degreePlanStore.latestValidation?.concentrationIssues || [])
const concentrationRequirementCount = computed(
  () => degreePlanStore.latestValidation?.concentrationRequirementCount || 0
)
const minorSummary = computed(() => degreePlanStore.latestValidation?.minors || [])
const minorIssues = computed(() => degreePlanStore.latestValidation?.minorIssues || [])
const minorRequirementCount = computed(
  () => degreePlanStore.latestValidation?.minorRequirementCount || 0
)
const minorCompletionPercent = computed(
  () => degreePlanStore.latestValidation?.minorCompletionPercent ?? 0
)
const majorCompletionPercent = computed(
  () => degreePlanStore.latestValidation?.majorCompletionPercent ?? 0
)
const requirementHasConcentrations = computed(() =>
  requirementDataHasConcentrations(requirementData.value)
)
const focusSections = computed(() => {
  const sections = []
  if (concentrationSummary.value.length) {
    sections.push({
      key: 'CONCENTRATION',
      title: 'Concentrations',
      completion: degreePlanStore.concentrationCompletionPercent,
      groups: concentrationSummary.value,
    })
  }
  if (minorSummary.value.length) {
    sections.push({
      key: 'MINOR',
      title: 'Minors',
      completion: minorCompletionPercent.value,
      groups: minorSummary.value,
    })
  }
  return sections
})
const hasFocusGroups = computed(() => focusSections.value.length > 0)
const hasConcentrationSection = computed(
  () =>
    hasFocusGroups.value ||
    concentrationIssues.value.length > 0 ||
    minorIssues.value.length > 0 ||
    concentrationRequirementCount.value > 0 ||
    minorRequirementCount.value > 0 ||
    requirementHasConcentrations.value
)
const hasMinorCategoryData = computed(
  () =>
    minorSummary.value.length > 0 ||
    minorRequirementCount.value > 0 ||
    minorIssues.value.length > 0
)
const issueBuckets = computed(() => {
  const buckets = {
    MAJOR: [],
    MINOR: [],
    CONCENTRATION: [],
    OTHER: [],
  }
  issues.value.forEach((issue) => {
    const key = (issue.category || '').toUpperCase()
    if (key && buckets[key]) {
      buckets[key].push(issue)
    } else {
      buckets.OTHER.push(issue)
    }
  })
  return buckets
})
const issueSections = computed(() => [
  { key: 'MAJOR', title: 'Major Requirements', items: issueBuckets.value.MAJOR },
  { key: 'MINOR', title: 'Minor Requirements', items: issueBuckets.value.MINOR },
  { key: 'CONCENTRATION', title: 'Concentrations / Focus Areas', items: issueBuckets.value.CONCENTRATION },
  { key: 'OTHER', title: 'Advisory / Other Checks', items: issueBuckets.value.OTHER },
].filter((section) => section.items.length))

/* ---------------------------------
   PROGRESS HELPERS
----------------------------------*/
function concentrationProgress(option) {
  if (!option) return 0
  const required = Math.max(option.requiredHours || 0, 0.01)
  const raw = (option.completedHours || 0) / required
  return Math.min(100, Math.max(0, raw * 100))
}

function generalEducationProgress(group) {
  if (!group) return 0
  const required = Math.max(group.requiredSelections || 0, 0.01)
  const completed = Math.min(group.satisfiedSelections || 0, required)
  return Math.min(100, (completed / required) * 100)
}

/* ---------------------------------
   IMPORT PDF
----------------------------------*/
async function importPdfUrl() {
  if (!activeAdviseeId.value) return
  try {
    await degreePlanStore.importDegreePlan(activeAdviseeId.value, pdfURL.value)
    showImportDialog.value = false
    pdfURL.value = ""
  } catch (err) {
    console.error(err)
  }
}

/* ---------------------------------
   AUTO VALIDATION
----------------------------------*/
async function autoValidatePlan(targetAdviseeId = activeAdviseeId.value) {
  if (!targetAdviseeId || degreePlanStore.importing) return
  try {
    await degreePlanStore.triggerValidation(targetAdviseeId)
  } catch (error) {
    console.error('Failed auto-validation:', error)
  }
}

/* ---------------------------------
   LOAD SUMMARY
----------------------------------*/
async function loadSummary(id = activeAdviseeId.value) {
  if (!id) return
  await degreePlanStore.loadSummary(id)
}

/* ---------------------------------
   ADVISEE DIRECTORY
----------------------------------*/
async function loadAdviseeDirectory() {
  adviseeListLoading.value = true
  adviseeListError.value = null

  try {
    if (isStudent.value) {
      if (currentAdvisee.value?.adviseeID) {
        advisees.value = [{
          adviseeID: Number(currentAdvisee.value.adviseeID),
          name: currentAdvisee.value.name,
          email: currentAdvisee.value.email,
          major: currentAdvisee.value.major,
          classification: currentAdvisee.value.classification,
          status: currentAdvisee.value.status,
          creditsCompleted: currentAdvisee.value.creditsCompleted ?? null,
        }]
      } else {
        adviseeListError.value = 'No advisee profile found.'
        advisees.value = []
      }
    } else {
      const data = await fetchAdvisees({ limit: 200 })
      advisees.value = data.map((item) => ({
        adviseeID: Number(item.adviseeID),
        name: item.name,
        email: item.email,
        major: item.major,
        classification: item.classification,
        status: item.status,
        creditsCompleted: item.creditsCompleted ?? null,
      }))
    }
  } catch (error) {
    console.error(error)
    adviseeListError.value = error.message || 'Failed to load advisees'
    advisees.value = FALLBACK_ADVISEES
  } finally {
    adviseeListLoading.value = false

    const preferred = Number(adviseeId.value) || null
    const defaultId =
      advisees.value.find((a) => a.adviseeID === preferred)?.adviseeID ||
      advisees.value[0]?.adviseeID ||
      null

    if (defaultId && selectedAdviseeId.value !== defaultId) {
      selectedAdviseeId.value = Number(defaultId)
    }
  }
}

/* ---------------------------------
   SAMPLE SEEDING
----------------------------------*/
const sampleRequirementTemplate = computed(() => ({
  programCode: profile.value.program_code || '',
  catalogYear: profile.value.catalog_year || '',
  programName: profile.value.major || '',
  totalCredits: profile.value.totalCredits || 0,

  requirementGroups: [
    {
      id: 'core',
      title: 'Core Curriculum',
      requiredCredits: 36,
      description: 'Foundational coursework required for graduation.',
      courses: [
        { code: 'ENG 1013', title: 'Composition I', credits: 3 },
        { code: 'MATH 2804', title: 'Calculus I', credits: 4 },
        { code: 'CS 1013', title: 'Intro to Programming', credits: 3 },
        { code: 'CS 2023', title: 'Data Structures', credits: 3 },
      ],
    },
    {
      id: 'advanced',
      title: 'Advanced Major Requirements',
      requiredCredits: 24,
      courses: [
        { code: 'CS 3013', title: 'Algorithms', credits: 3 },
        { code: 'CS 3223', title: 'Operating Systems', credits: 3 },
        { code: 'CS 3413', title: 'Database Systems', credits: 3 },
        { code: 'CS 4XX3', title: 'Upper-Level Electives', credits: 9 },
      ],
    },
  ],
}))

const sampleCompletedCourses = [
  { code: 'ENG 1013', title: 'Composition I', credits: 3, term: 'Fall 2023' },
  { code: 'MATH 2804', title: 'Calculus I', credits: 4, term: 'Fall 2023' },
  { code: 'CS 1013', title: 'Intro to Programming', credits: 3, term: 'Fall 2023' },
  { code: 'CS 2023', title: 'Data Structures', credits: 3, term: 'Spring 2024' },
  { code: 'CS 3013', title: 'Algorithms', credits: 3, term: 'Spring 2024' },
]

async function seedDegreePlan() {
  if (!activeAdviseeId.value || seeding.value) return

  seeding.value = true

  try {
    const requirement = await saveRequirementSet(sampleRequirementTemplate.value)

    await degreePlanStore.syncContext(
      activeAdviseeId.value,
      {
        requirementSetID: requirement.requirementSetID,
        completedCourses: sampleCompletedCourses,
        notes: 'Sample data loaded from UI seeding tool.',
      },
      { autoValidate: true }
    )
  } catch (err) {
    console.error(err)
  } finally {
    seeding.value = false
  }
}

/* ---------------------------------
   CONCENTRATION HELPERS
----------------------------------*/
function requirementDataHasConcentrations(payload) {
  if (!Array.isArray(payload)) return false
  return payload.some((entry) => groupContainsConcentration(entry))
}

function groupContainsConcentration(entry) {
  if (!entry || typeof entry !== 'object') return false

  for (const key of CONCENTRATION_CONTAINER_KEYS) {
    const value = entry[key]
    if (Array.isArray(value) ? value.length : Boolean(value)) {
      return true
    }
  }

  for (const nestedKey of CONCENTRATION_NESTED_KEYS) {
    const nested = entry[nestedKey]
    if (Array.isArray(nested) && nested.some((child) => groupContainsConcentration(child))) {
      return true
    }
    if (nested && typeof nested === 'object' && groupContainsConcentration(nested)) {
      return true
    }
  }

  return false
}

/* ---------------------------------
   WATCHERS
----------------------------------*/
watch(
  () => adviseeId.value,
  (newId) => {
    if (newId && newId !== selectedAdviseeId.value) {
      selectedAdviseeId.value = Number(newId)
    }
  }
)

watch(selectedAdviseeId, async (newId, oldId) => {
  if (!newId || newId === oldId) return

  const selected = advisees.value.find((a) => a.adviseeID === newId)

  if (selected) {
    studentStore.updateProfile({
      advisee_id: selected.adviseeID,
      student_name: selected.name,
      major: selected.major || profile.value.major,
    })
  } else {
    studentStore.updateProfile({ advisee_id: newId })
  }

  await loadSummary(newId)
  await autoValidatePlan(newId)
})

/* ---------------------------------
   INITIALIZATION
----------------------------------*/
onMounted(async () => {
  try {
    await loadUserContext()
  } catch (err) {
    console.error("User context failed:", err)
  }

  await loadAdviseeDirectory()
})
</script>
<style scoped>
/* Keep soft shadow aesthetic consistent across all requirement cards */
.requirement-option {
  background-color: rgb(var(--v-theme-surface));
  color: rgb(var(--v-theme-on-surface));
  border: 1px solid rgba(var(--v-theme-primary), 0.14);
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.08);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.requirement-option:hover {
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.12);
  transform: translateY(-2px);
}

/* Improve timeline spacing so cards don't overlap */
.v-timeline {
  margin-top: 8px;
}

/* Tightens up spacing between timeline items */
.v-timeline-item {
  margin-bottom: 16px;
}

/* Make tonal cards inside timelines more readable in dark mode */
.v-card[variant="tonal"] {
  backdrop-filter: blur(4px);
}

/* Standardize chip spacing */
.v-chip {
  margin: 2px;
}
</style>
