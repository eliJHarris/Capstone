<template>
  <div class="py-6">
    <h2 class="text-h4 mb-4">Welcome back, Jordan</h2>

    <v-row dense>
      <v-col
        v-for="card in cards"
        :key="card.title"
        cols="12"
        sm="6"
        md="4"
      >
        <DashboardCard
          :title="card.title"
          :value="card.value"
          :icon="card.icon"
          :footer="card.footer"
        />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import DashboardCard from '@/components/DashboardCard.vue'

const cards = [
  { title: 'Active Schedules', value: 8, icon: 'mdi-calendar-check', footer: 'Across all advisees' },
  { title: 'Pending Approvals', value: 3, icon: 'mdi-alert-circle', footer: 'Awaiting advisor review' },
  { title: 'Completed Scrapes', value: 14, icon: 'mdi-file-document', footer: 'Last updated today' },
]
</script>
