<template>
  <div>
    
    <v-tooltip :text="fabTooltip" location="top">
      <template #activator="{ props }">
        <v-btn
          v-bind="props"
          :icon="fabIcon"
          color="primary"
          class="chat-bubble"
          size="large"
          elevation="12"
          @click="handleFabClick"
        />
      </template>
    </v-tooltip>

    
    <v-dialog
      v-model="chatOpen"
      width="400"
      transition="dialog-bottom-transition"
      scrim="transparent"
    >
      <v-card rounded="xl" elevation="8">
        <v-toolbar color="primary" dark flat>
          <v-toolbar-title>Assistant</v-toolbar-title>
          <v-spacer></v-spacer>
          <v-btn icon @click="chatOpen = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-card-text class="chat-window">
          <v-container fluid>
            <v-row
              v-for="(msg, i) in messages"
              :key="i"
              class="mb-2"
              no-gutters
            >
              <v-col :class="msg.sender === 'user' ? 'text-right' : 'text-left'">
              
                <v-chip
                  v-if="msg.sender === 'user'"
                  variant="tonal"
                  color="primary"
                  text-color="white"
                  class="pa-2"
                >
                  {{ msg.text }}
                </v-chip>

             
                <v-chip
                  v-else
                  variant="tonal"
                  color="surface-variant"
                  text-color="on-surface"
                  class="pa-2"
                >
                  {{ msg.text }}
                </v-chip>
              </v-col>
            </v-row>
          </v-container>
        </v-card-text>

        <v-divider />

        <v-card-actions class="px-4 py-3">
          <v-text-field
            v-model="input"
            placeholder="Type a message..."
            variant="outlined"
            hide-details
            density="comfortable"
            class="flex-grow-1"
            @keyup.enter="sendMessage"
          />
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const chatOpen = ref(false)
const input = ref('')
const messages = ref([])

onMounted(() => {
  messages.value.push({
    text: 'Hello! How can I help you today?',
    sender: 'bot',
  })
})

function sendMessage() {
  const text = input.value.trim()
  if (!text) return
  messages.value.push({ text, sender: 'user' })
  input.value = ''
  // Placeholder AI response
  setTimeout(() => {
    messages.value.push({
      text: 'AI integration coming soon...',
      sender: 'bot',
    })
  }, 400)
}

function handleFabClick() {
  if (chatOpen.value && input.value.trim()) {
    sendMessage()
  } else {
    chatOpen.value = !chatOpen.value
  }
}

const fabIcon = computed(() =>
  chatOpen.value && input.value.trim() ? 'mdi-send' : 'mdi-chat'
)
const fabTooltip = computed(() =>
  chatOpen.value && input.value.trim() ? 'Send message' : 'Chat with us'
)
</script>

<style scoped>
.chat-bubble {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 3000;
  box-shadow: 0 4px 14px rgba(255, 255, 255, 0.65);
  transition: all 0.3s ease;
  animation: pulse 2.2s ease-out 3;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.6);
  }
  70% {
    transform: scale(1.05);
    box-shadow: 0 0 20px 10px rgba(255, 255, 255, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(255, 255, 255, 0);
  }
}

.chat-window {
  height: 400px;
  overflow-y: auto;
  background-color: var(--v-theme-surface);
}
</style>
