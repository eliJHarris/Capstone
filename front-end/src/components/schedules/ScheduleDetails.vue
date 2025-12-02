<template>
  <v-card rounded="xl" variant="flat">
    <template v-if="schedule">
      <v-card-title class="d-flex align-center">
        <div>
          <div class="text-h6">Schedule #{{ schedule.scheduleID }}</div>
          <div class="text-caption text-medium-emphasis">
            Term {{ schedule.termCode || schedule.termID }} • Advisee {{ schedule.adviseeID }}
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
              :disabled="!canSubmitStatus || mutationLoading"
              :loading="mutationLoading && pendingAction === 'status'"
              @click="handleStatusUpdate"
            >
              Update Status
            </v-btn>
          </v-col>
        </v-row>

        <v-row dense class="mb-4">
          <v-col cols="12">
            <v-textarea
              v-model="feedbackModel"
              label="Advisor feedback"
              auto-grow
              rows="2"
              variant="outlined"
              density="compact"
              :maxlength="500"
              :counter="500"
              :hint="feedbackHint"
              persistent-hint
              :color="requiresFeedback ? 'primary' : undefined"
              :error="requiresFeedback && !feedbackValid"
              :error-messages="requiresFeedback && !feedbackValid ? ['Feedback is required for approvals and rejections.'] : []"
            />
          </v-col>
        </v-row>

        <v-row dense class="mb-4">
          <v-col cols="12" md="6">
            <v-text-field
              label="Section ID"
              v-model="sectionId"
              type="number"
              density="compact"
              variant="outlined"
            />
          </v-col>
          <v-col cols="12" md="6" class="d-flex align-end">
            <v-btn
              color="secondary"
              block
              :disabled="!sectionId || mutationLoading"
              :loading="mutationLoading && pendingAction === 'add-class'"
              @click="handleAddClass"
            >
              Add Section To Schedule
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

        <div class="d-flex align-center mb-2">
          <h3 class="text-subtitle-1 mb-0">Classes ({{ classes.length }})</h3>
        </div>
        <v-table density="comfortable">
          <thead>
            <tr>
              <th class="text-left">Course</th>
              <th class="text-left">CRN</th>
              <th class="text-left">Professor</th>
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
              <td>{{ cls.credits }}</td>
              <td>{{ formatDate(cls.createdDate) }}</td>
              <td class="text-right">
                <v-btn
                  icon="mdi-delete"
                  size="small"
                  variant="text"
                  color="error"
                  :disabled="mutationLoading"
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
})

const emit = defineEmits(['update-status', 'delete', 'add-class', 'remove-class'])

const classes = computed(() => props.schedule?.classes ?? [])
const statusModel = ref('')
const sectionId = ref('')
const feedbackModel = ref('')
const dialogOpen = ref(false)
const pendingAction = ref(null)

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
  }
)

watch(
  () => props.mutationLoading,
  (value) => {
    if (!value) pendingAction.value = null
  }
)

watch(
  () => props.schedule?.advisorFeedback,
  (value) => {
    feedbackModel.value = value || ''
  },
  { immediate: true }
)

const statusChanged = computed(() => props.schedule && statusModel.value && statusModel.value !== props.schedule.status)
const trimmedFeedback = computed(() => feedbackModel.value.trim())
const requiresFeedback = computed(() => ['APPROVED', 'REJECTED'].includes(statusModel.value || ''))
const feedbackValid = computed(() => !requiresFeedback.value || Boolean(trimmedFeedback.value))
const canSubmitStatus = computed(() => statusChanged.value && feedbackValid.value)
const feedbackHint = computed(() =>
  requiresFeedback.value ? 'Provide guidance for the advisee when approving or rejecting.' : 'Optional note shared with the advisee.'
)

function handleAddClass() {
  if (!sectionId.value) return
  pendingAction.value = 'add-class'
  emit('add-class', Number(sectionId.value))
  sectionId.value = ''
}

function handleStatusUpdate() {
  if (!canSubmitStatus.value) return
  pendingAction.value = 'status'
  emit('update-status', {
    status: statusModel.value,
    advisorFeedback: trimmedFeedback.value || null,
  })
}

function requestRemoveClass(classId) {
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

const formatDate = (value) => {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
</script>
