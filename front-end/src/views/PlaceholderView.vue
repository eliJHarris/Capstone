<template>
  <div class="py-6">
    <h2 class="text-h4 mb-2">{{ title }}</h2>
    <p class="text-body-2" v-if="description">
      {{ description }}
    </p>
    <v-alert
      v-else
      type="info"
      variant="tonal"
      border="start"
      class="mt-4"
    >
      This section is coming soon.
    </v-alert>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  description: {
    type: String,
    default: '',
  },
})
</script>
