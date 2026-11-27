import { useId, useRef, useState, type KeyboardEvent } from 'react'
import { flushSync } from 'react-dom'
import type { Task } from '../types'
import ChatPanel from './ChatPanel'

interface ChatPopupProps {
  onTaskCreated: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

/**
 * Floating "Assistente IA" button that opens the chat in a non-modal popup.
 * Closing only hides the panel: ChatPanel stays mounted, so the conversation, a reply
 * still streaming and the tasks it creates survive while it is closed.
 */
export default function ChatPopup({ onTaskCreated, onApiError }: ChatPopupProps) {
  const [open, setOpen] = useState(false)
  const [unread, setUnread] = useState(false)
  // Read when a reply ends, not when it started: the user may close the popup meanwhile.
  const openRef = useRef(false)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const panelId = useId()
  const titleId = useId()

  function show() {
    openRef.current = true
    setOpen(true)
    setUnread(false)
  }

  function hide() {
    openRef.current = false
    // Commit first: on phones the button is hidden while the panel is open.
    flushSync(() => setOpen(false))
    buttonRef.current?.focus()
  }

  // Bound to the panel, so Esc only closes it while the focus is inside.
  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === 'Escape' && !event.nativeEvent.isComposing) hide()
  }

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        className="chat-fab"
        aria-expanded={open}
        aria-controls={panelId}
        onClick={open ? hide : show}
      >
        <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false">
          <path
            d="M5 4h14a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-6l-5 4v-4H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <path d="M12 7l1 2.5 2.5 1-2.5 1-1 2.5-1-2.5-2.5-1 2.5-1z" fill="currentColor" />
        </svg>
        {/* The space keeps the name "Assistente IA nova resposta" (each span's text is trimmed). */}
        <span className="chat-fab-label">Assistente IA</span>{' '}
        {unread && (
          <span className="chat-fab-dot">
            <span className="sr-only">nova resposta</span>
          </span>
        )}
      </button>
      {/* Announces a reply that arrived while the panel (and its live log) was hidden. */}
      <p className="sr-only" role="status">
        {unread ? 'Nova resposta do assistente.' : ''}
      </p>
      <div
        id={panelId}
        className="chat-popup"
        role="dialog"
        aria-labelledby={titleId}
        hidden={!open}
        onKeyDown={handleKeyDown}
      >
        <ChatPanel
          open={open}
          titleId={titleId}
          onClose={hide}
          onReply={() => {
            if (!openRef.current) setUnread(true)
          }}
          onTaskCreated={onTaskCreated}
          onApiError={onApiError}
        />
      </div>
    </>
  )
}
