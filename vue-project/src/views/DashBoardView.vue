<template>
  <div>
    <!-- Conditionally render dashboards -->
    <AdvisorDashboard v-if="userType === 'advisor'" />
    <StudentDashboard v-else-if="userType === 'student'" />
  </div>
</template>

<script>
import { useUserStore } from '../store'
import AdvisorDashboard from '../components/AdvisorDashboard.vue'
import StudentDashboard from '../components/StudentDashboard.vue'

export default {
  setup() {
    const userStore = useUserStore()
    return { userType: userStore.userType }
  },
}
</script>

<style scoped>
/* optional styling */
</style>
