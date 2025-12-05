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
      width="420"
      transition="dialog-bottom-transition"
      scrim="transparent"
    >
      <v-card rounded="xl" elevation="8">
        <v-toolbar color="primary" dark flat>
          <v-toolbar-title>Advisor Assistant</v-toolbar-title>
          <v-spacer />
          <v-btn icon @click="chatOpen = false">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-toolbar>

        <v-card-text class="chat-window">
          <div ref="chatScroll" class="chat-scroll">
            <v-container fluid class="pa-0">
              <v-row
                v-for="message in messages"
                :key="message.id"
                class="mb-2"
                no-gutters
              >
                <v-col :class="message.sender === 'user' ? 'text-right' : 'text-left'">
                  <v-sheet
                    :color="message.sender === 'user' ? 'primary' : 'surface-variant'"
                    rounded="xl"
                    border
                    :class="[
                      'chat-message',
                      message.sender === 'user' ? 'chat-message--user' : 'chat-message--bot',
                    ]"
                  >
                    <div class="chat-message__content">
                      <template v-if="message.loading">
                        <v-progress-circular size="18" indeterminate color="primary" class="mr-2" />
                        <span>Thinking...</span>
                      </template>
                      <template v-else>
                        {{ message.text }}
                      </template>
                    </div>
                  </v-sheet>
                </v-col>
              </v-row>
            </v-container>
            <v-alert
              v-if="errorMessage"
              class="mt-4"
              density="compact"
              type="error"
              variant="tonal"
            >
              {{ errorMessage }}
            </v-alert>
            <v-alert
              v-if="advisorNeedsSelection"
              class="mt-3"
              density="compact"
              type="warning"
              variant="tonal"
            >
              Advisors must select a student before chatting.
            </v-alert>
          </div>
        </v-card-text>

        <v-divider />

        <v-card-text v-if="!isStudentRole" class="px-4 pt-3 pb-0">
          <div class="d-flex align-center">
            <v-autocomplete
              v-model="selectedAdviseeOption"
              v-model:search="adviseeSearch"
              :items="adviseeOptions"
              :loading="adviseeLoading"
              :label="advisorNeedsSelection ? 'Select a student (required)' : 'Select a student'"
              item-title="title"
              item-value="value"
              hide-details
              variant="outlined"
              density="comfortable"
              class="flex-grow-1 mr-2"
              return-object
              clearable
              @update:search="handleAdviseeSearch"
            >
              <template #item="{ props, item }">
                <v-list-item v-bind="props">
                  <v-list-item-title>{{ item?.raw?.name || item?.raw?.title }}</v-list-item-title>
                  <v-list-item-subtitle>{{ item?.raw?.email || item?.raw?.major }}</v-list-item-subtitle>
                </v-list-item>
              </template>
            </v-autocomplete>
            <v-btn
              color="secondary"
              variant="tonal"
              :loading="manualAdviseeLoading"
              :disabled="manualAdviseeLoading || !selectedAdviseeOption"
              @click="applyManualAdvisee"
            >
              Load student
            </v-btn>
          </div>
          <div v-if="manualAdviseeError" class="text-caption text-error mt-1">
            {{ manualAdviseeError }}
          </div>
        </v-card-text>

        <v-card-actions class="px-4 py-3">
          <v-text-field
            v-model="input"
            :placeholder="advisorNeedsSelection ? 'Select a student to enable chat' : 'Ask about the degree plan...'"
            variant="outlined"
            hide-details
            density="comfortable"
            class="flex-grow-1"
            :disabled="isSending || advisorNeedsSelection"
            @keyup.enter="sendMessage"
          />
          <v-btn
            color="primary"
            :disabled="sendDisabled"
            @click="sendMessage"
          >
            Send
          </v-btn>
        </v-card-actions>
        <v-progress-linear v-if="isSending" indeterminate color="primary" />
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { storeToRefs } from 'pinia'

import { requestChatCompletion } from '@/services/openaiClient'
import { useScheduleStore } from '@/stores/schedules'
import { useDegreePlanStore } from '@/stores/degreePlans'
import { useCurrentUser } from '@/composables/useCurrentUser'
import { fetchAdvisees } from '@/services/advisees'

