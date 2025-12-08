<template>
  <div class="py-6 degree-plan-page">

    <!-- HEADER -->
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Degree Plan Validation</h2>
        <p class="text-body-2 text-medium-emphasis">
          Advisors can browse any student. Students only view their own degree plan.
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
        variant="tonal"
        :loading="seeding"
        @click="seedDegreePlan"
      >
        Load Sample Plan
      </v-btn>
    </div>

    <!-- ERRORS -->
    <v-alert
      v-if="userContextError"
      type="warning"
      variant="tonal"
      class="mb-4"
    >
      {{ userContextError }}
    </v-alert>

    <v-alert
      v-if="degreePlanStore.error"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      @click:close="degreePlanStore.error = null"
    >
      {{ degreePlanStore.error }}
    </v-alert>

    <!-- ADVISEE SELECTION CARD -->
    <v-card rounded="xl" class="mb-4">
      <v-card-text>
        <div class="d-flex flex-column flex-md-row align-start" style="gap: 24px;">

          <!-- ADVISEE SELECT -->
          <div class="flex-grow-1" style="min-width: 260px;">
            <div class="text-subtitle-2 text-medium-emphasis mb-2">Select Advisee</div>

            <template v-if="isStudent">
              <v-alert density="compact" color="primary" variant="tonal">
                You are viewing your own degree plan.
              </v-alert>
            </template>

            <template v-else>
              <v-autocomplete
                v-model="selectedAdviseeId"
                :items="adviseeSelectItems"
                item-title="label"
                item-value="value"
                :loading="adviseeListLoading"
                clearable
                hide-details
                prepend-inner-icon="mdi-account-search"
                density="comfortable"
                placeholder="Search by name or ID"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props">
                    <v-list-item-title>{{ item.raw.label }}</v-list-item-title>
                    <v-list-item-subtitle>{{ item.raw.subtitle }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-autocomplete>
            </template>
          </div>

          <!-- SNAPSHOT -->
          <div v-if="context" class="flex-grow-1">
            <div class="text-subtitle-2 text-medium-emphasis mb-1">Snapshot</div>

            <div class="text-h5 font-weight-medium mb-1">{{ context.name }}</div>

            <div class="text-body-2 text-medium-emphasis mb-2">
              Advisee #{{ context.adviseeID }} • {{ context.classification || '—' }}
            </div>

            <div class="text-body-2">Major: {{ context.major }}</div>
            <div class="text-body-2">Catalog Year: {{ context.catalogYear }}</div>
          </div>

          <div v-else class="flex-grow-1 text-medium-emphasis">
            Select an advisee to load their degree plan.
          </div>

        </div>
      </v-card-text>
    </v-card>

    <!-- IMPORT PDF DIALOG -->
    <v-dialog v-model="showImportDialog" max-width="500">
      <v-card>
        <v-card-title>Import Degree Audit PDF</v-card-title>

        <v-card-text>
          <v-text-field v-model="pdfURL" clearable label="Enter PDF URL" />
        </v-card-text>

        <v-card-actions>
          <v-spacer />
          <v-btn text @click="showImportDialog = false">Cancel</v-btn>

          <v-btn
            color="primary"
            :loading="degreePlanStore.importing"
            @click="importPdf"
          >
            Import
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- MAIN CONTENT -->
    <v-row dense v-if="context && latestValidation">

      <!-- LEFT COLUMN: COMPLETION WHEEL -->
      <v-col cols="12" md="4">
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
                {{ latestValidation.status }}
              </span>
            </div>

            <div class="text-caption text-medium-emphasis">
              Last run: {{ formattedLastRun }}
            </div>
          </v-card-text>

          <!-- PROGRAM INFO -->
          <v-divider />

          <v-list density="comfortable">
            <v-list-item>
              <v-list-item-title>Program</v-list-item-title>
              <v-list-item-subtitle>
                {{ context.major }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Catalog Year</v-list-item-title>
              <v-list-item-subtitle>
                {{ context.catalogYear || '—' }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Total Credits</v-list-item-title>
              <v-list-item-subtitle>
                {{ latestValidation.totalCredits ?? '—' }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>

          <!-- CATEGORY COMPLETION -->
          <v-divider />

          <v-card-text class="pt-4">
            <div class="text-subtitle-2 text-medium-emphasis mb-3">Category Completion</div>

            <div class="mb-4">
              <div class="text-body-2 font-weight-medium mb-1">Major</div>
              <v-progress-linear
                :model-value="majorPercent"
                height="6"
                rounded
                color="primary"
              />
              <div class="text-caption text-medium-emphasis">
                {{ majorPercent.toFixed(1) }}% complete
              </div>
            </div>

            <div v-if="minorPercent > 0">
              <div class="text-body-2 font-weight-medium mb-1">Minor</div>
              <v-progress-linear
                :model-value="minorPercent"
                height="6"
                rounded
                color="secondary"
              />
              <div class="text-caption text-medium-emphasis">
                {{ minorPercent.toFixed(1) }}% complete
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- RIGHT COLUMN -->
      <v-col cols="12" md="8">

        <!-- GENERAL EDUCATION -->
        <v-card v-if="generalEd.length" rounded="xl" class="mb-4">
          <v-card-title class="d-flex align-center">
            General Education Progress
            <v-spacer />
            <v-chip size="small" color="secondary" variant="tonal">
              {{ degreePlanStore.generalEducationCompletionPercent.toFixed(1) }}%
            </v-chip>
          </v-card-title>

          <v-card-text>
            <div v-for="group in generalEd" :key="group.title" class="mb-6">
              <div class="d-flex align-center justify-space-between mb-2">
                <div>
                  <div class="text-subtitle-1">{{ group.title }}</div>
                  <div class="text-caption text-medium-emphasis">
                    Complete {{ group.requiredSelections }} selection(s)
                  </div>
                </div>

                <v-chip size="small" :color="group.satisfiedSelections >= group.requiredSelections ? 'success' : 'warning'">
                  {{ group.satisfiedSelections }} / {{ group.requiredSelections }}
                </v-chip>
              </div>

              <v-progress-linear
                :model-value="generalEdProgress(group)"
                height="6"
                rounded
                class="mb-3"
              />
            </div>
          </v-card-text>
        </v-card>

        <!-- CONCENTRATION & MINOR SECTION -->
        <v-card v-if="hasFocusAreas" rounded="xl" class="mb-4">
          <v-card-title class="d-flex align-center">
            Focus Areas
            <v-spacer />

            <v-chip size="small" color="primary" variant="tonal" v-if="concentrationPercent > 0">
              Concentrations {{ concentrationPercent.toFixed(1) }}%
            </v-chip>

            <v-chip size="small" color="secondary" variant="tonal" v-if="minorPercent > 0">
              Minors {{ minorPercent.toFixed(1) }}%
            </v-chip>

          </v-card-title>

          <v-card-text>
            <div v-for="section in focusSections" :key="section.key" class="mb-6">
              <div class="d-flex align-center justify-space-between mb-2">
                <div>
                  <div class="text-subtitle-2">{{ section.title }}</div>
                </div>

                <v-chip size="small" :color="section.completion >= 100 ? 'success' : 'warning'" variant="tonal">
                  {{ section.completion.toFixed(1) }}%
                </v-chip>
              </div>

              <v-row dense>
                <v-col
                  cols="12"
                  md="6"
                  v-for="area in section.groups"
                  :key="area.title"
                >
                  <v-sheet class="pa-3 requirement-option" rounded="lg">
                    <div class="d-flex align-center justify-space-between mb-1">
                      <div class="text-subtitle-2">{{ area.title }}</div>

                      <v-chip size="x-small" color="primary" variant="tonal">
                        {{ area.completedHours }} / {{ area.requiredHours }} hrs
                      </v-chip>
                    </div>

                    <v-progress-linear
                      :model-value="concentrationProgress(area)"
                      height="6"
                      rounded
                      class="mb-2"
                    />

                    <div class="text-caption text-medium-emphasis mb-1">Outstanding Courses</div>
                    <div>
                      <v-chip
                        v-for="c in area.missingCourses"
                        :key="c"
                        size="x-small"
                        class="ma-1"
                        color="primary"
                        variant="outlined"
                      >
                        {{ c }}
                      </v-chip>
                    </div>
                  </v-sheet>
                </v-col>
              </v-row>

            </div>
          </v-card-text>
        </v-card>

        <!-- LLM BREAKDOWN -->
        <v-card v-if="llmNeeded.length || llmTaken.length" rounded="xl" class="mb-4">
          <v-card-title class="d-flex align-center">
            LLM Course Breakdown
            <v-spacer />
            <v-chip size="small" :color="llmNeeded.length ? 'error' : 'success'" variant="tonal">
              {{ llmNeeded.length ? 'Outstanding Work' : 'No Outstanding Courses' }}
            </v-chip>
          </v-card-title>

          <v-card-text>
            <div class="text-subtitle-2 text-medium-emphasis mb-2">Needed Courses</div>
            <div v-if="llmNeeded.length">
              <v-chip
                v-for="n in llmNeeded"
                :key="n"
                size="small"
                class="ma-1"
                color="warning"
                variant="tonal"
              >
                {{ n }}
              </v-chip>
            </div>

            <div class="text-subtitle-2 text-medium-emphasis mt-4 mb-1">
              Completed Courses (LLM)
            </div>
            <div>
              <v-chip
                v-for="t in llmTaken"
                :key="t"
                size="small"
                class="ma-1"
                color="success"
                variant="tonal"
              >
                {{ t }}
              </v-chip>
            </div>
          </v-card-text>
        </v-card>

        <!-- OUTSTANDING REQUIREMENTS -->
        <v-card rounded="xl">
          <v-card-title class="d-flex align-center">
            Outstanding Requirements

            <v-chip v-if="issues.length" size="small" class="ml-2" color="warning">
              {{ issues.length }} issue(s)
            </v-chip>

            <v-spacer />
            <span class="text-caption text-medium-emphasis">
              Auto validations run whenever the plan changes
            </span>
          </v-card-title>

          <v-card-text>

            <v-alert v-if="!issues.length" type="success" variant="tonal">
              All tracked requirements are satisfied.
            </v-alert>

            <template v-else>
              <div v-for="issue in issues" :key="issue.requirementId" class="mb-6">
                <v-timeline density="compact">
                  <v-timeline-item dot-color="warning">
                    <v-card color="warning" variant="tonal">
                      <v-card-title>{{ issue.requirementId }}</v-card-title>

                      <v-card-text>
                        <p class="mb-2">{{ issue.message }}</p>

                        <div class="text-body-2">
                          Missing:
                          <v-chip
                            v-for="c in issue.missingCourses"
                            :key="c"
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

          </v-card-text>
        </v-card>

      </v-col>
    </v-row>

    <!-- DEFAULT EMPTY STATE -->
    <v-alert v-else type="info" variant="tonal" class="mt-4">
      Select an advisee to load degree plan data.
    </v-alert>

  </div>
</template>

<script setup>
/* ------------------------------------------
   IMPORTS
------------------------------------------ */
import { ref, computed, watch, onMounted } from "vue"
import { useCurrentUser } from "@/composables/useCurrentUser"
import { useDegreePlanStore } from "@/stores/degreePlans"
import { fetchAdvisees } from "@/services/advisees"
import { NORMALIZED_ROLES } from "@/utils/auth"

/* ------------------------------------------
   STORE
------------------------------------------ */
const degreePlanStore = useDegreePlanStore()

/* ------------------------------------------
   STATE
------------------------------------------ */
const selectedAdviseeId = ref(null)
const advisees = ref([])
const adviseeListLoading = ref(false)

const showImportDialog = ref(false)
const pdfURL = ref("")
const seeding = ref(false)

const {
  role: userRole,
  advisee: currentAdvisee,
  loadUserContext,
  error: userContextError,
} = useCurrentUser()

const isStudent = computed(() => userRole.value === NORMALIZED_ROLES.STUDENT)

/* ------------------------------------------
   CONTEXT BINDINGS
------------------------------------------ */
const context = computed(() => degreePlanStore.context)
const latestValidation = computed(() => degreePlanStore.latestValidation || {})

const generalEd = computed(() => latestValidation.value.generalEducation || [])
const issues = computed(() => latestValidation.value.issues || [])

const majorPercent = computed(() => latestValidation.value.majorCompletionPercent ?? 0)
const minorPercent = computed(() => latestValidation.value.minorCompletionPercent ?? 0)
const concentrationPercent = computed(() => latestValidation.value.concentrationCompletionPercent ?? 0)

const llmNeeded = computed(() => latestValidation.value.llmCourseBreakdown?.neededCourses || [])
const llmTaken = computed(() => latestValidation.value.llmCourseBreakdown?.takenCourses || [])

/* ------------------------------------------
   FORMATTING
------------------------------------------ */
const formattedLastRun = computed(() => {
  const dt = latestValidation.value?.finishedAt || latestValidation.value?.createdAt
  if (!dt) return "n/a"
  return new Date(dt).toLocaleString()
})

const statusColor = computed(() => {
  switch (latestValidation.value?.status) {
    case "PASSED": return "success"
    case "FAILED": return "error"
    case "RUNNING": return "warning"
    default: return "primary"
  }
})

/* ------------------------------------------
   GENERAL ED PROGRESS
------------------------------------------ */
function generalEdProgress(group) {
  const req = Math.max(group.requiredSelections || 1, 1)
  const got = Math.min(group.satisfiedSelections || 0, req)
  return (got / req) * 100
}

/* ------------------------------------------
   FOCUS AREAS
------------------------------------------ */
const focusSections = computed(() => {
  const sections = []

  if (latestValidation.value.concentrations?.length) {
    sections.push({
      key: "CONCENTRATION",
      title: "Concentrations",
      completion: concentrationPercent.value,
      groups: latestValidation.value.concentrations
    })
  }

  if (latestValidation.value.minors?.length) {
    sections.push({
      key: "MINOR",
      title: "Minors",
      completion: minorPercent.value,
      groups: latestValidation.value.minors
    })
  }

  return sections
})

const hasFocusAreas = computed(() => focusSections.value.length > 0)

function concentrationProgress(area) {
  const req = Math.max(area.requiredHours || 1, 1)
  const got = area.completedHours || 0
  return (got / req) * 100
}

/* ------------------------------------------
   ADVISEE SELECT ITEMS
------------------------------------------ */
const adviseeSelectItems = computed(() =>
  advisees.value.map((a) => ({
    value: a.adviseeID,
    label: `${a.name} (#${a.adviseeID})`,
    subtitle: a.major,
  }))
)

/* ------------------------------------------
   LOAD ADVISEES (advisor mode)
------------------------------------------ */
async function loadAdvisees() {
  adviseeListLoading.value = true
  try {
    const data = await fetchAdvisees({ limit: 200 })
    advisees.value = data
  } finally {
    adviseeListLoading.value = false
  }
}

/* ------------------------------------------
   WATCHER — LOAD CONTEXT + SUMMARY
------------------------------------------ */
watch(selectedAdviseeId, async (id) => {
  if (!id) return

  await degreePlanStore.fetchContext(id)
  await degreePlanStore.loadSummary(id)
})

/* ------------------------------------------
   IMPORT PDF
------------------------------------------ */
async function importPdf() {
  if (!selectedAdviseeId.value) return
  await degreePlanStore.importDegreePlan(selectedAdviseeId.value, pdfURL.value)
  showImportDialog.value = false
  pdfURL.value = ""
}

/* ------------------------------------------
   INITIALIZATION
------------------------------------------ */
onMounted(async () => {
  await loadUserContext()

  if (isStudent.value) {
    selectedAdviseeId.value = currentAdvisee.value?.adviseeID
    await degreePlanStore.fetchContext(selectedAdviseeId.value)
    await degreePlanStore.loadSummary(selectedAdviseeId.value)
  } else {
    await loadAdvisees()
  }
})
</script>

<style scoped>
.degree-plan-page .requirement-option {
  background-color: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-theme-primary), 0.14);
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.degree-plan-page .requirement-option:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 26px rgba(0, 0, 0, 0.1);
}
</style>
