import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { sendChatMessage } from '../api/chat'
import type { Task } from '../types'

interface ChatPanelProps {
  onTaskCreated: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

interface Message {
  role: 'user' | 'agent'
  text: string
}

export default function ChatPanel({ onTaskCreated, onApiError }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const text = input.trim()
    if (!text || thinking) return
    setMessages((m) => [...m, { role: 'user', text }])
    setInput('')
    setError(null)
    setThinking(true)
    try {
      const { reply, created_task } = await sendChatMessage(text)
      setMessages((m) => [...m, { role: 'agent', text: reply }])
      if (created_task) onTaskCreated(created_task)
    } catch (err) {
      if (onApiError(err)) return
      setError(
        err instanceof ApiError && err.status === 503
          ? 'O assistente está indisponível agora.'
          : 'Não foi possível falar com o assistente.',
      )
    } finally {
      setThinking(false)
    }
  }

  return (
    <aside className="card stack">
      <h2>Assistente IA</h2>
      <p className="muted">
        Ex.: “Cadastre uma tarefa urgente chamada ‘Revisar relatório financeiro’ para o
        departamento Comercial”
      </p>
      <ul className="chat-log">
        {messages.map((m, i) => (
          <li key={i} className={`bubble ${m.role}`}>
            {m.text}
          </li>
        ))}
        {thinking && <li className="muted">pensando…</li>}
      </ul>
      {error && <p className="error">{error}</p>}
      <form onSubmit={handleSubmit} className="stack">
        <textarea
          aria-label="Mensagem para o assistente"
          placeholder="Escreva uma mensagem"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" disabled={thinking || !input.trim()}>
          Enviar
        </button>
      </form>
    </aside>
  )
}
