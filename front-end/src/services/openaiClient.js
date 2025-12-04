import { apiFetch } from './apiClient'

export async function requestChatCompletion({
  prompt,
  adviseeId,
  scheduleId,
  requesterRole,
  history = [],
} = {}) {
  if (!prompt || !String(prompt).trim()) {
    throw new Error('Prompt is required for chat completion')
  }

  return apiFetch('/openai/chat', {
    method: 'POST',
    body: {
      prompt,
      advisee_id: adviseeId,
      schedule_id: scheduleId,
      requester_role: requesterRole,
      history,
    },
  })
}
