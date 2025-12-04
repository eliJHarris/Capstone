<template>
  <div class="py-6">
    <div class="d-flex align-center mb-4">
      <div>
        <h2 class="text-h4 mb-1">Schedules & Appointments</h2>
        <p class="text-body-2 text-medium-emphasis">
          Connects directly to the FastAPI schedules endpoints for live data.
        </p>
      </div>
      <v-spacer />
      <v-btn
        icon="mdi-refresh"
        variant="text"
        :loading="loadingList"
        :disabled="loadingList"
        @click="refreshList"
      />
    </div>

    <v-alert
      v-if="scheduleError"
      type="error"
      class="mb-4"
      closable
      @click:close="clearError"
    >
      {{ scheduleError }}
    </v-alert>

    <v-alert
      v-if="userContextErrorMessage"
      type="error"
      class="mb-4"
      closable
    >
      {{ userContextErrorMessage }}
    </v-alert>

    <v-alert
      v-if="isStudent"
      type="info"
      variant="tonal"
      class="mb-4"
    >
      You are viewing schedules for your account only.
    </v-alert>

    <v-row dense>
      <v-col cols="12" md="4">
        <v-card rounded="xl" variant="flat" class="mb-4">
          <v-card-title>Filter schedules</v-card-title>
          <v-card-text>
              <v-form @submit.prevent="applyFilters">
              <v-autocomplete
                v-model="filterAdvisee"
                v-model:search="filterAdviseeSearch"
              :items="adviseeOptions"
              :loading="adviseeLoading"
              :disabled="isStudent || userContextLoading"
              item-title="title"
              item-value="value"
              label="Advisee"
              density="comfortable"
              variant="outlined"
              class="mb-3"
              return-object
              :clearable="!isStudent"
              @update:search="handleFilterAdviseeSearch"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props">
                    <v-list-item-title>{{ item?.raw?.name || item?.raw?.title }}</v-list-item-title>
                    <v-list-item-subtitle>{{ item?.raw?.email }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-autocomplete>
              <v-autocomplete
                v-model="filterTerm"
                v-model:search="filterTermSearch"
                :items="termOptions"
                :loading="termLoading"
                item-title="title"
                item-value="value"
                label="Term"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                return-object
                clearable
                @update:search="handleFilterTermSearch"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props">
                    <v-list-item-title>{{ item?.raw?.code || item?.raw?.title }}</v-list-item-title>
                    <v-list-item-subtitle>{{ formatTermRange(item?.raw) }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-autocomplete>
              <v-select
                v-model="filters.status"
                :items="statusOptions"
                label="Status"
                density="comfortable"
                variant="outlined"
                clearable
                class="mb-6"
              />
              <v-btn
                type="submit"
                color="primary"
                block
                class="mb-2"
                :loading="loadingList"
              >
                Apply Filters
              </v-btn>
              <v-btn
                type="button"
                variant="tonal"
                block
                :disabled="loadingList"
                @click="resetFilters"
              >
                Reset
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>

        <v-card rounded="xl" variant="flat">
          <v-card-title>Create schedule</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="handleCreate">
              <v-autocomplete
                v-model="createForm.advisee"
                v-model:search="adviseeSearch"
                :items="adviseeOptions"
                :loading="adviseeLoading"
                :disabled="isStudent || userContextLoading"
                item-title="title"
                item-value="value"
                label="Advisee"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                return-object
                :clearable="!isStudent"
                @update:search="handleAdviseeSearch"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props">
                    <v-list-item-title>{{ item?.raw?.name || item?.raw?.title }}</v-list-item-title>
                    <v-list-item-subtitle>{{ item?.raw?.email }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-autocomplete>
              <v-autocomplete
                v-model="createForm.term"
                v-model:search="termSearch"
                :items="termOptions"
                :loading="termLoading"
                item-title="title"
                item-value="value"
                label="Term"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                return-object
                clearable
                @update:search="handleTermSearch"
              >
                <template #item="{ props, item }">
                  <v-list-item v-bind="props">
                    <v-list-item-title>{{ item?.raw?.code || item?.raw?.title }}</v-list-item-title>
                    <v-list-item-subtitle>{{ formatTermRange(item?.raw) }}</v-list-item-subtitle>
                  </v-list-item>
                </template>
              </v-autocomplete>
              <v-select
                v-model="createForm.source"
                :items="sourceOptions"
                label="Source"
                density="comfortable"
                variant="outlined"
                class="mb-3"
              />
              <v-select
                v-model="createForm.status"
                :items="statusOptions"
                label="Status"
                density="comfortable"
                variant="outlined"
                class="mb-4"
              />
              <v-btn
                type="submit"
                color="primary"
                block
                :disabled="createDisabled || mutationLoading"
                :loading="mutationLoading"
              >
                Create Schedule
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <div
          v-if="selectedScheduleId"
          class="d-flex align-center mb-2"
        >
          <v-btn
            variant="text"
            color="primary"
            prepend-icon="mdi-arrow-left"
            @click="handleBackToList"
          >
            Back to schedules
          </v-btn>
          <v-spacer />
        </div>

        <ScheduleDetails
          class="mb-4"
          :schedule="selectedSchedule"
          :status-options="statusOptions"
  :loading="loadingDetail"
  :mutation-loading="mutationLoading"
  :section-options="sectionOptions"
  :section-results="sectionResults"
  :section-loading="sectionSearchLoading"
          :suggestions="suggestions"
          :suggestion-loading="suggestionLoading"
          :suggestion-error="suggestionError"
          :general-recommendations="suggestionRecommendations"
          :suggestion-note="suggestionNote"
          :disable-status-change="isStudent"
          :status-change-hint="isStudent ? 'Students cannot change schedule status.' : ''"
          @update-status="handleStatusUpdate"
          @delete="handleDelete"
          @add-class="handleAddClass"
          @remove-class="handleRemoveClass"
          @search-sections="handleSectionSearch"
          @request-suggestions="handleGenerateSuggestions"
          @apply-suggestion="handleApplySuggestion"
          @cancel-suggestion="handleCancelSuggestion"
          @update:suggestion-note="updateSuggestionNote"
        />

        <ScheduleList
          v-if="!selectedScheduleId"
          :items="schedules"
          :selected-id="selectedScheduleId"
          :loading="loadingList"
          :last-synced-at="lastSyncedAt"
          @select="scheduleStore.selectSchedule"
          @refresh="refreshList"
        />
      </v-col>
    </v-row>

    <v-snackbar
      v-model="feedback.show"
      :color="feedback.color"
      timeout="3000"
      location="bottom right"
    >
      {{ feedback.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, watch, ref } from 'vue'
import { storeToRefs } from 'pinia'
import ScheduleDetails from '@/components/schedules/ScheduleDetails.vue'
import ScheduleList from '@/components/schedules/ScheduleList.vue'
import { useScheduleStore } from '@/stores/schedules'
import { fetchAdvisees } from '@/services/advisees'
import { fetchTerms } from '@/services/terms'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { NORMALIZED_ROLES } from '@/utils/auth'

const scheduleStore = useScheduleStore()
const {
  schedules,
  selectedSchedule,
  selectedScheduleId,
  loadingList,
  loadingDetail,
  mutationLoading,
  lastSyncedAt,
  sectionOptions,
  sectionResults,
  sectionSearchLoading,
  error,
  suggestions,
  suggestionRecommendations,
  suggestionLoading,
  suggestionError,
} = storeToRefs(scheduleStore)

const {
  role: userRole,
  advisee: currentAdvisee,
  loadUserContext,
  loading: userContextLoading,
  error: userContextError,
} = useCurrentUser()

const isStudent = computed(() => userRole.value === NORMALIZED_ROLES.STUDENT)

const studentScopeReady = computed(() => {
  if (!isStudent.value) return true
  return Boolean(studentAdviseeId.value) && !userContextError.value
})

const statusOptions = computed(() => scheduleStore.statusOptions)
const sourceOptions = computed(() => scheduleStore.sourceOptions)

const filters = reactive({ ...scheduleStore.filters })
watch(
  () => scheduleStore.filters,
  (value) => Object.assign(filters, { ...value })
)

const createForm = reactive({
  advisee: null,
  term: null,
  source: sourceOptions.value[0],
  status: statusOptions.value[0],
})

const adviseeOptions = ref([])
const termOptions = ref([])
const adviseeSearch = ref('')
const termSearch = ref('')
const filterAdvisee = ref(null)
const filterTerm = ref(null)
const filterAdviseeSearch = ref('')
const filterTermSearch = ref('')
const adviseeLoading = ref(false)
const termLoading = ref(false)
const suggestionNote = ref('')
const initialStudentFetchApplied = ref(false)

const studentAdviseeId = computed(() =>
  currentAdvisee.value?.adviseeID ? Number(currentAdvisee.value.adviseeID) : null
)

const studentAdviseeOption = computed(() => {
  if (!studentAdviseeId.value) return null
  return {
    value: studentAdviseeId.value,
    title: currentAdvisee.value?.name || `Advisee #${studentAdviseeId.value}`,
    subtitle: currentAdvisee.value?.email || '',
    raw: currentAdvisee.value,
    name: currentAdvisee.value?.name,
    email: currentAdvisee.value?.email,
  }
})

const feedback = reactive({
  show: false,
  text: '',
  color: 'success',
})

const scheduleError = computed(() => error.value)
const userContextErrorMessage = computed(() => userContextError.value)
const createDisabled = computed(() => {
  if (isStudent.value) {
    return !studentAdviseeId.value || !createForm.term
  }
  return !createForm.advisee || !createForm.term
})

const clearError = () => scheduleStore.clearError()

const showFeedback = (text, color = 'success') => {
  feedback.text = text
  feedback.color = color
  feedback.show = true
}

const scopedFetchSchedules = async (overrides = {}) => {
  const scoped = { ...overrides }
  if (!studentScopeReady.value) {
    showFeedback('Unable to load your advisee profile. Please contact support.', 'error')
    return
  }
  if (isStudent.value && studentAdviseeId.value) {
    scoped.adviseeId = studentAdviseeId.value
  }
  await scheduleStore.fetchSchedules(scoped)
}

const syncStudentScope = () => {
  if (!isStudent.value || !studentAdviseeOption.value) return
  filterAdvisee.value = studentAdviseeOption.value
  filters.adviseeName = studentAdviseeOption.value.name || studentAdviseeOption.value.title || ''
  filters.adviseeId = studentAdviseeOption.value.value
  if (!createForm.advisee) {
    createForm.advisee = studentAdviseeOption.value
  }
  scheduleStore.setFilters({
    ...scheduleStore.filters,
    adviseeId: studentAdviseeOption.value.value,
    adviseeName: studentAdviseeOption.value.name || studentAdviseeOption.value.title || '',
  })
}

const formatTermRange = (term) => {
  if (!term?.startDate || !term?.endDate) return ''
  const format = (value) =>
    new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(new Date(value))
  return `${format(term.startDate)} - ${format(term.endDate)}`
}

const loadAdvisees = async (search = '') => {
  adviseeLoading.value = true
  try {
    if (isStudent.value) {
      adviseeOptions.value = studentAdviseeOption.value ? [studentAdviseeOption.value] : []
      return
    }

    const data = await fetchAdvisees({ search, limit: 10 })
    adviseeOptions.value = data.map((item) => ({
      value: Number(item.adviseeID),
      title: item.name || `Advisee #${item.adviseeID}`,
      subtitle: item.email,
      raw: item,
      name: item.name,
      email: item.email,
    }))
  } catch (err) {
    showFeedback(err.message || 'Failed to load advisees', 'error')
  } finally {
    adviseeLoading.value = false
  }
}

const loadTerms = async (search = '') => {
  termLoading.value = true
  try {
    const data = await fetchTerms({ search, limit: 20 })
    termOptions.value = data.map((term) => ({
      value: Number(term.termID),
      title: term.code,
      subtitle: formatTermRange(term),
      raw: term,
    }))
  } catch (err) {
    showFeedback(err.message || 'Failed to load terms', 'error')
  } finally {
    termLoading.value = false
  }
}

const handleAdviseeSearch = (value) => {
  if (isStudent.value) return
  adviseeSearch.value = value
}

const handleTermSearch = (value) => {
  termSearch.value = value
}

const handleFilterAdviseeSearch = (value) => {
  if (isStudent.value) return
  filterAdviseeSearch.value = value
  filters.adviseeName = value || ''
}

const handleFilterTermSearch = (value) => {
  filterTermSearch.value = value
  filters.termName = value || ''
}

watch(adviseeSearch, (value) => {
  if (isStudent.value) return
  loadAdvisees(value)
})

watch(termSearch, (value) => {
  loadTerms(value)
})

watch(filterAdvisee, (value) => {
  if (isStudent.value) return
  filters.adviseeName = value?.name || value?.title || ''
})

watch(filterTerm, (value) => {
  filters.termName = value?.raw?.code || value?.title || ''
})

watch(
  () => currentAdvisee.value,
  () => {
    if (isStudent.value) {
      syncStudentScope()
      loadAdvisees()
    }
  }
)

const refreshList = async () => {
  await scopedFetchSchedules()
  if (selectedScheduleId.value) {
    await scheduleStore.fetchScheduleById(selectedScheduleId.value)
  }
}

const applyFilters = async () => {
  scheduleStore.setFilters({
    ...filters,
    adviseeId: isStudent.value ? studentAdviseeId.value : filters.adviseeId,
    adviseeName: isStudent.value
      ? studentAdviseeOption.value?.name || studentAdviseeOption.value?.title || ''
      : filterAdvisee.value?.name || filterAdviseeSearch.value || '',
    termName: filterTerm.value?.raw?.code || filterTerm.value?.title || filterTermSearch.value || '',
  })
  await scopedFetchSchedules()
}

const resetFilters = async () => {
  scheduleStore.resetFilters()
  Object.assign(filters, { ...scheduleStore.filters })
  filterAdvisee.value = isStudent.value ? studentAdviseeOption.value : null
  filterTerm.value = null
  filterAdviseeSearch.value = isStudent.value
    ? studentAdviseeOption.value?.name || ''
    : ''
  filterTermSearch.value = ''
  if (isStudent.value) {
    syncStudentScope()
  }
  await scopedFetchSchedules()
}

const handleCreate = async () => {
  const adviseeId = isStudent.value ? studentAdviseeId.value : createForm.advisee?.value
  if (!adviseeId || !createForm.term) {
    showFeedback('Advisee and Term are required', 'error')
    return
  }

  createForm.advisee = isStudent.value && studentAdviseeOption.value
    ? studentAdviseeOption.value
    : createForm.advisee

  const payload = {
    adviseeID: Number(adviseeId),
    termID: Number(createForm.term?.value),
    source: createForm.source,
    status: createForm.status,
  }

  try {
    await scheduleStore.createSchedule(payload)
    Object.assign(createForm, {
      advisee: isStudent.value ? studentAdviseeOption.value : null,
      term: null,
      source: sourceOptions.value[0],
      status: statusOptions.value[0],
    })
    adviseeSearch.value = ''
    termSearch.value = ''
    showFeedback('Schedule created successfully')
  } catch (err) {
    showFeedback(err.message || 'Failed to create schedule', 'error')
  }
}

const handleStatusUpdate = async (newStatus) => {
  if (!selectedSchedule.value) return
  if (isStudent.value) {
    showFeedback('Students cannot change schedule status.', 'error')
    return
  }
  try {
    await scheduleStore.updateSchedule(selectedSchedule.value.scheduleID, { status: newStatus })
    showFeedback('Schedule status updated')
  } catch (err) {
    showFeedback(err.message || 'Failed to update status', 'error')
  }
}

const handleDelete = async (scheduleId) => {
  if (!scheduleId) return
  try {
    await scheduleStore.deleteSchedule(scheduleId)
    showFeedback('Schedule deleted', 'success')
  } catch (err) {
    showFeedback(err.message || 'Failed to delete schedule', 'error')
  }
}

const handleAddClass = async (sectionId) => {
  if (!selectedSchedule.value || !sectionId) return
  try {
    await scheduleStore.addClassToSchedule(selectedSchedule.value.scheduleID, sectionId)
    showFeedback(`Section ${sectionId} added`)
    await scheduleStore.searchSections(selectedSchedule.value.scheduleID, '')
  } catch (err) {
    showFeedback(err.message || 'Failed to add section', 'error')
  }
}

const handleRemoveClass = async (classId) => {
  if (!selectedSchedule.value || !classId) return
  try {
    await scheduleStore.removeClassFromSchedule(selectedSchedule.value.scheduleID, classId)
    showFeedback('Class removed')
    await scheduleStore.searchSections(selectedSchedule.value.scheduleID, '')
  } catch (err) {
    showFeedback(err.message || 'Failed to remove class', 'error')
  }
}

const handleSectionSearch = async (query) => {
  if (!selectedScheduleId.value) return
  try {
    await scheduleStore.searchSections(selectedScheduleId.value, query)
  } catch (err) {
    showFeedback(err.message || 'Failed to search sections', 'error')
  }
}

const updateSuggestionNote = (value) => {
  suggestionNote.value = value || ''
}

const handleGenerateSuggestions = async (note) => {
  if (!selectedScheduleId.value) return

  if (selectedSchedule.value && selectedSchedule.value.status !== 'DRAFT') {
    showFeedback('Switch the schedule to DRAFT to add suggested classes', 'error')
    return
  }

  try {
    await scheduleStore.generateSuggestions(selectedScheduleId.value, note ?? suggestionNote.value)
    showFeedback('Generated schedule suggestions')
  } catch (err) {
    showFeedback(err.message || 'Failed to generate suggestions', 'error')
  }
}

const handleApplySuggestion = async ({ option, strategy = 'merge' } = {}) => {
  if (!selectedScheduleId.value || !option) return
  if (selectedSchedule.value && selectedSchedule.value.status !== 'DRAFT') {
    showFeedback('Schedule must be in DRAFT to add suggested classes', 'error')
    return
  }

  try {
    await scheduleStore.applySuggestedOption(selectedScheduleId.value, option, strategy)
    const message =
      strategy === 'replace'
        ? 'Replaced current classes with suggested schedule.'
        : 'Added suggested classes to your current schedule.'
    showFeedback(message)
    await scheduleStore.searchSections(selectedScheduleId.value, '')
  } catch (err) {
    showFeedback(err.message || 'Failed to apply suggested schedule', 'error')
  }
}

const handleClearSuggestions = () => {
  scheduleStore.clearSuggestions()
  suggestionNote.value = ''
}

const handleCancelSuggestion = (optionNumber) => {
  if (!optionNumber) return
  scheduleStore.removeSuggestionOption(optionNumber)
}

const handleBackToList = () => {
  scheduleStore.clearSelection()
}

watch(
  () => selectedScheduleId.value,
  async (id) => {
    handleClearSuggestions()
    if (id) {
      await scheduleStore.searchSections(id, '')
    }
  }
)

const ensureInitialFetch = async () => {

  handleBackToList()
  await resetFilters()

  if (isStudent.value) {
    if (!studentScopeReady.value || initialStudentFetchApplied.value) return
    await applyFilters()
    initialStudentFetchApplied.value = true
    return
  }

  await applyFilters()
}

watch(
  () => studentScopeReady.value,
  async (ready) => {
    if (!ready || !isStudent.value || initialStudentFetchApplied.value) return
    await ensureInitialFetch()
  }
)

onMounted(async () => {
  try {
    await loadUserContext()
  } catch (err) {
    console.error('Failed to load user context', err)
  }

  syncStudentScope()

  await ensureInitialFetch()
  await loadAdvisees()
  await loadTerms()
})
</script>
