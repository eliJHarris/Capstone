<template>
  <v-card
    v-if="schedule"
    rounded="xl"
    variant="flat"
  >
      <v-card-title class="d-flex align-center">
        <div>
          <div class="text-h6">Schedule #{{ schedule.scheduleID }}</div>
          <div class="text-caption text-medium-emphasis">
            Term {{ schedule.termName || schedule.termCode || schedule.termID }} • Advisee
            {{ schedule.adviseeName || schedule.adviseeID }}
          </div>
        </div>
        <v-spacer />
        <v-btn
          v-if="canDelete"
          variant="text"
          color="error"
          :disabled="mutationLoading"
          @click="dialogOpen = true"
        >
          Delete
        </v-btn>
      </v-card-title>

      <v-card-text>
        <v-alert
          v-if="!isDraft"
          type="info"
          variant="tonal"
          class="mb-4"
          density="comfortable"
        >
          Classes can only be modified while the schedule is in DRAFT. Update the status
          to DRAFT to make changes.
        </v-alert>

        <v-alert
          v-if="isRejected && feedbackModel"
          type="error"
          variant="tonal"
          border="start"
          class="mb-4"
          density="comfortable"
        >
          <div class="text-subtitle-2 mb-1">Advisor feedback</div>
          <div class="text-body-2">{{ feedbackModel }}</div>
        </v-alert>

        <v-row dense class="mb-4" align="start">
          <v-col cols="12" md="6">
            <v-select
              v-model="statusModel"
              :items="statusOptions"
              label="Status"
              density="compact"
              variant="outlined"
              :disabled="disableStatusChange"
            />
          </v-col>
          <v-col cols="12" md="6" class="d-flex align-start justify-end">
            <v-btn
              color="primary"
              block
              :disabled="disableStatusChange || !hasPendingChanges || mutationLoading"
              :loading="mutationLoading && pendingAction === 'status'"
              @click="handleStatusUpdate"
            >
              Save Updates
            </v-btn>
          </v-col>
        </v-row>

        <v-alert
          v-if="disableStatusChange && statusChangeHint"
          type="info"
          variant="tonal"
          density="comfortable"
          class="mb-4"
        >
          {{ statusChangeHint }}
        </v-alert>

        <v-textarea
          v-model="feedbackModel"
          label="Advisor feedback"
          variant="outlined"
          density="comfortable"
          rows="3"
          auto-grow
          class="mb-4"
          :readonly="disableStatusChange"
          :placeholder="disableStatusChange ? '' : 'Explain why changes are needed or next steps...'"
        />
        <div class="text-caption text-medium-emphasis mb-6">
          Shared with the advisee when the schedule is rejected.
        </div>

        <v-row dense class="mb-4">
          <v-col cols="12" md="8">
            <v-autocomplete
              v-model="sectionId"
              v-model:search="sectionSearch"
              :items="sectionOptions"
              :loading="sectionLoading"
              label="Add class by course"
              density="compact"
              variant="outlined"
              item-title="title"
              item-value="value"
              :return-object="false"
              clearable
              @update:search="emitSearch"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <v-list-item-title>
                    {{ item?.raw?.title }}
                  </v-list-item-title>
                  <v-list-item-subtitle>
                    {{ item?.raw?.subtitle }}
                  </v-list-item-subtitle>
                  <template #append>
                    <div class="text-right">
                      <div class="text-caption text-medium-emphasis">
                        {{ seatSummary(item?.raw?.meta) }}
                      </div>
                    </div>
                  </template>
                </v-list-item>
              </template>
              <template #no-data>
                <div class="px-4 py-2 text-medium-emphasis text-caption">
                  {{ sectionSearch ? 'No classes match your search' : 'Start typing a course name or CRN' }}
                </div>
              </template>
            </v-autocomplete>
            <div class="d-flex align-center text-caption text-medium-emphasis mt-1">
              <v-icon size="16" class="mr-1">mdi-table-eye</v-icon>
              Use Browse classes to scan results in a wider table view.
            </div>
          </v-col>
          <v-col cols="12" md="4" class="d-flex flex-column justify-end">
            <v-btn
              color="secondary"
              block
              :disabled="addDisabled"
              :loading="isAddingSection(sectionId)"
              @click="handleAddClass"
            >
              Add Class
            </v-btn>
            <v-btn
              class="mt-2"
              variant="tonal"
              color="primary"
              block
              :disabled="sectionLoading"
              :loading="sectionLoading"
              @click="sectionBrowserOpen = true"
            >
              Browse classes
            </v-btn>
          </v-col>
        </v-row>

        <v-card class="mb-4" variant="tonal">
          <v-card-title class="text-subtitle-1">Metadata</v-card-title>
          <v-card-text>
            <v-row dense>
              <v-col cols="12" md="6">
                <strong>Source:</strong> {{ schedule.source }}
              </v-col>
              <v-col cols="12" md="6">
                <strong>Created:</strong> {{ formatDate(schedule.createdWhen) }}
              </v-col>
              <v-col cols="12" md="6">
                <strong>Approved:</strong> {{ formatDate(schedule.approvedWhen) }}
              </v-col>
              <v-col cols="12" md="6">
                <strong>Rejected:</strong> {{ formatDate(schedule.rejectedWhen) }}
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-card class="mb-4" variant="tonal">
          <v-card-title class="d-flex align-center">
            <div>
              <div class="text-subtitle-1">AI suggested schedules</div>
              <div class="text-caption text-medium-emphasis">
                Generate 12–15 credit options from open sections.
              </div>
            </div>
            <v-spacer />
            <v-btn
              color="primary"
              variant="flat"
              :loading="suggestionLoading"
              :disabled="!isDraft || suggestionLoading || loading"
              @click="emitSuggestions"
            >
              Get suggested schedule
            </v-btn>
          </v-card-title>
          <v-card-text>
            <v-textarea
              v-model="localSuggestionNote"
              label="Preferences or constraints (optional)"
              rows="2"
              auto-grow
              density="comfortable"
              variant="outlined"
              placeholder="e.g., Avoid Friday classes, prefer mornings, cap at 14 credits."
              :disabled="suggestionLoading"
              class="mb-3"
              @change="emitNote"
              @blur="emitNote"
            />

            <v-alert
              v-if="suggestionError"
              type="error"
              density="comfortable"
              class="mb-3"
            >
              {{ suggestionError }}
            </v-alert>

            <div v-if="suggestionLoading" class="py-4 d-flex align-center">
              <v-progress-circular indeterminate color="primary" class="mr-3" />
              <div class="text-medium-emphasis">Generating schedule options...</div>
            </div>
            <template v-else-if="suggestions && suggestions.length">
              <v-alert
                v-if="generalRecommendations"
                type="info"
                variant="tonal"
                density="comfortable"
                class="mb-3"
              >
                {{ generalRecommendations }}
              </v-alert>

              <v-row dense>
                <v-col
                  v-for="option in suggestions"
                  :key="option.option_number"
                  cols="12"
                >
                  <v-sheet rounded="lg" border class="pa-3">
                    <div class="d-flex align-center mb-2">
                      <div>
                        <div class="text-subtitle-1">Option {{ option.option_number }}</div>
                        <div class="text-caption text-medium-emphasis">
                          Total credits: {{ option.total_credits }}
                        </div>
                      </div>
                      <v-spacer />
                      <v-btn
                        color="primary"
                        size="small"
                        class="mr-2"
                        :disabled="!isDraft || mutationLoading"
                        :loading="isApplyingOption(option)"
                        @click="applySuggestion(option)"
                      >
                        Confirm
                      </v-btn>
                      <v-btn
                        variant="text"
                        size="small"
                        :disabled="suggestionLoading"
                        @click="cancelSuggestion(option)"
                      >
                        Cancel
                      </v-btn>
                    </div>

                    <div v-if="option.rationale" class="text-body-2 mb-2">
                      {{ option.rationale }}
                    </div>

                    <v-chip-group column>
                      <v-chip
                        v-for="course in option.courses"
                        :key="`${option.option_number}-${course.section || course.course_code}`"
                        class="mr-2 mb-2"
                        color="secondary"
                        variant="tonal"
                        label
                      >
                        {{ course.course_code || course.course_name }} ({{ course.credits }} cr)
                        <span
                          v-if="course.section"
                          class="text-caption text-medium-emphasis"
                        >
                          &nbsp;• Section {{ course.section }}
                        </span>
                      </v-chip>
                    </v-chip-group>

                    <div v-if="option.warnings && option.warnings.length" class="mt-2">
                      <div class="d-flex align-center mb-1">
                        <div class="text-caption text-medium-emphasis">
                          Warnings ({{ option.warnings.length }})
                        </div>
                        <v-spacer />
                        <v-btn
                          size="x-small"
                          variant="text"
                          color="warning"
                          @click="openWarningDialog(option)"
                        >
                          View warnings
                        </v-btn>
                      </div>
                    </div>
                  </v-sheet>
                </v-col>
              </v-row>
            </template>
            <div v-else class="text-caption text-medium-emphasis">
              No suggestions yet. Ask for a suggested schedule to get started.
            </div>
          </v-card-text>
        </v-card>

        <div class="d-flex align-center mb-2">
          <h3 class="text-subtitle-1 mb-0">Classes ({{ classes.length }})</h3>
        </div>
        <v-table density="comfortable">
          <thead>
            <tr>
              <th class="text-left">Course</th>
              <th class="text-left">CRN</th>
              <th class="text-left">Professor</th>
              <th class="text-left">Status</th>
              <th class="text-left">Seats</th>
              <th class="text-left">Credits</th>
              <th class="text-left">Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="classes.length === 0">
              <td colspan="6" class="text-medium-emphasis">
                No classes added yet.
              </td>
            </tr>
            <tr
              v-for="cls in classes"
              :key="cls.classID"
            >
              <td>
                <div class="font-weight-medium">{{ cls.courseName }}</div>
                <div class="text-caption text-medium-emphasis">{{ cls.courseDescription }}</div>
              </td>
              <td>{{ cls.crn }}</td>
              <td>{{ cls.professorName || 'TBD' }}</td>
              <td>
                <v-chip
                  size="small"
                  :color="sectionStatusColor(cls.sectionStatus)"
                  variant="tonal"
                >
                  {{ cls.sectionStatus || 'UNKNOWN' }}
                </v-chip>
              </td>
              <td>
                <div class="font-weight-medium">
                  {{ cls.enrolled ?? 0 }} / {{ cls.capacity ?? 0 }}
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ cls.seatsRemaining ?? Math.max((cls.capacity || 0) - (cls.enrolled || 0), 0) }} open seats
                </div>
              </td>
              <td>{{ cls.credits }}</td>
              <td>{{ formatDate(cls.createdDate) }}</td>
              <td class="text-right">
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  color="error"
                  :disabled="mutationLoading || !isDraft"
                  :loading="mutationLoading && pendingAction === `remove-${cls.classID}`"
                  @click="requestRemoveClass(cls.classID)"
                />
              </td>
            </tr>
          </tbody>
        </v-table>
      </v-card-text>
  </v-card>

  <v-progress-linear
    v-if="loading"
    indeterminate
    color="primary"
  />

  <v-dialog v-model="sectionBrowserOpen" max-width="1100">
    <v-card>
      <v-card-title class="d-flex align-center">
        <div>
          <div class="text-subtitle-1">Browse classes</div>
          <div class="text-caption text-medium-emphasis">
            Search available sections for this schedule's term.
          </div>
        </div>
        <v-spacer />
        <v-text-field
          v-model="sectionSearch"
          prepend-inner-icon="mdi-magnify"
          density="compact"
          variant="outlined"
          hide-details
          clearable
          placeholder="Search by course name, CRN, or professor"
          :loading="sectionLoading"
          style="max-width: 360px;"
          @update:model-value="emitSearch"
          @click:clear="emitSearch('')"
        />
        <v-btn
          icon="mdi-close"
          variant="text"
          class="ml-2"
          @click="sectionBrowserOpen = false"
        />
      </v-card-title>
      <v-card-text>
        <v-alert
          v-if="!isDraft"
          type="info"
          variant="tonal"
          density="comfortable"
          class="mb-3"
        >
          Switch to DRAFT to add classes.
        </v-alert>

        <v-data-table
          :headers="sectionHeaders"
          :items="sectionTableItems"
          :loading="sectionLoading"
          item-key="sectionID"
          :items-per-page="8"
          hover
          density="comfortable"
        >
          <template #item.course="{ item }">
            <div class="font-weight-medium">
              {{ item.raw?.courseName || item.courseName }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ item.raw?.courseDescription || item.courseDescription || '—' }}
            </div>
          </template>

          <template #item.professorName="{ item }">
            <div class="font-weight-medium">
              {{ item.raw?.professorName || item.professorName || 'TBD' }}
            </div>
          </template>

          <template #item.status="{ item }">
            <v-chip
              size="small"
              :color="sectionStatusColor(item.raw?.status || item.status)"
              variant="tonal"
            >
              {{ item.raw?.status || item.status }}
            </v-chip>
          </template>

          <template #item.seats="{ item }">
            <div class="font-weight-medium">
              {{ item.raw?.enrolled ?? item.enrolled ?? 0 }} / {{ item.raw?.capacity ?? item.capacity ?? 0 }}
            </div>
            <div class="text-caption text-medium-emphasis">
              {{ item.raw?.seatsRemaining ?? item.seatsRemaining ?? 0 }} open
            </div>
          </template>

          <template #item.credits="{ item }">
            <div class="text-right">{{ item.raw?.credits ?? item.credits }}</div>
          </template>

          <template #item.actions="{ item }">
            <v-btn
              color="primary"
              size="small"
              :disabled="!isDraft || mutationLoading"
              :loading="isAddingSection(item.raw?.sectionID || item.sectionID)"
              @click="handleAddClassFromList(item.raw?.sectionID || item.sectionID)"
            >
              Add
            </v-btn>
          </template>

          <template #no-data>
            <v-alert type="info" variant="tonal" class="ma-4" border="start">
              No classes match your search. Try a different keyword.
            </v-alert>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-dialog v-model="warningDialogOpen" max-width="700">
    <v-card class="warning-dialog-card">
      <v-card-title class="d-flex align-center">
        <v-icon color="warning" class="mr-3">mdi-alert-circle-outline</v-icon>
        <div>
          <div class="text-subtitle-1">
            Warnings for Option {{ warningDialogOption || '—' }}
          </div>
          <div class="text-caption text-medium-emphasis">
            Review details before applying this schedule.
          </div>
        </div>
        <v-spacer />
        <v-btn icon="mdi-close" variant="text" @click="warningDialogOpen = false" />
      </v-card-title>
      <v-card-text>
        <v-sheet class="pa-3 warning-sheet" rounded="lg" variant="tonal" color="warning">
          <div class="text-body-2 text-medium-emphasis">
            Consider resolving these items or confirm they are acceptable.
          </div>
        </v-sheet>

        <v-list density="comfortable" class="warning-list mt-3" lines="three">
          <v-list-item
            v-for="(warning, idx) in warningDialogWarnings"
            :key="`${warning}-${idx}`"
            class="warning-list-item"
          >
            <template #prepend>
              <div class="warning-bullet" />
            </template>
            <v-list-item-title class="text-body-2 warning-list-title">
              {{ warning }}
            </v-list-item-title>
          </v-list-item>
        </v-list>
      </v-card-text>
      <v-card-actions class="px-6 pb-4">
        <v-spacer />
        <v-btn variant="text" @click="warningDialogOpen = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-dialog v-model="dialogOpen" max-width="420">
    <v-card>
      <v-card-title>Delete schedule?</v-card-title>
      <v-card-text>
        This action is permanent and will remove all classes assigned to this schedule.
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="dialogOpen = false">Cancel</v-btn>
        <v-btn
          color="error"
          :loading="mutationLoading"
          @click="confirmDelete"
        >
          Delete
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  schedule: {
    type: Object,
    default: null,
  },
  statusOptions: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  mutationLoading: {
    type: Boolean,
    default: false,
  },
  sectionOptions: {
    type: Array,
    default: () => [],
  },
  sectionResults: {
    type: Array,
    default: () => [],
  },
  sectionLoading: {
    type: Boolean,
    default: false,
  },
  suggestions: {
    type: Array,
    default: () => [],
  },
  suggestionLoading: {
    type: Boolean,
    default: false,
  },
  suggestionError: {
    type: String,
    default: '',
  },
  suggestionNote: {
    type: String,
    default: '',
  },
  generalRecommendations: {
    type: String,
    default: '',
  },
  disableStatusChange: {
    type: Boolean,
    default: false,
  },
  statusChangeHint: {
    type: String,
    default: '',
  },
})

