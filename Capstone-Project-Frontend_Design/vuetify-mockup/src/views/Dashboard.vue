<template>
  <v-app>
    <AppNavbar @logout="handleLogout" />
    <v-main class="d-flex">
      <AppSidebar :role="role" />
      <v-container fluid style="flex:1;">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { useRouter } from "vue-router";
import AppNavbar from "@/components/AppNavbar.vue";
import AppSidebar from "@/components/AppSidebar.vue";
import { logout } from "@/services/auth.js";

const router = useRouter();
const role = "advisor";

function handleLogout() {
  logout();
  router.push({ name: "login" });
}
</script>
