import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import ChatPanel from '../components/ChatPanel'
import type { ChatStreamEvent, Task } from '../types'

// Simulates POST /v1/chat/stream answering the given SSE frames.
function mockStream(events: ChatStreamEvent[]) {
  const encoder = new TextEncoder()
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const ev of events) controller.enqueue(encoder.encode(`data: ${JSON.stringify(ev)}\n\n`))
      controller.close()
    },
  })
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } }),
  )
}

const task = { id: '9', title: 'Nova' } as Task

async function send(text: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('Mensagem para o assistente'), `${text}{Enter}`)
}

describe('ChatPanel', () => {
  it('streams deltas, then done with created_task calls onTaskCreated', async () => {
    const fetchMock = mockStream([
      { type: 'meta', conversation_id: 'c1' },
      { type: 'delta', text: 'Tarefa ' },
      { type: 'delta', text: 'criada' },
      { type: 'done', reply: 'Tarefa criada!', created_task: task, conversation_id: 'c1' },
    ])
    const onTaskCreated = vi.fn()
    const onReply = vi.fn()
    render(<ChatPanel onTaskCreated={onTaskCreated} onApiError={() => false} onReply={onReply} />)
    await send('crie uma tarefa')
    expect(await screen.findByText('Tarefa criada!')).toBeInTheDocument()
    expect(screen.getByText('crie uma tarefa')).toBeInTheDocument()
    expect(onTaskCreated).toHaveBeenCalledWith(task)
    expect(onReply).toHaveBeenCalledTimes(1)
    expect(JSON.parse(fetchMock.mock.calls[0][1]?.body as string)).toEqual({
      message: 'crie uma tarefa',
      conversation_id: null,
    })
  })

  it('shows a message on an error event', async () => {
    mockStream([{ type: 'meta', conversation_id: 'c1' }, { type: 'error', detail: 'x' }])
    const onReply = vi.fn()
    render(<ChatPanel onTaskCreated={vi.fn()} onApiError={() => false} onReply={onReply} />)
    await send('oi')
    expect(await screen.findByRole('alert')).toHaveTextContent('O assistente está indisponível agora.')
    expect(onReply).not.toHaveBeenCalled()
  })

  it('shows an error when the stream ends without done', async () => {
    mockStream([{ type: 'meta', conversation_id: 'c1' }, { type: 'delta', text: 'meia resp' }])
    const onTaskCreated = vi.fn()
    render(<ChatPanel onTaskCreated={onTaskCreated} onApiError={() => false} />)
    await send('oi')
    expect(await screen.findByRole('alert')).toHaveTextContent('O assistente está indisponível agora.')
    expect(onTaskCreated).not.toHaveBeenCalled()
  })

  it('Shift+Enter inserts a line break instead of sending', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    const user = userEvent.setup()
    render(<ChatPanel onTaskCreated={vi.fn()} onApiError={() => false} />)
    const box = screen.getByLabelText('Mensagem para o assistente')
    await user.type(box, 'linha 1{Shift>}{Enter}{/Shift}linha 2')
    expect(box).toHaveValue('linha 1\nlinha 2')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
