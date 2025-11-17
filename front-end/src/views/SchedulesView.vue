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

    <v-row dense>
      <v-col cols="12" md="4">
        <v-card rounded="xl" variant="flat" class="mb-4">
          <v-card-title>Filter schedules</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="applyFilters">
              <v-text-field
                v-model="filters.adviseeId"
                label="Advisee ID"
                type="number"
                density="comfortable"
                variant="outlined"
                class="mb-3"
              />
              <v-text-field
                v-model="filters.termId"
                label="Term ID"
                type="number"
                density="comfortable"
                variant="outlined"
                class="mb-3"
              />
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
              <v-text-field
                v-model="createForm.adviseeID"
                label="Advisee ID"
                type="number"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                required
              />
              <v-text-field
                v-model="createForm.termID"
                label="Term ID"
                type="number"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                required
              />
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
        <ScheduleList
          :items="schedules"
          :selected-id="selectedScheduleId"
          :loading="loadingList"
          :last-synced-at="lastSyncedAt"
          @select="scheduleStore.selectSchedule"
          @refresh="refreshList"
        />

        <ScheduleDetails
          :schedule="selectedSchedule"
          :status-options="statusOptions"
          :loading="loadingDetail"
          :mutation-loading="mutationLoading"
          @update-status="handleStatusUpdate"
          @delete="handleDelete"
          @add-class="handleAddClass"
          @remove-class="handleRemoveClass"
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
import { reactive, computed, onMounted, watch } from 'vue'
import { storeToRefs } from 'pinia'
import ScheduleDetails from '@/components/schedules/ScheduleDetails.vue'
import ScheduleList from '@/components/schedules/ScheduleList.vue'
import { useScheduleStore } from '@/stores/schedules'

const scheduleStore = useScheduleStore()
const {
  schedules,
  selectedSchedule,
  selectedScheduleId,
  loadingList,
  loadingDetail,
  mutationLoading,
  lastSyncedAt,
  error,
} = storeToRefs(scheduleStore)

const statusOptions = computed(() => scheduleStore.statusOptions)
const sourceOptions = computed(() => scheduleStore.sourceOptions)

const filters = reactive({ ...scheduleStore.filters })
watch(
  () => scheduleStore.filters,
  (value) => Object.assign(filters, { ...value })
)

const createForm = reactive({
  adviseeID: '',
  termID: '',
  source: sourceOptions.value[0],
  status: statusOptions.value[0],
})

const feedback = reactive({
  show: false,
  text: '',
  color: 'success',
})

const scheduleError = computed(() => error.value)
const createDisabled = computed(() => !createForm.adviseeID || !createForm.termID)

const clearError = () => scheduleStore.clearError()

const showFeedback = (text, color = 'success') => {
  feedback.text = text
  feedback.color = color
  feedback.show = true
}

const refreshList = async () => {
  await scheduleStore.fetchSchedules()
  if (selectedScheduleId.value) {
    await scheduleStore.fetchScheduleById(selectedScheduleId.value)
  }
}

const applyFilters = async () => {
  scheduleStore.setFilters({ ...filters })
  await scheduleStore.fetchSchedules()
}

const resetFilters = async () => {
  scheduleStore.resetFilters()
  Object.assign(filters, { ...scheduleStore.filters })
  await scheduleStore.fetchSchedules()
}

const handleCreate = async () => {
  if (createDisabled.value) {
    showFeedback('Advisee ID and Term ID are required', 'error')
    return
  }

  const payload = {
    adviseeID: Number(createForm.adviseeID),
    termID: Number(createForm.termID),
    source: createForm.source,
    status: createForm.status,
  }

  try {
    await scheduleStore.createSchedule(payload)
    Object.assign(createForm, {
      adviseeID: '',
      termID: '',
      source: sourceOptions.value[0],
      status: statusOptions.value[0],
    })
    showFeedback('Schedule created successfully')
  } catch (err) {
    showFeedback(err.message || 'Failed to create schedule', 'error')
  }
}

const handleStatusUpdate = async (newStatus) => {
  if (!selectedSchedule.value) return
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
  } catch (err) {
    showFeedback(err.message || 'Failed to add section', 'error')
  }
}

const handleRemoveClass = async (classId) => {
  if (!selectedSchedule.value || !classId) return
  try {
    await scheduleStore.removeClassFromSchedule(selectedSchedule.value.scheduleID, classId)
    showFeedback('Class removed')
  } catch (err) {
    showFeedback(err.message || 'Failed to remove class', 'error')
  }
}

onMounted(() => {
  if (!schedules.value.length) {
    scheduleStore.fetchSchedules()
  }
})
</script>
