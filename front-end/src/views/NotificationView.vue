<template>
  <v-app>
    <AppNavbar />
    <v-main class="d-flex">
      <AppSidebar :role="role" />
      <v-container fluid style="flex:1; padding-top: 24px;">
        <h2 class="text-h4 mb-4">You're in the {{ tabName }} tab</h2>

        <v-row dense>
          <v-col cols="12" sm="6" md="4" v-for="card in cards" :key="card.title">
            <DashboardCard
              :title="card.title"
              :value="card.value"
              :icon="card.icon"
              :footer="card.footer"
            />
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import AppNavbar from '@/components/AppNavbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import DashboardCard from '@/components/DashboardCard.vue'

const role = 'advisor'

const cards = [
  { title: 'Metric 1', value: 13, icon: 'mdi-chart-line', footer: 'Updated today' },
  { title: 'Metric 2', value: 456, icon: 'mdi-chart-bar', footer: 'Updated today' },
  { title: 'Metric 3', value: 789, icon: 'mdi-chart-pie', footer: 'Updated today' },
  { title: 'Metric 4', value: 789, icon: 'mdi-chart-pie', footer: 'Updated today' },
]

defineProps({
  tabName: String
})
</script>
