import { API_URL, ApiError, apiFetch, tokenStorage } from './client'
import type { ChatResponse, ChatStreamEvent } from '../types'

// No trailing slash: /v1/chat is served at exactly this path.
export async function sendChatMessage(
  message: string,
  conversationId: string | null,
): Promise<ChatResponse> {
  return apiFetch<ChatResponse>('/v1/chat', {
    method: 'POST',
    body: JSON.stringify({ message, conversation_id: conversationId }),
  })
}

// POST /v1/chat/stream answers Server-Sent Events (`data: <json>\n\n`).
// EventSource cannot POST nor send Authorization, so read the body by hand.
export async function streamChatMessage(
  message: string,
  conversationId: string | null,
  onEvent: (event: ChatStreamEvent) => void,
): Promise<void> {
  const headers = new Headers({ 'Content-Type': 'application/json' })
  const token = tokenStorage.get()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_URL}/v1/chat/stream`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, conversation_id: conversationId }),
  })
  if (!response.ok || !response.body) {
    const body = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const detail = typeof body?.detail === 'string' ? body.detail : response.statusText
    throw new ApiError(response.status, detail)
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += value
    const frames = buffer.split('\n\n')
    buffer = frames.pop() ?? ''
    for (const frame of frames) {
      const data = frame
        .split('\n')
        .filter((line) => line.startsWith('data: '))
        .map((line) => line.slice(6))
        .join('\n')
      if (data) onEvent(JSON.parse(data) as ChatStreamEvent)
    }
  }
}