const emit = defineEmits([
  'update-status',
  'delete',
  'add-class',
  'remove-class',
  'search-sections',
  'request-suggestions',
  'apply-suggestion',
  'cancel-suggestion',
  'update:suggestion-note',
])

const sectionHeaders = [
  { title: 'Course', key: 'course', sortable: false },
  { title: 'CRN', key: 'crn', sortable: false },
  { title: 'Professor', key: 'professorName', sortable: false },
  { title: 'Status', key: 'status', sortable: false },
  { title: 'Seats', key: 'seats', sortable: false },
  { title: 'Credits', key: 'credits', align: 'end' },
  { title: '', key: 'actions', sortable: false },
]

const classes = computed(() => props.schedule?.classes ?? [])
const sectionTableItems = computed(() =>
  (props.sectionResults || []).map((item) => ({
    ...item,
    course: item.courseName,
    seats: item.seatsRemaining,
    raw: item,
  }))
)
const isDraft = computed(() => props.schedule?.status === 'DRAFT')
const isRejected = computed(() => props.schedule?.status === 'REJECTED')
const statusModel = ref('')
const sectionId = ref('')
const sectionSearch = ref('')
const dialogOpen = ref(false)
const sectionBrowserOpen = ref(false)
const pendingAction = ref(null)
const suggestionPendingAction = ref('')
const localSuggestionNote = ref('')
const warningDialogOpen = ref(false)
const warningDialogWarnings = ref([])
const warningDialogOption = ref(null)
const feedbackModel = ref('')

