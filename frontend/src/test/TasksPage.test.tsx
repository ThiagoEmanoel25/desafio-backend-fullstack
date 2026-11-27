import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from '../api/auth'
import * as chatApi from '../api/chat'
import * as tasksApi from '../api/tasks'
import TasksPage from '../pages/TasksPage'
import type { Task } from '../types'

vi.mock('../api/tasks')
vi.mock('../api/auth')
vi.mock('../api/chat')

const task: Task = {
  id: '1',
  title: 'Revisar relatório',
  description: null,
  status: 'pending',
  priority: 'urgent',
  department: 'Comercial',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

beforeEach(() => {
  vi.mocked(authApi.getCurrentUser).mockResolvedValue({
    id: 'u', email: 'ana@example.com', full_name: 'Ana', created_at: '',
  })
})

describe('TasksPage list', () => {
  it('shows the loading state, then the tasks and the count', async () => {
    let resolve!: (t: Task[]) => void
    vi.mocked(tasksApi.listTasks).mockReturnValue(new Promise((r) => (resolve = r)))
    render(<TasksPage onLogout={() => {}} />)
    expect(screen.getByRole('status', { name: 'Carregando tarefas…' })).toBeInTheDocument()
    resolve([task])
    expect(await screen.findByText('Revisar relatório')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Tarefas \(1\)/ })).toBeInTheDocument()
    expect(await screen.findByText('Ana')).toBeInTheDocument()
  })

  it('shows the empty state', async () => {
    vi.mocked(tasksApi.listTasks).mockResolvedValue([])
    render(<TasksPage onLogout={() => {}} />)
    expect(await screen.findByText('Nenhuma tarefa ainda.')).toBeInTheDocument()
  })

  it('shows the error state and retries', async () => {
    vi.mocked(tasksApi.listTasks).mockRejectedValueOnce(new Error('boom')).mockResolvedValue([task])
    render(<TasksPage onLogout={() => {}} />)
    expect(await screen.findByText('Não foi possível carregar as tarefas.')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(await screen.findByText('Revisar relatório')).toBeInTheDocument()
  })

  it('reloads with the selected filters and "Todos" removes them', async () => {
    vi.mocked(tasksApi.listTasks).mockResolvedValue([task])
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({}, 100)

    await user.selectOptions(screen.getByLabelText('Filtrar por status'), 'in_progress')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: 'in_progress' }, 100)

    vi.mocked(tasksApi.listTasks).mockResolvedValue([])
    await user.selectOptions(screen.getByLabelText('Filtrar por prioridade'), 'urgent')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: 'in_progress', priority: 'urgent' }, 100)
    expect(await screen.findByText('Nenhuma tarefa com esses filtros.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Tarefas \(0\)/ })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Filtrar por status'), '')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: '', priority: 'urgent' }, 100)
  })

  it('notes when the API sent its maximum of 100 tasks', async () => {
    const many = Array.from({ length: 100 }, (_, i) => ({ ...task, id: String(i), title: `Tarefa ${i}` }))
    vi.mocked(tasksApi.listTasks).mockResolvedValueOnce([task]).mockResolvedValue(many)
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')
    expect(screen.queryByText('Mostrando as 100 tarefas mais recentes.')).not.toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Filtrar por prioridade'), 'urgent')
    expect(await screen.findByText('Mostrando as 100 tarefas mais recentes.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Tarefas \(100\)/ })).toBeInTheDocument()
  })

  it('keeps the "+ Nova tarefa" link pointing at the form', async () => {
    vi.mocked(tasksApi.listTasks).mockResolvedValue([])
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Nenhuma tarefa ainda.')
    expect(screen.getByRole('link', { name: '+ Nova tarefa' })).toHaveAttribute('href', '#new-task')
    expect(document.getElementById('new-task')).toContainElement(screen.getByRole('button', { name: 'Criar tarefa' }))
  })
})

