<template>
  <div>
    <h2>Student Dashboard</h2>
    <DashboardTabs />
    <!-- Add student-specific content here -->
  </div>
</template>

<script>
import DashboardTabs from './DashboardTabs.vue'

export default {
  name: 'StudentDashboard',
  components: { DashboardTabs },
}
</script>

<style scoped>
/* optional student dashboard styles */
</style>
