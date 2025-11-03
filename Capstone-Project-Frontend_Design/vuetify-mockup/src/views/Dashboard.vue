<template>
  <v-app>
    <AppNavbar />
    <v-main class="d-flex">
      <AppSidebar :role="role" />
      <v-container fluid style="flex:1;">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import AppNavbar from '@/components/AppNavbar.vue'
import AppSidebar from '@/components/AppSidebar.vue'

// Change between 'advisor' or 'student'
const role = 'advisor'
</script>

<style scoped>
.v-main {
  padding-top: 64px;
}
</style>
