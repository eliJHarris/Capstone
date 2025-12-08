<template>
  <v-app>
    <v-main class="landing-main">
      <v-container class="landing-container">

        <h1 class="text-h3 mb-2">Advise Me</h1>

        <p class="landing-text mb-6" v-html="displayedText"></p>

        <v-btn color="black" dark @click="$router.push('/login')">
          Log In
        </v-btn>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const fullText = `Advise Me brings students and advisors
together on one platform. From smart
scheduling to real-time updates, everything
you need to stay on track is in one place.`;

const displayedText = ref('');

onMounted(() => {
  let i = 0;
  const speed = 40;

  function typeWriter() {
    if (i < fullText.length) {
      let char = fullText[i];
      if (char === '\n') {
        displayedText.value += '<br>'; 
        displayedText.value += char;
      }
      i++;
      setTimeout(typeWriter, speed);
    }
  }

  typeWriter();
});
</script>

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
  min-height: 100px;
  position: relative;
  white-space: pre-wrap;
}

/* blinking cursor */
.landing-text::after {
  content: '|';
  display: inline-block;
  margin-left: 2px;
  animation: blink 0.7s infinite;
  color: black;
}

@keyframes blink {
  0%, 50%, 100% { opacity: 1; }
  25%, 75% { opacity: 0; }
}
</style>
