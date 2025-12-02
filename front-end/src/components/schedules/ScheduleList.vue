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

    <v-divider />

    <v-list v-if="items.length" lines="two">
      <v-list-item
        v-for="schedule in items"
        :key="schedule.scheduleID"
        :value="schedule.scheduleID"
        :class="{
          'selected-item': schedule.scheduleID === selectedId,
        }"
        @click="$emit('select', schedule.scheduleID)"
      >
        <template #prepend>
          <v-avatar color="primary">
            <span class="text-body-2 font-weight-medium">
              {{ schedule.termName || schedule.termCode || schedule.termID }}
            </span>
          </v-avatar>
        </template>
        <v-list-item-title class="font-weight-medium">
          Schedule #{{ schedule.scheduleID }}
        </v-list-item-title>
        <v-list-item-subtitle>
          {{ schedule.adviseeName || `Advisee ${schedule.adviseeID}` }} • Created
          {{ formatTimestamp(schedule.createdWhen) }}
        </v-list-item-subtitle>
        <template #append>
          <div class="d-flex flex-column align-end ga-2">
            <v-chip
              size="small"
              :color="statusColor(schedule.status)"
              variant="tonal"
            >
              {{ schedule.status }}
            </v-chip>
            <span class="text-caption text-medium-emphasis">
              {{ schedule.classCount }} classes
            </span>
          </div>
        </template>
      </v-list-item>
    </v-list>

    <div v-else-if="!loading" class="pa-6 text-body-2 text-medium-emphasis">
      No schedules found. Adjust filters or create a new schedule to get started.
    </div>

    <v-progress-linear
      v-if="loading"
      indeterminate
      color="primary"
    />
  </v-card>
</template>

<script setup>
defineProps({
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

defineEmits(['select', 'refresh'])

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
