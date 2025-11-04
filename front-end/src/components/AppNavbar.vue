<template>
  <v-app-bar flat elevate-on-scroll style="background-color:#ccccc6;">
    <v-app-bar-title class="d-flex align-center">
      <v-img
        src="/src/assets/mockup/Logo.png"
        alt="logo"
        max-width="40"
        class="mr-3"
      />
      <span>Advise Me</span>
    </v-app-bar-title>

    <v-spacer />

    <v-text-field
      hide-details
      dense
      placeholder="Search"
      append-inner-icon="mdi-magnify"
      style="max-width:320px"
    />

    <v-btn icon>
      <v-icon>mdi-bell</v-icon>
    </v-btn>

    <v-menu>
      <template #activator="{ props }">
        <v-btn v-bind="props" variant="text" class="d-flex align-center">
          <v-avatar size="48" class="mb-2">
            <img
              src="/src/assets/mockup/Avatar.png"
              style="width:100%; height:100%; object-fit:cover; border-radius:50%;"
            />
          </v-avatar>
          <span>Jordan</span>
          <v-icon>mdi-menu-down</v-icon>
        </v-btn>
      </template>

      <v-list>
        <v-list-item>Profile</v-list-item>
        <v-list-item>Settings</v-list-item>
        <v-list-item @click="handleLogout" class="text-red">
          <v-icon start color="red">mdi-logout</v-icon>
          <span>Sign out</span>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-app-bar>
</template>

<script setup>
import { useRouter } from "vue-router";
import { logout } from "@/services/auth.js";

const router = useRouter();

function handleLogout() {
  logout(); // clear localStorage or JWT
  router.push({ name: "login" }); // redirect to login
}
</script>

<style scoped>
.text-red {
  color: #b71c1c !important;
}
</style>