watch(
  () => props.schedule?.status,
  (value) => {
    statusModel.value = value || ''
  },
  { immediate: true }
)

watch(
  () => props.schedule?.advisorFeedback,
  (value) => {
    feedbackModel.value = value || ''
  },
  { immediate: true }
)

watch(
  () => props.schedule?.scheduleID,
  () => {
    sectionId.value = ''
    sectionSearch.value = ''
    sectionBrowserOpen.value = false
    emitSearch('')
  }
)

watch(
  () => props.mutationLoading,
  (value) => {
    if (!value) {
      pendingAction.value = null
      suggestionPendingAction.value = ''
    }
  }
)

watch(
  () => props.suggestionNote,
  (value) => {
    localSuggestionNote.value = value || ''
  },
  { immediate: true }
)

const addDisabled = computed(() => !sectionId.value || props.mutationLoading || !isDraft.value)
const statusChanged = computed(() => props.schedule && statusModel.value && statusModel.value !== props.schedule.status)
const normalizedFeedback = computed(() => (feedbackModel.value || '').trim())
const feedbackChanged = computed(() => {
  const current = (props.schedule?.advisorFeedback || '').trim()
  return normalizedFeedback.value !== current
})
const hasPendingChanges = computed(() => statusChanged.value || feedbackChanged.value)