describe('TasksPage chat popup', () => {
  it('starts closed and a task the chat creates after closing it shows up in the list', async () => {
    const created: Task = { ...task, id: '2', title: 'Criada pelo chat' }
    vi.mocked(tasksApi.listTasks).mockResolvedValueOnce([task]).mockResolvedValue([task, created])
    let release = () => {}
    vi.mocked(chatApi.streamChatMessage).mockImplementation(async (_message, _conversationId, onEvent) => {
      onEvent({ type: 'meta', conversation_id: 'c1' })
      await new Promise<void>((resolve) => (release = resolve))
      onEvent({ type: 'done', reply: 'Criei a tarefa.', created_task: created, conversation_id: 'c1' })
    })
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')

    const chat = screen.getByRole('button', { name: 'Assistente IA' })
    expect(chat).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    await user.click(chat)
    await user.type(screen.getByLabelText('Mensagem para o assistente'), 'crie uma tarefa{Enter}')
    await user.click(screen.getByRole('button', { name: 'Fechar assistente' }))

    await act(async () => release())
    expect(await screen.findByText('Criada pelo chat')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Tarefas \(2\)/ })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})

describe('TasksPage views', () => {
  it('has Lista, Kanban and Calendário tabs; arrows and Home/End move and select', async () => {
    vi.mocked(tasksApi.listTasks).mockResolvedValue([task])
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')

    const tabs = within(screen.getByRole('tablist', { name: 'Visualização das tarefas' })).getAllByRole('tab')
    expect(tabs.map((t) => t.textContent)).toEqual(['Lista', 'Kanban', 'Calendário'])
    const [list, kanban, calendar] = tabs
    const selected = () => tabs.map((t) => t.getAttribute('aria-selected'))
    const tabStops = () => tabs.map((t) => t.tabIndex)
    expect(selected()).toEqual(['true', 'false', 'false'])
    expect(tabStops()).toEqual([0, -1, -1])
    for (const tab of tabs) {
      const panel = document.getElementById(tab.getAttribute('aria-controls')!)
      expect(panel).toHaveAttribute('role', 'tabpanel')
      expect(panel).toHaveAttribute('aria-labelledby', tab.id)
    }
    expect(screen.getByRole('tabpanel', { name: 'Lista' })).toContainElement(screen.getByText('Revisar relatório'))

    await user.click(list)
    await user.keyboard('{ArrowRight}')
    expect(kanban).toHaveFocus()
    expect(selected()).toEqual(['false', 'true', 'false'])
    expect(tabStops()).toEqual([-1, 0, -1])
    expect(screen.getByRole('tabpanel', { name: 'Kanban' })).toContainElement(
      screen.getByRole('region', { name: /^Pendente/ }),
    )

    await user.keyboard('{ArrowRight}')
    expect(calendar).toHaveFocus()
    expect(selected()).toEqual(['false', 'false', 'true'])
    expect(screen.getByRole('tabpanel', { name: 'Calendário' })).toContainElement(
      screen.getByRole('button', { name: 'Próximo mês' }),
    )
    await user.keyboard('{ArrowRight}') // wraps around
    expect(list).toHaveFocus()
    expect(selected()).toEqual(['true', 'false', 'false'])
    await user.keyboard('{ArrowLeft}')
    expect(calendar).toHaveFocus()
    await user.keyboard('{Home}')
    expect(list).toHaveFocus()
    await user.keyboard('{End}')
    expect(calendar).toHaveFocus()
    expect(selected()).toEqual(['false', 'false', 'true'])
    expect(tabStops()).toEqual([-1, -1, 0])
  })

  it('Kanban loads every status (limit 100) and hides the status filter; Lista brings it back', async () => {
    const other: Task = { ...task, id: '2', title: 'Fechar proposta', status: 'in_progress' }
    vi.mocked(tasksApi.listTasks).mockImplementation(async (filters) => (filters?.status ? [task] : [task, other]))
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')
    await user.selectOptions(screen.getByLabelText('Filtrar por status'), 'pending')
    await user.selectOptions(screen.getByLabelText('Filtrar por prioridade'), 'urgent')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: 'pending', priority: 'urgent' }, 100)
    expect(await screen.findByRole('heading', { name: /Tarefas \(1\)/ })).toBeInTheDocument()

    await user.click(screen.getByRole('tab', { name: 'Kanban' }))
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ priority: 'urgent' }, 100)
    expect(screen.queryByLabelText('Filtrar por status')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Filtrar por prioridade')).toHaveValue('urgent')
    const inProgress = await screen.findByRole('region', { name: /^Em andamento/ })
    expect(within(inProgress).getByText('Fechar proposta')).toBeInTheDocument()
    // The count and the summary follow what the board shows.
    expect(screen.getByRole('heading', { name: /Tarefas \(2\)/ })).toBeInTheDocument()
    expect(within(screen.getByLabelText('Resumo das tarefas exibidas')).getByText('Em andamento').nextSibling).toHaveTextContent('1')

    await user.click(screen.getByRole('tab', { name: 'Lista' }))
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: 'pending', priority: 'urgent' }, 100)
    expect(screen.getByLabelText('Filtrar por status')).toHaveValue('pending')
    expect(await screen.findByRole('heading', { name: /Tarefas \(1\)/ })).toBeInTheDocument()
    expect(screen.queryByText('Fechar proposta')).not.toBeInTheDocument()
  })

  it('switching between Lista and Calendário keeps the query (no reload)', async () => {
    vi.mocked(tasksApi.listTasks).mockResolvedValue([task])
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')
    await user.click(screen.getByRole('tab', { name: 'Kanban' })) // no status chosen: same query
    await user.click(screen.getByRole('tab', { name: 'Calendário' }))
    await user.click(screen.getByRole('tab', { name: 'Lista' }))
    expect(tasksApi.listTasks).toHaveBeenCalledTimes(1)
  })
})