const scheduleStore = useScheduleStore()
const degreePlanStore = useDegreePlanStore()
const { selectedSchedule, selectedScheduleId } = storeToRefs(scheduleStore)
const { summary: degreeSummary } = storeToRefs(degreePlanStore)

const {
  advisee: currentAdvisee,
  loadUserContext,
  loading: userContextLoading,
  role,
} = useCurrentUser()

const chatOpen = ref(false)
const input = ref('')
const isSending = ref(false)
const errorMessage = ref('')
const chatScroll = ref(null)
const messages = ref([])
const selectedAdviseeOption = ref(null)
const adviseeSearch = ref('')
const adviseeOptions = ref([])
const manualAdviseeContextId = ref(null)
const manualAdviseeLoading = ref(false)
const manualAdviseeError = ref('')

let messageSeed = 0
const nextMessageId = () => {
  messageSeed += 1
  return messageSeed
}

const isStudentRole = computed(() => role.value === 'student')
const advisorNeedsSelection = computed(() => role.value === 'advisor' && !activeAdviseeId.value)
const sendDisabled = computed(
  () => isSending.value || !input.value.trim() || advisorNeedsSelection.value
)
const activeScheduleId = computed(
  () => selectedScheduleId.value || selectedSchedule.value?.scheduleID || null
)
const activeAdviseeId = computed(() => {
  return (
    manualAdviseeContextId.value ||
    selectedSchedule.value?.adviseeID ||
    currentAdvisee.value?.adviseeID ||
    null
  )
})

const normalizedContext = computed(() => {
  const advisee = currentAdvisee.value || {}
  const nameFromSchedule = selectedSchedule.value?.adviseeName
  const nameFallback = manualAdviseeContextId.value ? `Advisee ${manualAdviseeContextId.value}` : 'Student'
  const requirement = degreeSummary.value?.requirementSet
  return {
    student_name: advisee.name || nameFromSchedule || advisee.email || nameFallback,
    major:
      advisee.major ||
      requirement?.programName ||
      requirement?.programCode ||
      'Undeclared',
    advisor_name: advisee.advisorName || 'Advisor',
  }
})

const welcomeMessage = computed(
  () =>
    `Hi ${normalizedContext.value.student_name || 'there'}! I'm the AdviseMe academic advising assistant. ` +
    `How can I help you with your ${normalizedContext.value.major || 'degree plan'} today?`
)

const fabIcon = computed(() => {
  if (chatOpen.value && input.value.trim() && !isSending.value) {
    return 'mdi-send'
  }
  return 'mdi-chat-outline'
})

const fabTooltip = computed(() => {
  if (chatOpen.value && input.value.trim()) {
    return isSending.value ? 'Sending...' : 'Send message'
  }
  return 'Chat with AdviseMe'
})

onMounted(() => {
  if (!currentAdvisee.value && !userContextLoading.value) {
    loadUserContext().catch((err) => console.error('Failed to load user context for chat', err))
  }

  if (!isStudentRole.value) {
    fetchAdviseeMatches()
  }

  messages.value = [
    {
      id: nextMessageId(),
      text: welcomeMessage.value,
      sender: 'bot',
      isSystem: true,
    },
  ]
})

watch(activeAdviseeId, async (adviseeId) => {
  if (!adviseeId) return
  try {
    await degreePlanStore.loadSummary(adviseeId)
  } catch (err) {
    console.error('Failed to load degree summary for chat', err)
  }
})

async function fetchAdviseeMatches(search = '') {
  manualAdviseeError.value = ''
  adviseeLoadingState(true)
  try {
    const results = await fetchAdvisees({
      search: search || undefined,
      limit: 25,
    })
    adviseeOptions.value = (results || []).map((item) => ({
      value: item.adviseeID,
      title: item.name || item.email || `Advisee ${item.adviseeID}`,
      subtitle: item.major || item.email || '',
      raw: item,
    }))
  } catch (err) {
    manualAdviseeError.value = err?.message || 'Unable to load advisees'
  } finally {
    adviseeLoadingState(false)
  }
}

