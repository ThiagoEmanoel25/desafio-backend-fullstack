import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { ApiError } from '../api/client'
import { streamChatMessage } from '../api/chat'
import type { Task } from '../types'

interface ChatPanelProps {
  onTaskCreated: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

interface Message {
  role: 'user' | 'agent'
  text: string
}

const UNAVAILABLE = 'O assistente está indisponível agora.'

export default function ChatPanel({ onTaskCreated, onApiError }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const logRef = useRef<HTMLUListElement>(null)

  // Keep the newest message visible while the reply streams in.
  useEffect(() => {
    const log = logRef.current
    if (log) log.scrollTop = log.scrollHeight
  }, [messages])

  // Replace the text of the last (agent) bubble.
  function setAgentText(update: (text: string) => string) {
    setMessages((m) => {
      const last = m[m.length - 1]
      return [...m.slice(0, -1), { ...last, text: update(last.text) }]
    })
  }

  async function handleSubmit(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault()
    const text = input.trim()
    if (!text || thinking) return
    setMessages((m) => [...m, { role: 'user', text }, { role: 'agent', text: '' }])
    setInput('')
    setError(null)
    setThinking(true)
    let failed = false
    let finished = false
    try {
      await streamChatMessage(text, conversationId, (ev) => {
        if (ev.type === 'meta') setConversationId(ev.conversation_id)
        else if (ev.type === 'delta') {
          setStreaming(true)
          setAgentText((t) => t + ev.text)
        } else if (ev.type === 'done') {
          finished = true
          setConversationId(ev.conversation_id)
          setAgentText(() => ev.reply)
          if (ev.created_task) onTaskCreated(ev.created_task)
        } else {
          failed = true
          setError(UNAVAILABLE)
        }
      })
      // The connection closed without `done` or `error`: the reply is incomplete.
      if (!finished && !failed) {
        failed = true
        setError(UNAVAILABLE)
      }
    } catch (err) {
      failed = true
      if (onApiError(err)) return
      setError(
        err instanceof ApiError && err.status === 503
          ? UNAVAILABLE
          : 'Não foi possível falar com o assistente.',
      )
    } finally {
      // Drop an agent bubble left empty by a failure.
      if (failed) setMessages((m) => (m[m.length - 1]?.text ? m : m.slice(0, -1)))
      setThinking(false)
      setStreaming(false)
    }
  }

  // Enter sends; Shift+Enter (or an IME composition) inserts a line break.
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      void handleSubmit()
    }
  }

  function newConversation() {
    setConversationId(null)
    setMessages([])
    setError(null)
  }

  return (
    <aside className="card stack chat">
      <div className="section-head">
        <h2>Assistente IA</h2>
        <button
          type="button"
          className="secondary"
          onClick={newConversation}
          disabled={thinking || messages.length === 0}
        >
          Nova conversa
        </button>
      </div>
      <p className="muted hint">
        Ex.: “Cadastre uma tarefa urgente chamada ‘Revisar relatório financeiro’ para o
        departamento Comercial” ou “Quais tarefas urgentes eu tenho?”
      </p>
      <ul ref={logRef} className="chat-log" aria-live="polite">
        {messages.map((m, i) =>
          m.text ? (
            <li key={i} className={`bubble ${m.role}`}>
              <span className="sr-only">{m.role === 'user' ? 'Você: ' : 'Assistente: '}</span>
              {m.text}
            </li>
          ) : null,
        )}
        {thinking && !streaming && (
          <li className="bubble agent typing">
            <span className="dots" aria-hidden="true" />
            digitando…
          </li>
        )}
      </ul>
      {error && <p className="error" role="alert">{error}</p>}
      <form onSubmit={handleSubmit} className="stack">
        <textarea
          aria-label="Mensagem para o assistente"
          placeholder="Escreva uma mensagem"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <small className="muted">Enter envia · Shift+Enter quebra a linha</small>
        <button type="submit" disabled={thinking || !input.trim()}>
          {thinking ? 'Respondendo…' : 'Enviar'}
        </button>
      </form>
    </aside>
  )
}
