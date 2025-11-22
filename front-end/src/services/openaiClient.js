import { apiFetch } from './apiClient'

export async function requestChatCompletion(prompt) {
  if (!prompt || !prompt.trim()) {
    throw new Error('Prompt is required for chat completion')
  }

  return apiFetch('/openai/chat', {
    method: 'POST',
    body: { prompt },
  })
}