function handleAddClass() {
  if (!sectionId.value || !isDraft.value) return
  pendingAction.value = `add-${sectionId.value}`
  emit('add-class', Number(sectionId.value))
  sectionId.value = ''
  sectionSearch.value = ''
  emitSearch('')
}

function handleAddClassFromList(sectionId) {
  const id = Number(sectionId)
  if (!id || !isDraft.value) return
  pendingAction.value = `add-${id}`
  emit('add-class', id)
  sectionSearch.value = ''
  emitSearch('')
}

function handleStatusUpdate() {
  if (!hasPendingChanges.value) return
  pendingAction.value = 'status'
  emit('update-status', {
    status: statusModel.value,
    advisorFeedback: normalizedFeedback.value || null,
  })
}

function requestRemoveClass(classId) {
  if (!isDraft.value) return
  pendingAction.value = `remove-${classId}`
  emit('remove-class', classId)
}

function confirmDelete() {
  dialogOpen.value = false
  if (!props.canDelete) return
  if (props.schedule) {
    pendingAction.value = 'delete'
    emit('delete', props.schedule.scheduleID)
  }
}

function emitNote() {
  emit('update:suggestion-note', localSuggestionNote.value)
}

function emitSuggestions() {
  emitNote()
  emit('request-suggestions', localSuggestionNote.value)
}