const adviseeLoading = ref(false)
function adviseeLoadingState(isLoading) {
  adviseeLoading.value = isLoading
}

function handleAdviseeSearch(term) {
  adviseeSearch.value = term
  fetchAdviseeMatches(term)
}

watch(
  () => normalizedContext.value,
  (ctx, prev) => {
    if (!prev || ctx.student_name !== prev.student_name || ctx.major !== prev.major) {
      messages.value = [
        {
          id: nextMessageId(),
          text: welcomeMessage.value,
          sender: 'bot',
          isSystem: true,
        },
      ]
    }
  },
  { deep: true }
)

watch(
  messages,
  () => {
    scrollToBottom()
  },
  { deep: true }
)

function scrollToBottom() {
  nextTick(() => {
    const el = chatScroll.value
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  })
}

function buildHistoryPayload() {
  return messages.value
    .filter((message) => !message.isSystem && !message.loading)
    .map((message) => ({
      sender: message.sender === 'user' ? 'user' : 'assistant',
      text: message.text,
    }))
}

async function applyManualAdvisee() {
  manualAdviseeError.value = ''
  const selected = selectedAdviseeOption.value
  const parsedId = selected?.value ? Number.parseInt(selected.value, 10) : null
  if (!parsedId) {
    manualAdviseeError.value = 'Select a student'
    return
  }

  manualAdviseeLoading.value = true
  try {
    await degreePlanStore.loadSummary(parsedId)
    manualAdviseeContextId.value = parsedId
  } catch (err) {
    manualAdviseeError.value = err?.message || 'Unable to load advisee context'
  } finally {
    manualAdviseeLoading.value = false
  }
}

async function sendMessage() {
  if (isSending.value) return
  if (advisorNeedsSelection.value) {
    errorMessage.value = 'Advisors must select a student before chatting.'
    return
  }

  const text = input.value.trim()
  if (!text) return

  errorMessage.value = ''
  const historyPayload = buildHistoryPayload()
  const userMessage = {
    id: nextMessageId(),
    sender: 'user',
    text,
  }
  messages.value.push(userMessage)
  input.value = ''
  isSending.value = true

  const thinkingMessage = {
    id: nextMessageId(),
    sender: 'bot',
    text: '',
    loading: true,
  }
  messages.value.push(thinkingMessage)

  try {
    const response = await requestChatCompletion({
      prompt: text,
      adviseeId: activeAdviseeId.value,
      scheduleId: activeScheduleId.value,
      requesterRole: role.value,
      history: historyPayload,
    })
    const content = response?.content?.trim()
    if (!content) {
      throw new Error('Assistant returned an empty response')
    }
    thinkingMessage.loading = false
    thinkingMessage.text = content
  } catch (error) {
    console.error('Failed to send chat message', error)
    errorMessage.value =
      error?.message ||
      'Unable to reach the advising assistant. Please try again in a few moments.'
    const fallbackText =
      'I encountered an issue reaching the advising assistant. Please retry in a moment or contact your advisor directly.'
    thinkingMessage.loading = false
    thinkingMessage.text = fallbackText
    thinkingMessage.isSystem = true
  } finally {
    isSending.value = false
  }
}

function handleFabClick() {
  if (chatOpen.value && input.value.trim() && !isSending.value) {
    sendMessage()
  } else {
    chatOpen.value = !chatOpen.value
  }
}
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
  height: 420px;
  background-color: var(--v-theme-surface);
  overflow: hidden;
}

.chat-scroll {
  height: 100%;
  overflow-y: auto;
  padding: 12px 12px 4px;
}

.chat-message {
  display: inline-flex;
  align-items: center;
  max-width: calc(100% - 32px);
  padding: 8px 12px;
  border-color: transparent !important;
  box-shadow: none;
}

.chat-message--user {
  color: white;
}

.chat-message--bot {
  color: var(--v-theme-on-surface);
}

.chat-message__content {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
  text-align: left;
}
</style>
