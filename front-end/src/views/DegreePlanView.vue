<template>
  <div class="py-6 degree-plan-page">
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Degree Plan Validation</h2>
        <p class="text-body-2 text-medium-emphasis">
          Advisors can browse any student. Students only view their own degree plan.
        </p>
      </div>

      <v-spacer />
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
      v-if="degreePlanStore.error"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      @click:close="degreePlanStore.error = null"
    >
      {{ degreePlanStore.error }}
    </v-alert>

    <v-alert
      v-if="transcriptError"
      type="error"
      variant="tonal"
      class="mb-4"
      closable
      @click:close="transcriptError = null"
    >
      {{ transcriptError }}
    </v-alert>

    <div
      v-if="transcriptLoading"
      class="d-flex align-center mb-4 text-caption text-medium-emphasis"
    >
      <v-progress-circular indeterminate size="18" width="3" color="primary" class="mr-2" />
      Syncing transcript data…
    </div>

    <v-card rounded="xl" class="mb-4">
      <v-card-text>
        <div class="d-flex flex-column flex-md-row align-start" style="gap: 24px;">
          <div class="flex-grow-1" style="min-width: 260px;">
            <div class="text-subtitle-2 text-medium-emphasis mb-2">Select Advisee</div>

            <template v-if="isStudent">
              <v-alert
                density="compact"
                color="primary"
                variant="tonal"
              >
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

    <v-row dense v-if="context && latestValidation">
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

          </v-card-text>

          <v-divider />

          <v-list density="comfortable">
            <v-list-item>
              <v-list-item-title>Program</v-list-item-title>
              <v-list-item-subtitle>{{ context.major }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Catalog Year</v-list-item-title>
              <v-list-item-subtitle>{{ context.catalogYear || '—' }}</v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Credits Completed</v-list-item-title>
              <v-list-item-subtitle>
                {{ creditsCompletedLabel }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Total Credits Required</v-list-item-title>
              <v-list-item-subtitle>
                {{
                  totalCreditsRequired !== null && totalCreditsRequired !== undefined
                    ? `${totalCreditsRequired} hrs`
                    : '—'
                }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card rounded="xl" class="mb-4">
          <v-card-title class="d-flex align-center">
            Year-by-Year Degree Plan Breakdown
            <v-spacer />

            <v-chip size="small" color="primary" variant="tonal">
              {{ totalCompleted }} / {{ totalPlanned }} courses completed
            </v-chip>
          </v-card-title>

          <v-card-text>
            <v-tabs v-model="yearTab" grow density="compact" class="mb-6">
              <v-tab v-for="y in yearTabs" :key="y" :value="y">
                {{ y }}
              </v-tab>
            </v-tabs>
            <div class="mb-4">
              <v-progress-linear
                :model-value="yearProgress(yearTab)"
                :color="yearColor(yearTab)"
                height="12"
                rounded
              />
              <div class="text-caption text-medium-emphasis mt-1">
                {{ yearProgress(yearTab).toFixed(1) }}% complete
              </div>
            </div>
            <div class="d-flex align-center justify-space-between mb-3">
              <div class="text-subtitle-1 font-weight-medium">{{ formattedYearTitle }}</div>
              <v-chip size="small" color="grey-darken-1" variant="tonal">
                {{ activeYearHours }} hrs planned
              </v-chip>
            </div>

            <v-table
              v-if="activeYearCourses.length"
              class="degree-plan-table"
              density="comfortable"
            >
              <thead>
                <tr>
                  <th class="text-left">Course</th>
                  <th class="text-left">Details</th>
                  <th class="text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in activeYearCourses" :key="c.code">
                  <td>
                    <div class="font-weight-medium">
                      {{ c.code }}
                      <span class="text-body-2 font-weight-regular">— {{ c.title }}</span>
                    </div>
                  </td>
                  <td>
                    <div class="text-body-2">{{ c.credits || '—' }} hrs</div>
                    <div class="text-caption text-medium-emphasis">
                      {{ c.category || 'Requirement' }}
                    </div>
                  </td>
                  <td class="text-no-wrap">
                    <v-chip
                      :color="c.taken ? 'success' : 'warning'"
                      size="small"
                      variant="tonal"
                    >
                      {{ statusLabel(c) }}
                    </v-chip>
                    <div v-if="termLabel(c)" class="text-caption text-medium-emphasis">
                      {{ termLabel(c) }}
                    </div>
                  </td>
                </tr>
              </tbody>
            </v-table>

            <div v-else class="text-body-2 text-medium-emphasis">
              No courses assigned to {{ yearTab }} year.
            </div>

          </v-card-text>
        </v-card>
        <v-card rounded="xl">
          <v-card-title class="d-flex align-center">
            Remaining Courses
            <v-spacer />
            <v-tabs v-model="needTab" grow density="compact" class="ml-4">
              <v-tab v-for="tab in needTabs" :key="tab" :value="tab">
                {{ tab }}
              </v-tab>
            </v-tabs>
          </v-card-title>

          <v-divider />

          <v-card-text>
            <div v-if="neededCourses[needTab] && neededCourses[needTab].length">
              <v-list density="comfortable">
                <v-list-item
                  v-for="course in neededCourses[needTab]"
                  :key="course.code"
                >
                  <v-list-item-title>
                    <strong>{{ course.code }}</strong> — {{ course.title }}
                    <span class="text-medium-emphasis">
                      ({{ course.credits || '—' }} hrs)
                    </span>
                  </v-list-item-title>
                  <v-list-item-subtitle class="text-caption text-medium-emphasis">
                    {{ course.category }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
            <div v-else class="text-body-2 text-medium-emphasis">
              No outstanding courses in this category.
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert v-else type="info" variant="tonal" class="mt-4">
      Select an advisee to load degree plan data.
    </v-alert>
  </div>
</template>
<script setup>
import { ref, computed, watch, onMounted } from "vue"
import { useCurrentUser } from "@/composables/useCurrentUser"
import { useDegreePlanStore } from "@/stores/degreePlans"
import { fetchAdvisees } from "@/services/advisees"
import { fetchMyTranscript, fetchTranscriptByAdvisee } from "@/services/transcripts"
import { NORMALIZED_ROLES } from "@/utils/auth"

const degreePlanStore = useDegreePlanStore()
const {
  role: userRole,
  advisee: currentAdvisee,
  loadUserContext,
  loading: userContextLoading,
  error: userContextError,
} = useCurrentUser()

const isStudent = computed(() => userRole.value === NORMALIZED_ROLES.STUDENT)


const selectedAdviseeId = ref(null)
const advisees = ref([])
const adviseeListLoading = ref(false)
const transcriptError = ref(null)
const transcriptLoading = ref(false)

const showImportDialog = ref(false)
const pdfURL = ref("")
const seeding = ref(false)

const yearTab = ref("All")
const needTab = ref("Major")

const context = computed(() => degreePlanStore.context)
const requirementSet = computed(() => degreePlanStore.requirementSet)
const latestValidation = computed(() => degreePlanStore.latestValidation || {})
const hasConcentration = computed(() => (latestValidation.value.concentrationRequirementCount || 0) > 0)
const hasMinor = computed(() => (latestValidation.value.minorRequirementCount || 0) > 0)
const activeConcentrationIds = computed(() => {
  const ids = new Set()
  ;(latestValidation.value.concentrations || []).forEach((c) => {
    const key = (c.groupId || c.title || "").toString().toLowerCase()
    if (key) ids.add(key)
  })
  return ids
})


const statusColor = computed(() => {
  switch (latestValidation.value?.status) {
    case "PASSED": return "success"
    case "FAILED": return "error"
    case "RUNNING": return "warning"
    default: return "primary"
  }
})

const totalCreditsRequired = computed(() => {
  const fromValidation = latestValidation.value?.totalCredits
  if (fromValidation !== undefined && fromValidation !== null) {
    const parsed = Number(fromValidation)
    if (Number.isFinite(parsed)) return parsed
  }
  const fromRequirement = requirementSet.value?.totalCredits
  const parsedRequirement = Number(fromRequirement)
  return Number.isFinite(parsedRequirement) ? parsedRequirement : null
})


function inferYearBucket(code = "", category = "") {
  const categoryText = (category || "").toLowerCase()
  if (categoryText.includes("elective")) return "Other"
  if (!code) return "Other"
  const digits = code.replace(/\s+/g, "").match(/\d+/)
  if (!digits || !digits[0]) return "Other"
  const first = digits[0][0]
  if (first === "1") return "Freshman"
  if (first === "2") return "Sophomore"
  if (first === "3") return "Junior"
  if (first === "4" || first === "5") return "Senior"
  return "Other"
}

function normalizeYearLabel(value = "") {
  const label = value.toString().toLowerCase()
  if (label.includes("fresh")) return "Freshman"
  if (label.includes("soph")) return "Sophomore"
  if (label.includes("junior")) return "Junior"
  if (label.includes("senior")) return "Senior"
  return ""
}

function statusLabel(course = {}) {
  if (course.taken) return "Taken"
  const status = (course.status || "").toString().toUpperCase()
  if (status === "IN_PROGRESS") return "In Progress"
  if (status === "COMPLETED") return "Taken"
  return "Not Taken"
}

function termLabel(course = {}) {
  return course.term || ""
}


function normalizeCourseCode(entry) {
  if (!entry) return ""
  const raw = typeof entry === "string" ? entry : entry.code
  return (raw || "").replace(/\s+/g, "").toUpperCase()
}

function normalizeTranscriptStatus(status = "", grade = "") {
  const normalized = status.toString().toUpperCase()
  const normalizedGrade = grade.toString().toUpperCase()
  if (normalized.includes("PROGRESS") || normalized === "IP" || normalizedGrade === "IP") {
    return "IN_PROGRESS"
  }
  if (normalized === "COMPLETED") return "COMPLETED"
  if (normalized === "DROPPED" || normalized === "WITHDRAWN") return normalized
  return normalized || "COMPLETED"
}

const completedCodes = computed(() => {
  const all = [
    ...(degreePlanStore.completedCourses || []),
    ...(latestValidation.value.completedCourseDetails || []),
    ...(latestValidation.value.completedCourses || []),
    ...(latestValidation.value.completed || []),
    ...(latestValidation.value.takenCourses || []),
    ...(latestValidation.value.llmCourseBreakdown?.takenCourses || [])
  ]

  const completed = new Set()

  const isCompletedEntry = (entry) => {
    if (!entry) return false
    if (typeof entry === "string") return true
    const status = (entry.status || "").toString().toUpperCase()
    const grade = (entry.grade || "").toString().toUpperCase()
    if (status && ["IN_PROGRESS", "PLANNED", "WITHDRAWN", "DROPPED"].includes(status)) return false
    if (grade && (grade === "IP" || grade === "IN PROGRESS")) return false
    return true
  }

  all.forEach((entry) => {
    if (!isCompletedEntry(entry)) return
    const code = normalizeCourseCode(entry)
    if (code) completed.add(code)
  })

  return completed
})

const completedCourseDetailMap = computed(() => {
  const detailMap = new Map()
  const sources = [
    ...(degreePlanStore.completedCourses || []),
    ...(latestValidation.value.completedCourseDetails || []),
    ...(latestValidation.value.completedCourses || []),
  ]

  sources.forEach((entry) => {
    if (!entry || typeof entry === "string") return
    const code = normalizeCourseCode(entry.code)
    if (!code) return
    detailMap.set(code, entry)
  })

  return detailMap
})

const creditsCompleted = computed(() => {
  const explicit = context.value?.creditsCompleted
  if (explicit !== undefined && explicit !== null) {
    const parsed = Number(explicit)
    if (Number.isFinite(parsed)) return parsed
  }

  const seen = new Set()
  const sources = [
    ...(degreePlanStore.completedCourses || []),
    ...(latestValidation.value.completedCourseDetails || []),
    ...(latestValidation.value.completedCourses || []),
  ]

  let total = 0
  sources.forEach((entry) => {
    if (!entry || typeof entry === "string") return
    const code = normalizeCourseCode(entry.code)
    if (!code || seen.has(code)) return
    seen.add(code)
    const credits = Number(entry.credits)
    if (Number.isFinite(credits)) {
      total += credits
    }
  })

  return total
})

const creditsCompletedLabel = computed(() => {
  const total = creditsCompleted.value
  return Number.isFinite(total) ? `${total} hrs` : "—"
})

function extractPlannedCourses() {
  const itemsMap = new Map()

  const groups = requirementSet.value?.requirementGroups || requirementSet.value?.requirementData || []

  const labelForGroup = (group = {}) => {
    const type = (group.type || "").toLowerCase()
    const baseTitle = group.title || group.id || "Requirement"

    if (type === "concentration") return `Concentration — ${baseTitle}`
    if (type === "minor") return `Minor — ${baseTitle}`
    if (
      type === "category" ||
      type === "choose_one" ||
      type === "paired_group" ||
      type === "credit_minimum" ||
      (group.category || "").toLowerCase() === "general_education"
    ) {
      return `General Education — ${baseTitle}`
    }
    return baseTitle
  }

  const normalizeCourseEntry = (course) => {
    const code = normalizeCourseCode(course)
    if (!code) return null
    const title =
      typeof course === "string"
        ? code
        : course.title || course.display || code
    const credits = Number(
      (typeof course === "string" ? null : course.credits) ?? 3
    )
    const rawYear = typeof course === "string" ? null : (course.yearBucket || course.year || course.termBucket)
    const yearBucket = normalizeYearLabel(rawYear || "")
    return { code, title, credits: Number.isFinite(credits) ? credits : 3, yearBucket }
  }

  if (groups.length) {
    groups.forEach((group) => {
      const type = (group.type || "").toLowerCase()
      if (type === "concentration" && activeConcentrationIds.value.size) {
        const key = (group.id || group.title || "").toString().toLowerCase()
        if (!activeConcentrationIds.value.has(key)) {
          return
        }
      }

      const categoryLabel = labelForGroup(group)
      const courseEntries = (group.courses && group.courses.length)
        ? group.courses
        : [...(group.requiredCourses || []), ...(group.chooseCourses || [])]

      courseEntries.forEach((course) => {
        const normalized = normalizeCourseEntry(course)
        if (!normalized) return
        const courseYear = normalized.yearBucket || normalizeYearLabel(group.year || group.yearBucket || group.termBucket)
        const key = normalized.code
        if (!itemsMap.has(key)) {
          itemsMap.set(key, { ...normalized, category: categoryLabel, yearBucket: courseYear })
        }
      })
    })
    return Array.from(itemsMap.values())
  }

  const raw = latestValidation.value

  const pushGroup = (group, categoryLabel) => {
    if (!group?.courses) return
    group.courses.forEach((course) => {
      const normalized = normalizeCourseEntry(course)
      if (!normalized) return
      const courseYear = normalized.yearBucket || normalizeYearLabel(group.year || group.yearBucket || group.termBucket)
      const key = normalized.code
      if (!itemsMap.has(key)) {
        itemsMap.set(key, { ...normalized, category: categoryLabel, yearBucket: courseYear })
      }
    })
  }

  ;(raw.majorRequirements || []).forEach((g) => pushGroup(g, "Major Requirement"))
  ;(raw.minorRequirements || []).forEach((g) => pushGroup(g, "Minor Requirement"))
  ;(raw.generalEducation || []).forEach((g) => pushGroup(g, `General Education — ${g.title}`))
  ;(raw.concentrations || []).forEach((g) => pushGroup(g, `Concentration — ${g.title}`))

  return Array.from(itemsMap.values())
}

const plannedCourses = computed(() => extractPlannedCourses())

function bucketPlannedCourses() {
  const buckets = {
    All: [],
    Freshman: [],
    Sophomore: [],
    Junior: [],
    Senior: [],
    Other: [],
  }

  plannedCourses.value.forEach((c) => {
    const explicitYear = normalizeYearLabel(c.yearBucket || "")
    const year = explicitYear || inferYearBucket(c.code, c.category)
    const entry = {
      ...c,
      taken: completedCodes.value.has(c.code),
      status: completedCourseDetailMap.value.get(c.code)?.status,
      term: completedCourseDetailMap.value.get(c.code)?.term,
    }
    buckets[year].push(entry)
    buckets["All"].push(entry)
  })

  Object.keys(buckets).forEach((key) => {
    buckets[key] = sortCourses(buckets[key])
  })

  return buckets
}

const degreePlanYearBuckets = computed(() => bucketPlannedCourses())

const yearTabs = ["All", "Freshman", "Sophomore", "Junior", "Senior", "Other"]

function sortCourses(list = []) {
  return [...list].sort((a, b) => {
    const codeA = a.code || ""
    const codeB = b.code || ""
    const numA = parseInt(codeA.replace(/\D/g, ""), 10) || 0
    const numB = parseInt(codeB.replace(/\D/g, ""), 10) || 0
    if (numA !== numB) return numA - numB
    return codeA.localeCompare(codeB)
  })
}

const activeYearCourses = computed(() => degreePlanYearBuckets.value[yearTab.value] || [])

const activeYearHours = computed(() =>
  activeYearCourses.value.reduce((sum, course) => {
    const credits = Number(course.credits || 0)
    return sum + (Number.isFinite(credits) ? credits : 0)
  }, 0)
)

const formattedYearTitle = computed(() => {
  if (yearTab.value === "All") return "All Courses"
  return `${yearTab.value} Year Plan`
})

const needTabs = computed(() => {
  const tabs = ["Major"]
  if (hasConcentration.value) tabs.push("Concentration")
  if (hasMinor.value) tabs.push("Minor")
  return tabs
})

watch(needTabs, (tabs) => {
  if (!tabs.includes(needTab.value)) {
    needTab.value = tabs[0]
  }
})

function normalizeNeededCourse(detail, categoryLabel) {
  const code = normalizeCourseCode(detail?.code || detail)
  if (!code) return null
  return {
    code,
    title: detail?.title || detail?.display || code,
    credits: detail?.credits,
    category: categoryLabel,
  }
}

const neededCourses = computed(() => {
  const buckets = { Major: [], Concentration: [], Minor: [] }
  const dedupe = { Major: new Set(), Concentration: new Set(), Minor: new Set() }

  ;(latestValidation.value.majorRequirements || []).forEach((group) => {
    const label = `Major — ${group.title || group.groupId || "Requirement"}`
    const list = group.missingCourseDetails?.length
      ? group.missingCourseDetails
      : (group.missingCourses || [])
    list.forEach((c) => {
      const normalized = normalizeNeededCourse(c, label)
      if (!normalized) return
      if (!dedupe.Major.has(normalized.code)) {
        dedupe.Major.add(normalized.code)
        buckets.Major.push(normalized)
      }
    })
  })

  ;(latestValidation.value.concentrations || []).forEach((group) => {
    const key = (group.groupId || group.title || "").toString().toLowerCase()
    if (activeConcentrationIds.value.size && !activeConcentrationIds.value.has(key)) return
    const label = `Concentration — ${group.title || "Option"}`
    const list = group.missingCourseDetails?.length
      ? group.missingCourseDetails
      : (group.missingCourses || [])
    list.forEach((c) => {
      const normalized = normalizeNeededCourse(c, label)
      if (!normalized) return
      if (!dedupe.Concentration.has(normalized.code)) {
        dedupe.Concentration.add(normalized.code)
        buckets.Concentration.push(normalized)
      }
    })
  })

  ;(latestValidation.value.minorRequirements || []).forEach((group) => {
    const label = `Minor — ${group.title || group.groupId || "Requirement"}`
    const list = group.missingCourseDetails?.length
      ? group.missingCourseDetails
      : (group.missingCourses || [])
    list.forEach((c) => {
      const normalized = normalizeNeededCourse(c, label)
      if (!normalized) return
      if (!dedupe.Minor.has(normalized.code)) {
        dedupe.Minor.add(normalized.code)
        buckets.Minor.push(normalized)
      }
    })
  })

  return buckets
})


function mergeCompletedCourses(existing = [], additions = []) {
  const map = new Map()
  const push = (entry = {}) => {
    const code = normalizeCourseCode(entry.code)
    if (!code) return
    const key = `${code}-${entry.term || ""}-${entry.grade || ""}-${entry.status || ""}`
    map.set(key, { ...entry, code })
  }
  existing.forEach(push)
  additions.forEach(push)
  return Array.from(map.values())
}

function transcriptCoursesToCompleted(data) {
  const items = []
  data?.terms?.forEach((term) => {
    term?.courses?.forEach((course) => {
      const code = normalizeCourseCode(course.courseCode)
      if (!code) return
      items.push({
        code,
        title: course.courseTitle || code,
        credits: course.credits,
        term: course.term || term.term,
        status: normalizeTranscriptStatus(course.status, course.grade),
        grade: course.grade,
      })
    })
  })
  return items
}

function yearProgress(year) {
  const list = degreePlanYearBuckets.value[year] || []
  if (list.length === 0) return 0
  const taken = list.filter((c) => c.taken).length
  return (taken / list.length) * 100
}

function yearColor(year) {
  switch (year) {
    case "Freshman": return "primary"
    case "Sophomore": return "secondary"
    case "Junior": return "info"
    case "Senior": return "success"
    case "Other": return "warning"
    default: return "primary"
  }
}

const allPlannedCourses = computed(() => degreePlanYearBuckets.value.All || [])

const totalCompleted = computed(() =>
  allPlannedCourses.value.filter((c) => c.taken).length
)

const totalPlanned = computed(() => allPlannedCourses.value.length)


const adviseeSelectItems = computed(() =>
  advisees.value.map((a) => ({
    value: a.adviseeID,
    label: `${a.name} (#${a.adviseeID})`,
    subtitle: a.major,
  }))
)


async function loadAdvisees() {
  adviseeListLoading.value = true
  try {
    const data = await fetchAdvisees({ limit: 200 })
    advisees.value = data
  } finally {
    adviseeListLoading.value = false
  }
}

watch(selectedAdviseeId, async (id) => {
  if (!id) return

  await loadDegreePlanData(id)
})


async function importPdf() {
  if (!selectedAdviseeId.value) return
  await degreePlanStore.importDegreePlan(selectedAdviseeId.value, pdfURL.value)
  showImportDialog.value = false
  pdfURL.value = ""
}

async function loadTranscriptData(adviseeId) {
  transcriptLoading.value = true
  transcriptError.value = null
  try {
    let data = null
    if (isStudent.value) {
      data = await fetchMyTranscript()
      selectedAdviseeId.value = data?.adviseeID || selectedAdviseeId.value
    } else if (adviseeId) {
      data = await fetchTranscriptByAdvisee(adviseeId)
    }
    const mapped = transcriptCoursesToCompleted(data)
    if (mapped.length) {
      degreePlanStore.completedCourses = mergeCompletedCourses(
        degreePlanStore.completedCourses,
        mapped
      )
    }
  } catch (err) {
    transcriptError.value = err?.message || "Failed to load transcript data"
  } finally {
    transcriptLoading.value = false
  }
}

async function loadDegreePlanData(adviseeId) {
  if (!adviseeId) return
  const allowBootstrap = false
  try {
    await degreePlanStore.fetchContext(adviseeId, { allowBootstrap })
    await loadTranscriptData(adviseeId)
    await degreePlanStore.loadSummary(adviseeId, { allowBootstrap })
  } catch (err) {
    // Errors are surfaced via degreePlanStore.error or transcriptError; prevent unhandled rejections
    if (!degreePlanStore.error) {
      degreePlanStore.error = err?.message || "Failed to load degree plan data"
    }
  }
}

onMounted(async () => {
  await loadUserContext()

  if (isStudent.value) {
    selectedAdviseeId.value = currentAdvisee.value?.adviseeID
    await loadDegreePlanData(selectedAdviseeId.value)
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


.year-header {
  font-weight: 600;
  margin-bottom: 8px;
  font-size: 1.1rem;
}

.year-section {
  background-color: rgba(var(--v-theme-surface), 1);
  border-radius: 16px;
  padding: 16px;
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
}

.course-entry {
  display: flex;
  flex-direction: column;
  padding: 8px 0;
  border-bottom: 1px solid rgba(var(--v-theme-on-background), 0.06);
}

.course-entry:last-child {
  border-bottom: none;
}

.course-title-line {
  font-size: 0.95rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.course-code {
  font-weight: 600;
  margin-right: 6px;
}

.course-hours {
  color: rgba(var(--v-theme-on-surface), 0.7);
  margin-left: 4px;
}

.course-category {
  font-size: 0.78rem;
  color: rgba(var(--v-theme-on-surface), 0.6);
  margin-top: 2px;
}

.degree-plan-table th {
  font-weight: 600;
  font-size: 0.85rem;
  text-transform: uppercase;
  color: rgba(var(--v-theme-on-surface), 0.7);
}

.degree-plan-table td {
  vertical-align: middle;
}

.degree-plan-table .v-chip {
  font-weight: 600;
}

.taken-chip {
  margin-left: 12px;
  min-width: 80px;
  text-align: center;
}

@media (max-width: 600px) {
  .course-title-line {
    flex-direction: column;
    align-items: flex-start;
  }

  .taken-chip {
    margin-top: 6px;
    margin-left: 0;
  }
}


.v-tabs {
  background-color: transparent !important;
}

.year-progress-container {
  margin-bottom: 12px;
}

.year-progress {
  height: 10px;
  border-radius: 6px;
}

.text-caption {
  opacity: 0.8;
}

</style>