function applySuggestion(option) {
  if (!option) return
  const strategy = option.option_number === 3 ? 'replace' : 'merge'
  suggestionPendingAction.value = `${strategy}-${option.option_number}`
  emit('apply-suggestion', { option, strategy })
}

function openWarningDialog(option) {
  warningDialogWarnings.value = option?.warnings || []
  warningDialogOption.value = option?.option_number || null
  warningDialogOpen.value = true
}

function isApplyingOption(option) {
  return (
    props.mutationLoading &&
    (suggestionPendingAction.value === `merge-${option.option_number}` ||
      suggestionPendingAction.value === `replace-${option.option_number}`)
  )
}

function cancelSuggestion(option) {
  if (!option) return
  emit('cancel-suggestion', option.option_number)
}

function emitSearch(value) {
  emit('search-sections', value)
}

const isAddingSection = (sectionId) =>
  Boolean(sectionId) && props.mutationLoading && pendingAction.value === `add-${sectionId}`

const seatSummary = (meta = {}) => {
  const { enrolled = 0, capacity = 0, seatsRemaining = Math.max((capacity || 0) - (enrolled || 0), 0) } = meta
  return `${enrolled}/${capacity} • ${seatsRemaining} open`
}

const formatDate = (value) => {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

const sectionStatusColor = (status) => {
  const map = {
    OPEN: 'green',
    CLOSED: 'grey',
    CANCELLED: 'error',
  }
  return map[status] || 'primary'
}
</script>

<style scoped>
.warning-list {
  max-height: 320px;
  overflow-y: auto;
}

.warning-list-item {
  align-items: flex-start;
}

.warning-list-title {
  white-space: normal;
  word-break: break-word;
  line-height: 1.5;
}

.warning-dialog-card {
  box-shadow: 0 12px 36px rgba(0, 0, 0, 0.18);
}

.warning-sheet {
  background-color: rgba(255, 152, 0, 0.12) !important;
  border: 1px solid rgba(255, 152, 0, 0.3);
}

.warning-bullet {
  width: 10px;
  height: 10px;
  margin-top: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #ffb74d, #f57c00);
  box-shadow: 0 0 0 4px rgba(255, 152, 0, 0.15);
}
</style>