describe('TasksPage reloads with the current query', () => {
  // The chat reply waits until the returned function is called.
  function holdChatReply() {
    let release = () => {}
    vi.mocked(chatApi.streamChatMessage).mockImplementation(async (_message, _conversationId, onEvent) => {
      onEvent({ type: 'meta', conversation_id: 'c1' })
      await new Promise<void>((resolve) => (release = resolve))
      onEvent({
        type: 'done',
        reply: 'Criei a tarefa.',
        created_task: { ...task, id: '2', title: 'Criada pelo chat' },
        conversation_id: 'c1',
      })
    })
    return () => act(async () => release())
  }

  async function askTheChat(user: ReturnType<typeof userEvent.setup>) {
    await user.click(screen.getByRole('button', { name: 'Assistente IA' }))
    await user.type(screen.getByLabelText('Mensagem para o assistente'), 'crie uma tarefa{Enter}')
    await user.click(screen.getByRole('button', { name: 'Fechar assistente' }))
  }

  it('a task the chat creates after a filter change reloads with the new filter', async () => {
    vi.mocked(tasksApi.listTasks).mockResolvedValue([task])
    const finish = holdChatReply()
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')
    await askTheChat(user)

    await user.selectOptions(screen.getByLabelText('Filtrar por status'), 'in_progress')
    await screen.findByText('Revisar relatório')
    const calls = vi.mocked(tasksApi.listTasks).mock.calls.length
    await finish()
    await waitFor(() => expect(tasksApi.listTasks).toHaveBeenCalledTimes(calls + 1))
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: 'in_progress' }, 100)
  })

  it('a task the chat creates after opening the Kanban reloads every status', async () => {
    vi.mocked(tasksApi.listTasks).mockResolvedValue([task])
    const finish = holdChatReply()
    const user = userEvent.setup()
    render(<TasksPage onLogout={() => {}} />)
    await screen.findByText('Revisar relatório')
    await user.selectOptions(screen.getByLabelText('Filtrar por status'), 'pending')
    await screen.findByText('Revisar relatório')
    await askTheChat(user)

    await user.click(screen.getByRole('tab', { name: 'Kanban' }))
    await screen.findByRole('region', { name: /^Pendente/ })
    const calls = vi.mocked(tasksApi.listTasks).mock.calls.length
    await finish()
    await waitFor(() => expect(tasksApi.listTasks).toHaveBeenCalledTimes(calls + 1))
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({}, 100)
  })
})
