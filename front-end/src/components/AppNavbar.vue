<template>
  <v-app-bar flat elevate-on-scroll style="background-color:#ccccc6;">
    <v-btn
      icon
      variant="text"
      class="mr-2"
      @click="toggleSidebar"
    >
      <v-icon>mdi-menu</v-icon>
    </v-btn>
    <v-app-bar-title class="d-flex align-center">
      <span>AdviseMe™</span>
    </v-app-bar-title>

    <v-spacer />

    <v-menu>
      <template #activator="{ props }">
        <v-btn v-bind="props" variant="text" class="d-flex align-center">
          <v-avatar size="48" class="mb-2">
            <img
              src="/src/assets/mockup/Avatar.png"
              style="width:100%; height:100%; object-fit:cover; border-radius:50%;"
            />
          </v-avatar>
          <span>{{ userLabel }}</span>
          <v-icon>mdi-menu-down</v-icon>
        </v-btn>
      </template>

      <v-list>
        <v-list-item class="logout-item" @click="handleLogout">
          <template #prepend>
            <v-icon color="red">mdi-logout</v-icon>
          </template>
          <v-list-item-title class="text-red">Sign out</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-menu>
  </v-app-bar>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from "vue";
import { useRouter } from "vue-router";
import { AUTH_ROLE_EVENT } from "@/composables/useUserRole";
import { useCurrentUser } from "@/composables/useCurrentUser";
import { useLayoutStore } from "@/stores/layout";
import { logout } from "@/services/auth.js";

const router = useRouter();
const { displayName, username, refreshIdentity } = useCurrentUser();
const layoutStore = useLayoutStore();
const userLabel = computed(() => displayName.value || username.value || "User");
const toggleSidebar = () => layoutStore.toggleSidebar();

const handleIdentityChange = (event) => {
  if (
    event?.type === "storage" &&
    event?.key &&
    event.key !== "auth_user" &&
    event.key !== "auth_token"
  ) {
    return;
  }
  refreshIdentity();
};

onMounted(() => {
  refreshIdentity();
  if (typeof window !== "undefined") {
    window.addEventListener("storage", handleIdentityChange);
    window.addEventListener(AUTH_ROLE_EVENT, handleIdentityChange);
  }
});

onBeforeUnmount(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("storage", handleIdentityChange);
    window.removeEventListener(AUTH_ROLE_EVENT, handleIdentityChange);
  }
});

function handleLogout() {
  logout(); // clear localStorage or JWT
  router.push({ name: "login" }); // redirect to login
}
</script>

<style scoped>
.text-red {
  color: #b71c1c !important;
}
.logout-item {
  justify-content: flex-start;
}
</style>
