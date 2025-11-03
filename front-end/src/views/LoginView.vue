<template>
  <v-app>
    <v-main
      class="d-flex align-center justify-center"
      style="min-height: 100vh; background-color: #e6e5e1;"
    >
      <v-container max-width="420">
        <v-card elevation="8" class="pa-6" rounded="xl">
          <v-img
            src="@/assets/mockup/Logo.png"
            alt="Logo"
            contain
            width="120"
            class="mx-auto mb-6"
          />

          <v-text-field
            v-model="email"
            label="Email"
            variant="outlined"
            prepend-inner-icon="mdi-email"
            class="mb-4"
          />

          <v-text-field
            v-model="password"
            label="Password"
            type="password"
            variant="outlined"
            prepend-inner-icon="mdi-lock"
            class="mb-4"
          />

          <v-btn
            block
            color="primary"
            size="large"
            class="mb-3"
            @click="goToDashboard"
          >
            LOGIN
          </v-btn>

          
          <div class="text-center mb-4">
            <v-btn
              variant="text"
              color="primary"
              size="small"
              class="text-capitalize"
              @click="forgotPassword"
            >
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const email = ref('')
const password = ref('')

function goToDashboard() {
  router.push('/dashboard')
}

function forgotPassword() {
  alert('Password reset functionality not yet implemented.')
}
</script>
