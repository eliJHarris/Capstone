<template>
  <div class="py-6">
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Degree Plan Validation</h2>
        <p class="text-body-2 text-medium-emphasis">
          Track validation runs for {{ profile.student_name }} ({{ profile.major }})
        </p>
      </div>
      <v-spacer />
      <v-btn
        color="primary"
        class="mr-3"
        :loading="seeding"
        variant="tonal"
        @click="seedDegreePlan"
      >
        Load Sample Plan
      </v-btn>
      <v-btn
        color="primary"
        :loading="degreePlanStore.validationLoading"
        :disabled="!degreePlanStore.context || degreePlanStore.validationLoading"
        @click="handleManualValidation"
      >
        Validate Plan
      </v-btn>
    </div>

    <v-alert
      v-if="degreePlanStore.error"
      type="error"
      class="mb-4"
      closable
      @click:close="degreePlanStore.error = null"
    >
      {{ degreePlanStore.error }}
    </v-alert>

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
              <span :class="`text-${statusColor}`">{{ degreePlanStore.validationStatus }}</span>
            </div>
            <div class="text-caption text-medium-emphasis">
              Last run: {{ lastValidationRun || 'n/a' }}
            </div>
          </v-card-text>
          <v-divider />
          <v-list density="comfortable">
            <v-list-item>
              <v-list-item-title>Program</v-list-item-title>
              <v-list-item-subtitle>{{ requirementInfo?.programName || 'Not linked' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Catalog Year</v-list-item-title>
              <v-list-item-subtitle>{{ requirementInfo?.catalogYear || 'Unknown' }}</v-list-item-subtitle>
            </v-list-item>
            <v-list-item>
              <v-list-item-title>Total Credits</v-list-item-title>
              <v-list-item-subtitle>{{ requirementInfo?.totalCredits || '—' }}</v-list-item-subtitle>
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
                No requirement set linked to this advisee yet. Use “Load Sample Plan” or ingest a plan
                from the scraper pipeline.
              </v-alert>
              <v-alert
                v-else-if="!issues.length"
                type="success"
                variant="tonal"
              >
                All tracked requirements are satisfied.
              </v-alert>
              <v-timeline
                v-else
                density="compact"
              >
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
import { computed, onMounted, ref } from 'vue'
import { useStudentProfileStore } from '@/stores/studentProfile'
import { useDegreePlanStore } from '@/stores/degreePlans'
import { saveRequirementSet } from '@/services/degreePlans'

const studentStore = useStudentProfileStore()
const degreePlanStore = useDegreePlanStore()
const seeding = ref(false)

const profile = computed(() => studentStore.studentProfile)
const adviseeId = computed(() => profile.value.advisee_id)

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
    case 'PASSED':
      return 'success'
    case 'FAILED':
      return 'error'
    case 'RUNNING':
      return 'warning'
    default:
      return 'primary'
  }
})

const requirementInfo = computed(() => degreePlanStore.requirementSet)
const issues = computed(() => degreePlanStore.latestValidation?.issues || [])

async function loadSummary() {
  if (!adviseeId.value) return
  await degreePlanStore.loadSummary(adviseeId.value)
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

onMounted(() => {
  loadSummary()
})
</script>
