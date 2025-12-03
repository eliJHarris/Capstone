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

      <!-- VALIDATE -->
      <v-btn
        color="primary"
        :loading="degreePlanStore.validationLoading"
        :disabled="!degreePlanStore.context || degreePlanStore.validationLoading"
        @click="handleManualValidation"
      >
        Validate Plan
      </v-btn>
    </div>

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
                <v-list-item title="No advisees found" subtitle="Adjust filters or try again." />
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
            <div class="text-h5 font-weight-medium mb-1">
              {{ selectedAdvisee.name }}
            </div>
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
            label="Enter PDF or starting URL"
            placeholder="https://adviseme.uafs.edu/..."
            clearable
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
    <v-alert
      v-if="userContextError"
      type="error"
      class="mb-4"
      variant="tonal"
    >
      {{ userContextError }}
    </v-alert>

    <v-alert
      v-if="isStudent"
      type="info"
      class="mb-4"
      variant="tonal"
    >
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

    <!-- REST OF PAGE -->
    <v-row dense>
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
                {{ requirementInfo?.totalCredits || '—' }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card rounded="xl">
          <v-card-title class="d-flex align-center">
            Outstanding Requirements

            <v-chip
              v-if="issues.length"
              class="ml-2"
              color="warning"
              size="small"
            >
              {{ issues.length }} issue{{ issues.length === 1 ? '' : 's' }}
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

              <v-timeline v-else density="compact">
                <v-timeline-item
                  v-for="issue in issues"
                  :key="issue.requirementId || issue.message"
                  :color="statusColor"
                  dot-color="warning"
                >
                  <v-card variant="tonal" color="warning">
                    <v-card-title class="text-subtitle-1">
                      {{ issue.requirementId || 'Requirement' }}
                    </v-card-title>

                    <v-card-text>
                      <p class="mb-2">{{ issue.message }}</p>

                      <div class="text-body-2">
                        Missing:
                        <v-chip
                          v-for="course in issue.missingCourses"
                          :key="course"
                          size="small"
                          class="ma-1"
                        >
                          {{ course }}
                        </v-chip>
                      </div>
                    </v-card-text>
                  </v-card>
                </v-timeline-item>
              </v-timeline>
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

const studentStore = useStudentProfileStore()
const degreePlanStore = useDegreePlanStore()
const {
  role: userRole,
  advisee: currentAdvisee,
  loadUserContext,
  loading: userContextLoading,
  error: userContextError,
} = useCurrentUser()

const isStudent = computed(() => userRole.value === NORMALIZED_ROLES.STUDENT)

const seeding = ref(false)
const showImportDialog = ref(false)
const pdfURL = ref("")

const advisees = ref([])
const selectedAdviseeId = ref(null)
const adviseeListLoading = ref(false)
const adviseeListError = ref(null)

const FALLBACK_ADVISEES = [
  { adviseeID: 1, name: 'Jordan Casey', email: 'jcasey@college.edu', major: 'B.S. Computer Science', classification: 'Senior', status: 'Active' },
  { adviseeID: 2, name: 'Ariel Summers', email: 'asummers@college.edu', major: 'B.S. Mathematics', classification: 'Junior', status: 'Active' },
  { adviseeID: 3, name: 'Priya Patel', email: 'ppatel@college.edu', major: 'B.S. Information Systems', classification: 'Senior', status: 'Active' },
]

const profile = computed(() => studentStore.studentProfile)
const studentAdviseeId = computed(() =>
  currentAdvisee.value?.adviseeID ? Number(currentAdvisee.value.adviseeID) : profile.value?.advisee_id
)
const adviseeId = computed(() => selectedAdviseeId.value || studentAdviseeId.value || profile.value?.advisee_id)
const selectedAdvisee = computed(() => advisees.value.find((item) => item.adviseeID === selectedAdviseeId.value) || null)
const currentAdviseeName = computed(() => selectedAdvisee.value?.name || profile.value?.student_name || 'Advisee')
const currentAdviseeMajor = computed(() => selectedAdvisee.value?.major || profile.value?.major || 'Major TBD')
const adviseeSelectItems = computed(() =>
  advisees.value.map((item) => ({
    value: item.adviseeID,
    label: `${item.name} (#${item.adviseeID})`,
    subtitle: item.email || item.major,
  }))
)

function formatDate(value) {
  if (!value) return null
  return new Date(value).toLocaleString()
}

const lastValidationRun = computed(() => {
  const validation = degreePlanStore.latestValidation
  if (!validation) return null
  return formatDate(validation.finishedAt || validation.createdAt)
})

const statusColor = computed(() => {
  switch (degreePlanStore.validationStatus) {
    case 'PASSED': return 'success'
    case 'FAILED': return 'error'
    case 'RUNNING': return 'warning'
    default: return 'primary'
  }
})

const requirementInfo = computed(() => degreePlanStore.requirementSet)
const issues = computed(() => degreePlanStore.latestValidation?.issues || [])

async function importPdfUrl() {
  if (!adviseeId.value) return
  try {
    await degreePlanStore.importDegreePlan(adviseeId.value, pdfURL.value)
    showImportDialog.value = false
    pdfURL.value = ""
  } catch (err) {
    console.error(err)
  }
}

async function loadSummary() {
  if (!adviseeId.value) return
  await degreePlanStore.loadSummary(adviseeId.value)
}

async function loadAdviseeDirectory() {
  adviseeListLoading.value = true
  adviseeListError.value = null
  try {
    if (isStudent.value) {
      if (currentAdvisee.value?.adviseeID) {
        advisees.value = [
          {
            adviseeID: Number(currentAdvisee.value.adviseeID),
            name: currentAdvisee.value.name,
            email: currentAdvisee.value.email,
            major: currentAdvisee.value.major,
            classification: currentAdvisee.value.classification,
            status: currentAdvisee.value.status,
          },
        ]
      } else {
        adviseeListError.value = 'No advisee profile found for this account.'
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
      }))
    }
  } catch (error) {
    console.error(error)
    adviseeListError.value = error.message || 'Failed to load advisees'
    advisees.value = FALLBACK_ADVISEES
  } finally {
    adviseeListLoading.value = false
    const initial = adviseeId.value || advisees.value[0]?.adviseeID || null
    if (initial && selectedAdviseeId.value !== initial) {
      selectedAdviseeId.value = Number(initial)
    }
  }
}

