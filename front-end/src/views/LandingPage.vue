<template>
  <v-app>
    <v-main class="landing-main">
      <v-container class="landing-container">

        
        <h1 class="text-h3 mb-2">Advise Me</h1>

   
        <p class="landing-text mb-6">
          Advise Me brings students and advisors<br>
          together on one platform. From smart<br>
          scheduling to real-time updates, everything<br>
          you need to stay on track is in one place.
        </p>

        <v-btn color="black" dark @click="$router.push('/login')">
          Log In
        </v-btn>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup></script>

<style scoped>

.landing-main {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
}


.landing-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.landing-text {
  line-height: 1.3;
  max-width: 400px;
}
</style>
