<template>
  <v-card rounded="xl" variant="flat" class="mb-4">
    <v-card-title class="d-flex align-center">
      <div>
        <div class="text-h6">Schedules</div>
        <div class="text-caption text-medium-emphasis" v-if="lastSyncedAt">
          Synced {{ formatTimestamp(lastSyncedAt) }}
        </div>
      </div>
      <v-spacer />
      <span class="text-caption text-medium-emphasis mr-4" v-if="items.length">
        Click a row to view details
      </span>
      <v-btn
        icon
        variant="text"
        :loading="loading"
        :disabled="loading"
        @click="$emit('refresh')"
      >
        <v-icon>mdi-refresh</v-icon>
      </v-btn>
    </v-card-title>

    <v-data-table
      :headers="headers"
      :items="tableItems"
      item-key="scheduleID"
      :loading="loading"
      :items-per-page="8"
      hover
      density="comfortable"
      @click:row="handleRowClick"
    >
      <template #item.scheduleID="{ item }">
        <div class="d-flex align-center" style="gap: 8px;">
          <v-icon
            v-if="isSelected(item)"
            size="small"
            color="primary"
          >
            mdi-check-circle
          </v-icon>
          <span class="font-weight-medium">#{{ item.raw?.scheduleID || item.scheduleID }}</span>
        </div>
      </template>

      <template #item.advisee="{ item }">
        <div class="d-flex flex-column">
          <span class="font-weight-medium">
            {{ item.raw?.adviseeName || item.advisee || `Advisee ${item.raw?.adviseeID}` }}
          </span>
          <span class="text-caption text-medium-emphasis">
            {{ item.raw?.adviseeEmail || item.raw?.email || '—' }}
          </span>
        </div>
      </template>

      <template #item.term="{ item }">
        <div class="d-flex align-center" style="gap: 8px;">
          <v-chip size="small" color="primary" variant="tonal">
            {{ item.raw?.termName || item.raw?.termCode || item.term }}
          </v-chip>
          <span class="text-caption text-medium-emphasis">
            {{ item.raw?.termID ? `#${item.raw.termID}` : '' }}
          </span>
        </div>
      </template>

      <template #item.status="{ item }">
        <v-chip
          size="small"
          :color="statusColor(item.raw?.status || item.status)"
          variant="tonal"
        >
          {{ item.raw?.status || item.status }}
        </v-chip>
      </template>

      <template #item.classCount="{ item }">
        <div class="text-right font-weight-medium">
          {{ item.raw?.classCount ?? item.classCount ?? 0 }}
        </div>
      </template>

      <template #item.createdWhen="{ item }">
        <div class="text-caption text-medium-emphasis">
          {{ formatTimestamp(item.raw?.createdWhen || item.createdWhen) }}
        </div>
      </template>

      <template #no-data>
        <v-alert type="info" border="start" variant="tonal" class="ma-4">
          No schedules found. Adjust filters or create a new schedule to get started.
        </v-alert>
      </template>
    </v-data-table>
  </v-card>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  selectedId: {
    type: Number,
    default: null,
  },
  loading: {
    type: Boolean,
    default: false,
  },
  lastSyncedAt: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['select', 'refresh'])

const headers = [
  { title: 'ID', key: 'scheduleID', sortable: false },
  { title: 'Advisee', key: 'advisee', sortable: false },
  { title: 'Term', key: 'term', sortable: false },
  { title: 'Status', key: 'status' },
  { title: 'Classes', key: 'classCount', align: 'end' },
  { title: 'Created', key: 'createdWhen' },
]

const tableItems = computed(() =>
  props.items.map((item) => ({
    ...item,
    advisee: item.adviseeName || `Advisee ${item.adviseeID}`,
    term: item.termName || item.termCode || item.termID || '—',
    createdWhen: item.createdWhen,
    raw: item,
  }))
)

const isSelected = (item) => {
  const id = item?.raw?.scheduleID ?? item?.scheduleID
  return props.selectedId != null && Number(id) === Number(props.selectedId)
}

const handleRowClick = (_, row) => {
  const schedule = row?.item?.raw || row?.item
  if (schedule?.scheduleID) {
    emit('select', Number(schedule.scheduleID))
  }
}

const statusColor = (status) => {
  const map = {
    DRAFT: 'grey',
    APPROVED: 'green',
    REJECTED: 'error',
  }
  return map[status] || 'primary'
}

const formatTimestamp = (value) => {
  if (!value) return 'n/a'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
</script>

<style scoped>
.selected-item {
  background-color: color-mix(in srgb, var(--v-theme-primary) 12%, transparent);
}
</style>
