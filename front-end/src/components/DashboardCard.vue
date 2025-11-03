<template>
  <v-card class="pa-4" elevation="2">
    <div class="d-flex justify-space-between align-center">
      <div>
        <div class="subtitle-2 text--secondary">{{ title }}</div>
        <div class="headline">{{ value }}</div>
      </div>
      <v-icon size="36">{{ icon }}</v-icon>
    </div>
    <div v-if="footer" class="caption mt-3">{{ footer }}</div>
  </v-card>
</template>

<script>
export default {
  name: 'DashboardCard',
  props: {
    title: String,
    value: [String, Number],
    icon: { type: String, default: 'mdi-chart-line' },
    footer: String
  }
}
</script>

<style scoped></style>
