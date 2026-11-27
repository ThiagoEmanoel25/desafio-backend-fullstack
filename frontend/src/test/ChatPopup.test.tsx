import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { streamChatMessage } from '../api/chat'
import ChatPopup from '../components/ChatPopup'
import type { ChatStreamEvent, Task } from '../types'

vi.mock('../api/chat')

type DoneEvent = Extract<ChatStreamEvent, { type: 'done' }>

// Simulates the SSE stream: meta and a delta at once, then `done`. With `hold`, `done`
// waits until the returned function is called, so the test can close the popup first.
function mockStream(done: DoneEvent, { hold = false } = {}) {
  let release = () => {}
  const gate = new Promise<void>((resolve) => {
    release = resolve
    if (!hold) resolve()
  })
  vi.mocked(streamChatMessage).mockImplementation(async (_message, _conversationId, onEvent) => {
    onEvent({ type: 'meta', conversation_id: done.conversation_id })
    onEvent({ type: 'delta', text: 'Um momento' })
    await gate
    onEvent(done)
  })
  return () => act(async () => release())
}

const task = { id: '9', title: 'Nova' } as Task

function renderPopup(onTaskCreated = vi.fn()) {
  const user = userEvent.setup()
  render(<ChatPopup onTaskCreated={onTaskCreated} onApiError={() => false} />)
  return {
    user,
    button: screen.getByRole('button', { name: /^Assistente IA/ }),
    message: () => screen.getByLabelText('Mensagem para o assistente'),
    close: () => user.click(screen.getByRole('button', { name: 'Fechar assistente' })),
  }
}

describe('ChatPopup', () => {
  it('starts closed, opens with the focus on the message box and × closes back to the button', async () => {
    const { user, button, message, close } = renderPopup()
    const panel = screen.getByRole('dialog', { hidden: true })
    expect(button).toHaveAccessibleName('Assistente IA')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(button).toHaveAttribute('aria-controls', panel.id)
    expect(panel).not.toBeVisible()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await user.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('dialog', { name: 'Assistente IA' })).toBeVisible()
    expect(panel).not.toHaveAttribute('aria-modal')
    expect(message()).toHaveFocus()

    await close()
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(panel).not.toBeVisible()
    expect(button).toHaveFocus()
  })

  it('Esc closes only while the focus is inside the panel', async () => {
    const { user, button, message } = renderPopup()
    await user.click(button)

    button.focus()
    await user.keyboard('{Escape}')
    expect(button).toHaveAttribute('aria-expanded', 'true')

    await user.click(message())
    await user.keyboard('{Escape}')
    expect(button).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(button).toHaveFocus()
  })

  it('keeps the conversation and its id after closing and reopening', async () => {
    const reply = 'Olá! Como posso ajudar?'
    mockStream({ type: 'done', reply, created_task: null, conversation_id: 'c1' })
    const { user, button, message, close } = renderPopup()
    await user.click(button)
    await user.type(message(), 'oi{Enter}')
    expect(await screen.findByText(reply)).toBeVisible()
    // Read with the popup open: no unread flag.
    expect(within(button).queryByText('nova resposta')).not.toBeInTheDocument()

    await close()
    expect(screen.getByText('oi')).not.toBeVisible()
    expect(within(button).queryByText('nova resposta')).not.toBeInTheDocument()

    await user.click(button)
    expect(screen.getByText('oi')).toBeVisible()
    expect(screen.getByText(reply)).toBeVisible()

    await user.type(message(), 'e agora?{Enter}')
    expect(await screen.findAllByText(reply)).toHaveLength(2)
    const calls = vi.mocked(streamChatMessage).mock.calls
    expect(calls.map(([text, conversationId]) => [text, conversationId])).toEqual([
      ['oi', null],
      ['e agora?', 'c1'],
    ])
  })

  it('shows "nova resposta" when a reply ends while closed, and opening clears it', async () => {
    const finish = mockStream(
      { type: 'done', reply: 'Pronto!', created_task: null, conversation_id: 'c1' },
      { hold: true },
    )
    const { user, button, message, close } = renderPopup()
    await user.click(button)
    await user.type(message(), 'oi{Enter}')
    await close()
    expect(within(button).queryByText('nova resposta')).not.toBeInTheDocument()

    await finish()
    expect(await within(button).findByText('nova resposta')).toBeInTheDocument()
    expect(button).toHaveAccessibleName('Assistente IA nova resposta')
    expect(screen.getByRole('status')).toHaveTextContent('Nova resposta do assistente.')

    await user.click(button)
    expect(within(button).queryByText('nova resposta')).not.toBeInTheDocument()
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
    expect(screen.getByText('Pronto!')).toBeVisible()
  })

  it('calls onTaskCreated when the reply creates a task with the popup closed', async () => {
    const finish = mockStream(
      { type: 'done', reply: 'Tarefa criada!', created_task: task, conversation_id: 'c1' },
      { hold: true },
    )
    const onTaskCreated = vi.fn()
    const { user, button, message, close } = renderPopup(onTaskCreated)
    await user.click(button)
    await user.type(message(), 'crie uma tarefa{Enter}')
    await close()
    expect(onTaskCreated).not.toHaveBeenCalled()

    await finish()
    await vi.waitFor(() => expect(onTaskCreated).toHaveBeenCalledWith(task))
    expect(button).toHaveAttribute('aria-expanded', 'false')
  })
})