async function handleManualValidation() {
  if (!adviseeId.value) return
  await degreePlanStore.triggerValidation(adviseeId.value)
}

const sampleRequirementTemplate = computed(() => ({
  programCode: profile.value.program_code || 'BS-CS',
  catalogYear: profile.value.catalog_year || 'CAT2024',
  programName: profile.value.major,
  totalCredits: 120,
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
  if (!adviseeId.value || seeding.value) return
  seeding.value = true
  try {
    const requirement = await saveRequirementSet(sampleRequirementTemplate.value)
    await degreePlanStore.syncContext(
      adviseeId.value,
      {
        requirementSetID: requirement.requirementSetID,
        completedCourses: sampleCompletedCourses,
        notes: 'Sample data loaded from UI seeding utility.',
      },
      { autoValidate: true }
    )
  } catch (error) {
    console.error(error)
  } finally {
    seeding.value = false
  }
}
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
  const selected = advisees.value.find((item) => item.adviseeID === newId)
  if (selected) {
    studentStore.updateProfile({
      advisee_id: selected.adviseeID,
      student_name: selected.name,
      major: selected.major || profile.value.major,
    })
  } else {
    studentStore.updateProfile({ advisee_id: newId })
  }
  await loadSummary()
})

onMounted(async () => {
  try {
    await loadUserContext()
  } catch (error) {
    console.error('Failed to load user context for degree plan view', error)
  }
  await loadAdviseeDirectory()
})
</script>
