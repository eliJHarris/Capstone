<template>
  <div class="py-6">
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Student Directory</h2>
        <p class="text-body-2 text-medium-emphasis">
          Live advisee roster with filters and advisor assignments.
        </p>
      </div>
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        variant="text"
        :loading="loading"
        :disabled="loading"
        @click="loadAdvisees"
      />
    </div>

    <v-alert
      v-if="error"
      type="error"
      class="mb-4"
      closable
      @click:close="error = null"
    >
      {{ error }}
    </v-alert>

    <v-row dense>
      <v-col cols="12" md="4">
        <v-card rounded="xl" class="mb-4">
          <v-card-title>Filters</v-card-title>
          <v-card-text>
            <v-text-field
              v-model="filters.search"
              label="Search students"
              prepend-inner-icon="mdi-magnify"
              density="comfortable"
              clearable
              class="mb-3"
              @keydown.enter.prevent="applyFilters"
            />
            <v-select
              v-model="filters.classification"
              :items="classificationOptions"
              label="Classification"
              density="comfortable"
              variant="outlined"
              clearable
              class="mb-3"
            />
            <v-select
              v-model="filters.status"
              :items="statusOptions"
              label="Status"
              density="comfortable"
              variant="outlined"
              clearable
              class="mb-3"
            />
            <v-select
              v-model="filters.advisorId"
              :items="advisorFilterItems"
              :loading="advisorsLoading"
              item-title="title"
              item-value="value"
              label="Advisor"
              density="comfortable"
              variant="outlined"
              clearable
              class="mb-4"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <v-list-item-title>{{ item?.raw?.title || item?.title }}</v-list-item-title>
                  <v-list-item-subtitle>{{ item?.raw?.subtitle }}</v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-select>
            <v-btn
              color="primary"
              block
              class="mb-2"
              :loading="loading"
              @click="applyFilters"
            >
              Apply Filters
            </v-btn>
            <v-btn
              variant="tonal"
              block
              :disabled="loading"
              @click="resetFilters"
            >
              Reset
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card rounded="xl">
          <v-card-title>Roster Snapshot</v-card-title>
          <v-card-text>
            <div class="d-flex align-center mb-2">
              <div class="text-h4 font-weight-bold mr-2">{{ stats.total }}</div>
              <div class="text-caption text-medium-emphasis">students</div>
            </div>
            <div class="text-body-2 mb-1">
              Active:
              <strong>{{ stats.active }}</strong>
            </div>
            <div class="text-body-2 mb-1">
              Unassigned:
              <strong>{{ stats.unassigned }}</strong>
            </div>
            <div class="text-body-2 text-medium-emphasis">
              Avg GPA: {{ stats.avgGpa }}
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <v-card
          v-if="selectedAdvisee"
          rounded="xl"
          class="mb-4"
        >
          <v-card-title class="d-flex align-center">
            {{ selectedAdvisee.name }}
            <v-chip class="ml-2" size="small" :color="statusColor(selectedAdvisee)" variant="tonal">
              {{ selectedAdvisee.status || 'Unknown' }}
            </v-chip>
            <v-spacer />
            <span class="text-caption text-medium-emphasis">
              Updated {{ formatDate(selectedAdvisee.updatedAt) || 'n/a' }}
            </span>
          </v-card-title>

          <v-card-text>
            <v-row dense>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 text-medium-emphasis mb-1">Contact</div>
                <div class="text-body-2">{{ selectedAdvisee.email || 'No email on file' }}</div>
                <div class="text-body-2">
                  Major: {{ selectedAdvisee.major || '—' }}
                </div>
                <div class="text-body-2">
                  Classification: {{ selectedAdvisee.classification || '—' }}
                </div>
              </v-col>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 text-medium-emphasis mb-1">Progress</div>
                <div class="text-body-2">
                  Credits: {{ selectedAdvisee.creditsCompleted ?? '—' }}
                </div>
                <div class="text-body-2">
                  GPA: {{ formatGpa(selectedAdvisee.gpa) }}
                </div>
                <div class="text-body-2">
                  Degree Plan: {{ selectedAdvisee.degreePlan || 'Not linked' }}
                </div>
              </v-col>
            </v-row>

            <v-divider class="my-4" />

            <div class="d-flex flex-column flex-sm-row align-center" style="gap: 12px;">
              <div class="flex-grow-1">
                <div class="text-subtitle-2 text-medium-emphasis mb-1">Advisor</div>
                <v-select
                  v-model="advisorSelection"
                  :items="advisorSelectItems"
                  :loading="advisorsLoading || updatingAdvisor"
                  item-title="title"
                  item-value="value"
                  density="comfortable"
                  variant="outlined"
                  clearable
                />
              </div>
              <v-btn
                color="primary"
                :loading="updatingAdvisor"
                :disabled="!selectedAdvisee || updatingAdvisor"
                @click="handleAdvisorUpdate"
              >
                Update Assignment
              </v-btn>
            </div>
          </v-card-text>
        </v-card>

        <v-card rounded="xl">
          <v-card-title class="d-flex align-center">
            Students
            <v-chip size="small" class="ml-2" color="primary" variant="tonal">
              {{ advisees.length }}
            </v-chip>
            <v-spacer />
            <span class="text-caption text-medium-emphasis">
              Click a row to view details
            </span>
          </v-card-title>

          <v-data-table
            :headers="headers"
            :items="advisees"
            item-key="adviseeID"
            :loading="loading"
            :items-per-page="8"
            class="student-table"
            :item-class="rowClass"
            hover
            @click:row="handleRowClick"
          >
            <template #item.name="{ item }">
              <div class="d-flex flex-column">
                <div class="d-flex align-center">
                  <v-icon
                    v-if="isSelected(item.raw?.adviseeID || item.adviseeID)"
                    icon="mdi-check-circle"
                    color="primary"
                    size="16"
                    class="mr-2"
                  />
                  <span class="font-weight-medium">{{ item.raw?.name || item.name }}</span>
                </div>
                <span class="text-caption text-medium-emphasis">
                  {{ item.raw?.email || item.email || '—' }}
                </span>
              </div>
            </template>

            <template #item.status="{ item }">
              <v-chip
                size="small"
                :color="statusColor(item.raw || item)"
                variant="tonal"
              >
                {{ (item.raw?.status || item.status) || 'Unknown' }}
              </v-chip>
            </template>

            <template #item.gpa="{ item }">
              <div class="text-right">
                {{ formatGpa(item.raw?.gpa ?? item.gpa) }}
              </div>
            </template>

            <template #item.advisorName="{ item }">
              <span>{{ advisorDisplayName(item.raw || item) }}</span>
            </template>

            <template #no-data>
              <v-alert type="info" border="start" variant="tonal" class="ma-4">
                No students matched these filters.
              </v-alert>
            </template>
          </v-data-table>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      timeout="3000"
      location="bottom right"
    >
      {{ snackbar.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { fetchAdvisees, updateAdviseeAdvisor } from '@/services/advisees'
import { fetchAdvisors } from '@/services/advisors'
import { useStudentProfileStore } from '@/stores/studentProfile'

const UNASSIGNED_FILTER_VALUE = '__UNASSIGNED__'

const advisees = ref([])
const loading = ref(false)
const error = ref(null)
const advisors = ref([])
const advisorsLoading = ref(false)
const updatingAdvisor = ref(false)
const advisorSelection = ref(null)

const selectedAdviseeId = ref(null)
const studentProfileStore = useStudentProfileStore()

const snackbar = reactive({
  show: false,
  text: '',
  color: 'success',
})

const filters = reactive({
  search: '',
  classification: null,
  status: null,
  advisorId: null,
})

const headers = [
  { title: 'Name', key: 'name', sortable: false },
  { title: 'Major', key: 'major', sortable: false },
  { title: 'Classification', key: 'classification' },
  { title: 'GPA', key: 'gpa', align: 'end' },
  { title: 'Status', key: 'status' },
  { title: 'Advisor', key: 'advisorName', sortable: false },
]

const classificationOptions = ['Freshman', 'Sophomore', 'Junior', 'Senior'].map((value) => ({
  title: value,
  value,
}))

const statusOptions = ['Active', 'Inactive', 'Graduated', 'Suspended'].map((value) => ({
  title: value,
  value,
}))

const advisorSelectItems = computed(() => [
  { title: 'Unassigned', value: null, subtitle: 'Not linked to an advisor' },
  ...advisors.value.map((advisor) => ({
    title: advisor.name || `Advisor #${advisor.advisorID}`,
    subtitle: advisor.office || '',
    value: Number(advisor.advisorID),
  })),
])

const advisorFilterItems = computed(() => [
  { title: 'Unassigned', value: UNASSIGNED_FILTER_VALUE, subtitle: 'Not linked to an advisor' },
  ...advisors.value.map((advisor) => ({
    title: advisor.name || `Advisor #${advisor.advisorID}`,
    subtitle: advisor.office || '',
    value: Number(advisor.advisorID),
  })),
])

const advisorLookup = computed(() => {
  const map = new Map()
  advisors.value.forEach((advisor) => {
    map.set(Number(advisor.advisorID), advisor.name)
  })
  return map
})

const selectedAdvisee = computed(
  () => advisees.value.find((item) => item.adviseeID === selectedAdviseeId.value) || null
)

const stats = computed(() => {
  const total = advisees.value.length
  const active = advisees.value.filter((a) => a.status === 'Active').length
  const unassigned = advisees.value.filter((a) => !a.advisorID).length
  const gpas = advisees.value
    .map((a) => (a.gpa === null || a.gpa === undefined ? null : Number(a.gpa)))
    .filter((value) => value !== null && !Number.isNaN(value))
  const avgGpa = gpas.length
    ? (gpas.reduce((sum, value) => sum + value, 0) / gpas.length).toFixed(2)
    : '—'
  return { total, active, unassigned, avgGpa }
})

const statusColor = (item) => {
  const status = item?.status
  switch (status) {
    case 'Active':
      return 'success'
    case 'Graduated':
      return 'primary'
    case 'Suspended':
      return 'error'
    case 'Inactive':
      return 'grey'
    default:
      return 'secondary'
  }
}

const formatGpa = (value) => {
  if (value === null || value === undefined || value === '') return '—'
  const num = Number(value)
  return Number.isNaN(num) ? '—' : num.toFixed(2)
}

const formatDate = (value) => {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

const advisorDisplayName = (item) => {
  if (!item) return 'Unassigned'
  const advisorId = item.advisorID ?? item.advisorId
  if (item.advisorName) return item.advisorName
  if (advisorId && advisorLookup.value.get(Number(advisorId))) {
    return advisorLookup.value.get(Number(advisorId))
  }
  return advisorId ? `Advisor #${advisorId}` : 'Unassigned'
}

const showFeedback = (text, color = 'success') => {
  snackbar.text = text
  snackbar.color = color
  snackbar.show = true
}

const normalizeAdvisee = (item) => ({
  adviseeID: Number(item.adviseeID),
  userID: item.userID !== undefined && item.userID !== null ? Number(item.userID) : null,
  name: item.name,
  email: item.email,
  advisorID: item.advisorID !== null && item.advisorID !== undefined ? Number(item.advisorID) : null,
  advisorName: item.advisorName || null,
  major: item.major,
  degreePlan: item.degreePlan,
  classification: item.classification,
  gpa: item.gpa !== null && item.gpa !== undefined ? Number(item.gpa) : null,
  creditsCompleted:
    item.creditsCompleted !== null && item.creditsCompleted !== undefined
      ? Number(item.creditsCompleted)
      : null,
  status: item.status,
  updatedAt: item.updatedAt || item.lastUpdated || null,
})

const loadAdvisors = async () => {
  advisorsLoading.value = true
  try {
    advisors.value = await fetchAdvisors({ limit: 200 })
  } catch (err) {
    console.error(err)
    showFeedback(err.message || 'Failed to load advisors', 'error')
  } finally {
    advisorsLoading.value = false
  }
}

const loadAdvisees = async () => {
  loading.value = true
  error.value = null
  const isUnassignedAdvisorFilter = filters.advisorId === UNASSIGNED_FILTER_VALUE
  const advisorIdFilter = isUnassignedAdvisorFilter ? undefined : filters.advisorId ?? undefined
  try {
    const data = await fetchAdvisees({
      advisorId: advisorIdFilter,
      advisorIsNull: isUnassignedAdvisorFilter ? true : undefined,
      classification: filters.classification || undefined,
      status: filters.status || undefined,
      search: filters.search || undefined,
      limit: 400,
    })
    advisees.value = data.map(normalizeAdvisee)

    if (!advisees.value.length) {
      selectedAdviseeId.value = null
      advisorSelection.value = null
    } else if (!selectedAdviseeId.value || !advisees.value.find((a) => a.adviseeID === selectedAdviseeId.value)) {
      const firstId = advisees.value[0].adviseeID
      selectedAdviseeId.value = firstId
      advisorSelection.value = advisees.value[0].advisorID
    }
  } catch (err) {
    console.error(err)
    error.value = err.message || 'Failed to load students'
  } finally {
    loading.value = false
  }
}

const applyFilters = () => {
  loadAdvisees()
}

const resetFilters = () => {
  filters.search = ''
  filters.classification = null
  filters.status = null
  filters.advisorId = null
  applyFilters()
}

const handleRowClick = (_, row) => {
  const raw = row?.item?.raw ?? row?.item
  if (raw?.adviseeID) {
    selectAdvisee(Number(raw.adviseeID))
  }
}

const selectAdvisee = (id) => {
  selectedAdviseeId.value = id
  const current = advisees.value.find((item) => item.adviseeID === id)
  advisorSelection.value = current?.advisorID ?? null
}

const isSelected = (id) => Number(id) === selectedAdviseeId.value

const rowClass = (item) => {
  const raw = item?.raw ?? item
  return Number(raw?.adviseeID) === selectedAdviseeId.value ? 'selected-row' : ''
}

const handleAdvisorUpdate = async () => {
  if (!selectedAdvisee.value) return
  updatingAdvisor.value = true
  try {
    const advisorId = advisorSelection.value ?? null
    await updateAdviseeAdvisor(selectedAdvisee.value.adviseeID, advisorId)
    const idx = advisees.value.findIndex((a) => a.adviseeID === selectedAdvisee.value.adviseeID)
    if (idx !== -1) {
      advisees.value[idx] = {
        ...advisees.value[idx],
        advisorID: advisorId ? Number(advisorId) : null,
        advisorName: advisorDisplayName({
          advisorID: advisorId,
          advisorName: advisorLookup.value.get(Number(advisorId)),
        }),
      }
    }
    showFeedback('Advisor assignment updated')
  } catch (err) {
    console.error(err)
    showFeedback(err.message || 'Failed to update advisor', 'error')
  } finally {
    updatingAdvisor.value = false
  }
}

const syncProfileStore = (advisee) => {
  if (!advisee) return
  studentProfileStore.updateProfile({
    advisee_id: advisee.adviseeID,
    student_name: advisee.name,
    major: advisee.major,
    advisor_name: advisorDisplayName(advisee),
  })
}

watch(selectedAdvisee, (value) => {
  if (value) {
    advisorSelection.value = value.advisorID ?? null
    syncProfileStore(value)
  }
})

onMounted(() => {
  loadAdvisors()
  loadAdvisees()
})
</script>

<style scoped>
.student-table :deep(thead th) {
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.5px;
}

.student-table :deep(.selected-row) {
  background-color: rgba(0, 0, 0, 0.04) !important;
  transition: background-color 0.2s ease;
}
</style>
