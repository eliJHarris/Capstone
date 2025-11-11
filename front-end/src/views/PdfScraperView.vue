<template>
  <div class="py-6">
    <div class="d-flex align-center mb-4">
      <div>
        <h1 class="text-h4 mb-1">WIP SUBJECT TO CHANGE</h1>
        <h2 class="text-h4 mb-1">PDF Scraper</h2>
        <p class="text-body-2 text-medium-emphasis">
          Trigger the FastAPI PDF scraper and inspect its output without leaving the UI.
        </p>
      </div>
      <v-spacer />
      <v-btn
        variant="text"
        :disabled="store.loading"
        @click="prefillExample"
      >
        Use Sample Config
      </v-btn>
    </div>

    <v-alert
      v-if="store.error"
      type="error"
      class="mb-4"
      closable
      @click:close="store.clearError()"
    >
      {{ store.error }}
    </v-alert>

    <v-row dense>
      <v-col cols="12" md="6">
        <v-card rounded="xl" variant="flat">
          <v-card-title>Scraper configuration</v-card-title>
          <v-card-text>
            <v-form @submit.prevent="runScraper">
              <v-text-field
                v-model="store.form.startUrl"
                label="Start URL"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                placeholder="https://example.edu/catalog"
                required
              />
              <v-text-field
                v-model="store.form.outputPath"
                label="Output path (optional)"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                placeholder="scrapes/catalog.txt"
              />
              <v-combobox
                v-model="keywordModel"
                label="Required keywords"
                density="comfortable"
                variant="outlined"
                class="mb-3"
                multiple
                chips
                closable-chips
              />
              <v-row dense class="mb-3">
                <v-col cols="12" sm="4">
                  <v-text-field
                    v-model="store.form.maxPages"
                    label="Max pages"
                    type="number"
                    density="comfortable"
                    variant="outlined"
                    min="1"
                  />
                </v-col>
                <v-col cols="12" sm="4">
                  <v-text-field
                    v-model="store.form.delay"
                    label="Delay (s)"
                    type="number"
                    step="0.5"
                    density="comfortable"
                    variant="outlined"
                    min="0"
                  />
                </v-col>
                <v-col cols="12" sm="4">
                  <v-text-field
                    v-model="store.form.timeout"
                    label="Timeout (s)"
                    type="number"
                    density="comfortable"
                    variant="outlined"
                    min="1"
                  />
                </v-col>
              </v-row>
              <v-switch
                v-model="store.form.verbose"
                color="primary"
                label="Verbose logging"
                class="mb-4"
              />

              <v-btn
                type="submit"
                color="primary"
                block
                :loading="store.loading"
              >
                Run Scraper
              </v-btn>
              <v-btn
                type="button"
                variant="tonal"
                block
                class="mt-2"
                :disabled="store.loading"
                @click="resetForm"
              >
                Reset
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-card rounded="xl" variant="flat">
          <v-card-title>Latest run details</v-card-title>
          <v-card-text v-if="store.lastResult">
            <div class="d-flex align-center mb-4">
              <v-chip
                :color="store.lastResult.success ? 'success' : 'error'"
                variant="tonal"
                class="mr-3"
              >
                {{ store.lastResult.success ? 'Success' : 'Failed' }}
              </v-chip>
              <span class="text-body-2 text-medium-emphasis">
                Exit code {{ store.lastResult.exit_code }} •
                {{ formatDuration(store.lastResult.duration_seconds) }}
              </span>
            </div>

            <v-list density="compact">
              <v-list-item>
                <v-list-item-title>Output file</v-list-item-title>
                <v-list-item-subtitle>{{ store.lastResult.output_path }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Stdout bytes</v-list-item-title>
                <v-list-item-subtitle>{{ store.lastResult.stdout.length }}</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <v-list-item-title>Stderr bytes</v-list-item-title>
                <v-list-item-subtitle>{{ store.lastResult.stderr.length }}</v-list-item-subtitle>
              </v-list-item>
            </v-list>

            <v-expansion-panels class="mt-4">
              <v-expansion-panel title="Standard output">
                <v-expansion-panel-text>
                  <v-textarea
                    :model-value="store.lastResult.stdout || 'No stdout captured.'"
                    readonly
                    auto-grow
                    rows="5"
                    class="font-mono"
                  />
                </v-expansion-panel-text>
              </v-expansion-panel>
              <v-expansion-panel title="Standard error">
                <v-expansion-panel-text>
                  <v-textarea
                    :model-value="store.lastResult.stderr || 'No stderr captured.'"
                    readonly
                    auto-grow
                    rows="5"
                    class="font-mono"
                  />
                </v-expansion-panel-text>
              </v-expansion-panel>
            </v-expansion-panels>
          </v-card-text>
          <v-card-text v-else class="text-medium-emphasis">
            Run the scraper to see output and diagnostics here.
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar
      v-model="feedback.show"
      :color="feedback.color"
      timeout="3000"
      location="bottom right"
    >
      {{ feedback.text }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { usePdfScraperStore } from '@/stores/pdfScraper'

const store = usePdfScraperStore()
const feedback = ref({
  show: false,
  text: '',
  color: 'success',
})

const keywordModel = computed({
  get() {
    const value = store.form.requireKeywords
    if (Array.isArray(value)) {
      return value
    }
    if (typeof value === 'string' && value.length) {
      return value.split(',').map((word) => word.trim()).filter(Boolean)
    }
    return []
  },
  set(value) {
    store.setForm({ requireKeywords: value })
  },
})

const showFeedback = (text, color = 'success') => {
  feedback.value = { show: true, text, color }
}

const runScraper = async () => {
  try {
    await store.runScraper()
    showFeedback('Scraper completed')
  } catch (err) {
    showFeedback(err.message || 'Failed to run scraper', 'error')
  }
}

const formatDuration = (seconds) => {
  if (!seconds && seconds !== 0) return 'n/a'
  return `${seconds.toFixed(1)}s`
}

const resetForm = () => {
  store.resetForm()
}

const prefillExample = () => {
  store.setForm({
    startUrl: 'uafs.edu',
    outputPath: 'uafs.txt',
    maxPages: 10,
    delay: 0.5,
    timeout: 20,
    verbose: true,
    requireKeywords: [],
  })
}
</script>

<style scoped>
.font-mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
</style>
