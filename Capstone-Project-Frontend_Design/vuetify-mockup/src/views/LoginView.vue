<template>
  <v-app>
    <v-main class="d-flex align-center justify-center" style="min-height: 100vh; background-color: #e6e5e1;">
      <v-container max-width="420">
        <v-card elevation="8" class="pa-6" rounded="xl">
          <v-img
            src="@/assets/mockup/Logo.png"
            alt="Logo"
            contain
            width="120"
            class="mx-auto mb-6"
          />

          <v-alert
            v-if="errorMsg"
            type="error"
            variant="tonal"
            class="mb-4"
            density="compact"
          >
            {{ errorMsg }}
          </v-alert>

          <v-form @submit.prevent="handleLogin">
            <v-text-field
              v-model="username"
              label="Username"
              variant="outlined"
              prepend-inner-icon="mdi-account"
              class="mb-4"
              autocomplete="username"
            />

            <v-text-field
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              label="Password"
              variant="outlined"
              prepend-inner-icon="mdi-lock"
              :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
              @click:append-inner="showPassword = !showPassword"
              class="mb-4"
              autocomplete="current-password"
            />

            <v-btn
              type="submit"
              block
              color="primary"
              size="large"
              class="mb-3"
              :loading="loading"
            >
              LOGIN
            </v-btn>
          </v-form>

          <div class="text-center mb-4">
            <v-btn variant="text" color="primary" size="small" class="text-capitalize" @click="forgotPassword">
              Forgot Password?
            </v-btn>
          </div>

          <div class="text-body-2 text-center" style="color: #6C6B67;">
            Need an account?
            <v-btn variant="text" color="primary" size="small">Sign Up</v-btn>
          </div>
        </v-card>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
// If "@/services/auth.js" alias fails, use "../services/auth.js"
import { loginRequest } from "@/services/auth.js";

const router = useRouter();

const username = ref("");
const password = ref("");
const showPassword = ref(false);
const loading = ref(false);
const errorMsg = ref("");

function forgotPassword() {
  // TODO: route or dialog
  console.log("Forgot password clicked");
}

async function handleLogin() {
  errorMsg.value = "";
  loading.value = true;
  try {
    // For your LDAP demo users: aadvisor / AdvisorPass123!
    await loginRequest(username.value, password.value);
    router.push({ name: "dashboard" });
  } catch (err) {
    console.error(err);
    errorMsg.value = err?.message || "Login failed";
  } finally {
    loading.value = false;
  }
}
</script>
