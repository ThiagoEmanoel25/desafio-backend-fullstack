import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as authApi from '../api/auth'
import * as tasksApi from '../api/tasks'
import TasksPage from '../pages/TasksPage'
import type { Task } from '../types'

vi.mock('../api/tasks')
vi.mock('../api/auth')

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
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({})

    await user.selectOptions(screen.getByLabelText('Filtrar por status'), 'in_progress')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: 'in_progress' })

    vi.mocked(tasksApi.listTasks).mockResolvedValue([])
    await user.selectOptions(screen.getByLabelText('Filtrar por prioridade'), 'urgent')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: 'in_progress', priority: 'urgent' })
    expect(await screen.findByText('Nenhuma tarefa com esses filtros.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Tarefas \(0\)/ })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Filtrar por status'), '')
    expect(tasksApi.listTasks).toHaveBeenLastCalledWith({ status: '', priority: 'urgent' })
  })
})
