<template>
  <v-app-bar flat elevate-on-scroll style="background-color:#ccccc6;">
    <!-- Logo + Title -->
    <v-app-bar-title class="d-flex align-center">
      <v-img
        src="@/assets/mockup/Logo.png"
        alt="logo"
        max-width="40"
        class="mr-3"
      />
      <span>Advise Me</span>
    </v-app-bar-title>

    <v-spacer />

    <!-- Search -->
    <v-text-field
      hide-details
      dense
      placeholder="Search"
      append-inner-icon="mdi-magnify"
      style="max-width:320px"
      variant="outlined"
    />

    <!-- Notifications -->
    <v-btn icon>
      <v-icon>mdi-bell</v-icon>
    </v-btn>

    <!-- User menu with sign out -->
    <v-menu>
      <template #activator="{ props }">
        <v-btn v-bind="props" variant="text" class="d-flex align-center">
          <v-avatar size="40" class="mr-2">
            <img
              src="@/assets/mockup/Avatar.png"
              style="width:100%; height:100%; object-fit:cover; border-radius:50%;"
            />
          </v-avatar>
          <span class="mr-1">Jordan</span>
          <v-icon>mdi-menu-down</v-icon>
        </v-btn>
      </template>

      <v-list>
        <v-list-item>Profile</v-list-item>
        <v-list-item>Settings</v-list-item>
        <v-list-item @click="$emit('logout')">
          <v-icon start>mdi-logout</v-icon>
          <span>Sign out</span>
        </v-list-item>
      </v-list>
    </v-menu>

    <!-- Optional: a visible Logout button outside the menu -->
    <!--
    <v-btn
      variant="text"
      color="primary"
      @click="$emit('logout')"
      class="text-capitalize ml-2"
    >
      <v-icon start>mdi-logout</v-icon>
      Logout
    </v-btn>
    -->
  </v-app-bar>
</template>

<script>
export default {
  name: "AppNavbar",
};
</script>
