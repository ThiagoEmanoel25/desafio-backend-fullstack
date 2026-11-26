import { apiFetch } from './client'
import type { ChatResponse } from '../types'

// No trailing slash: /v1/chat is served at exactly this path.
export async function sendChatMessage(message: string): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/v1/chat', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}
