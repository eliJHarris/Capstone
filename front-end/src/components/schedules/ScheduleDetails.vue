<template>
  <v-card rounded="xl" variant="flat">
    <template v-if="schedule">
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

        <v-row dense class="mb-4">
          <v-col cols="12" md="6">
            <v-select
              v-model="statusModel"
              :items="statusOptions"
              label="Status"
              density="compact"
              variant="outlined"
            />
          </v-col>
          <v-col cols="12" md="6" class="d-flex align-end">
            <v-btn
              color="primary"
              block
              :disabled="!statusChanged || mutationLoading"
              :loading="mutationLoading && pendingAction === 'status'"
              @click="handleStatusUpdate"
            >
              Update Status
            </v-btn>
          </v-col>
        </v-row>

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
          </v-col>
          <v-col cols="12" md="4" class="d-flex align-end">
            <v-btn
              color="secondary"
              block
              :disabled="addDisabled"
              :loading="mutationLoading && pendingAction === 'add-class'"
              @click="handleAddClass"
            >
              Add Class
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
                        :loading="isApplyingOption(option, 'confirm')"
                        @click="applySuggestion(option, 'confirm')"
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
                      <div class="text-caption text-medium-emphasis mb-1">Warnings</div>
                      <v-chip
                        v-for="warning in option.warnings"
                        :key="warning"
                        color="warning"
                        variant="tonal"
                        size="small"
                        class="mr-2 mb-1"
                      >
                        {{ warning }}
                      </v-chip>
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
    </template>

    <template v-else>
      <v-card-text class="text-medium-emphasis">
        Select a schedule from the list to see its details.
      </v-card-text>
    </template>

    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
    />
  </v-card>

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

  <v-dialog v-model="suggestionStrategyDialog" max-width="520">
    <v-card>
      <v-card-title>How should we add these classes?</v-card-title>
      <v-card-text>
        <v-radio-group v-model="suggestionStrategy" hide-details>
          <v-radio label="Add to current classes" value="merge" />
          <v-radio label="Replace current classes with suggested" value="replace" />
        </v-radio-group>
        <div class="text-caption text-medium-emphasis mt-2">
          Your existing classes: {{ classes.length }} • Suggested: {{ pendingSuggestionOption?.courses?.length || 0 }}
        </div>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="suggestionStrategyDialog = false">Cancel</v-btn>
        <v-btn color="primary" :loading="mutationLoading" @click="confirmSuggestionStrategy">
          Continue
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

const classes = computed(() => props.schedule?.classes ?? [])
const isDraft = computed(() => props.schedule?.status === 'DRAFT')
const statusModel = ref('')
const sectionId = ref('')
const sectionSearch = ref('')
const dialogOpen = ref(false)
const pendingAction = ref(null)
const suggestionPendingAction = ref('')
const localSuggestionNote = ref('')
const suggestionStrategyDialog = ref(false)
const suggestionStrategy = ref('merge')
const pendingSuggestionOption = ref(null)

watch(
  () => props.schedule?.status,
  (value) => {
    statusModel.value = value || ''
  },
  { immediate: true }
)

watch(
  () => props.schedule?.scheduleID,
  () => {
    sectionId.value = ''
    sectionSearch.value = ''
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

function handleAddClass() {
  if (!sectionId.value || !isDraft.value) return
  pendingAction.value = 'add-class'
  emit('add-class', Number(sectionId.value))
  sectionId.value = ''
}

function handleStatusUpdate() {
  if (!statusChanged.value) return
  pendingAction.value = 'status'
  emit('update-status', statusModel.value)
}

function requestRemoveClass(classId) {
  if (!isDraft.value) return
  pendingAction.value = `remove-${classId}`
  emit('remove-class', classId)
}

function confirmDelete() {
  dialogOpen.value = false
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

function applySuggestion(option, mode) {
  if (!option) return
  if (classes.value.length > 0) {
    pendingSuggestionOption.value = option
    suggestionStrategy.value = 'merge'
    suggestionStrategyDialog.value = true
    return
  }
  suggestionPendingAction.value = `${mode}-${option.option_number}`
  emit('apply-suggestion', { option, strategy: 'merge' })
}

function isApplyingOption(option, mode) {
  return suggestionPendingAction.value === `${mode}-${option.option_number}` && props.mutationLoading
}

function cancelSuggestion(option) {
  if (!option) return
  emit('cancel-suggestion', option.option_number)
}

function confirmSuggestionStrategy() {
  if (!pendingSuggestionOption.value) return
  const strategy = suggestionStrategy.value === 'replace' ? 'replace' : 'merge'
  suggestionPendingAction.value = `${strategy}-${pendingSuggestionOption.value.option_number}`
  emit('apply-suggestion', { option: pendingSuggestionOption.value, strategy })
  suggestionStrategyDialog.value = false
  pendingSuggestionOption.value = null
}

function emitSearch(value) {
  emit('search-sections', value)
}

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
