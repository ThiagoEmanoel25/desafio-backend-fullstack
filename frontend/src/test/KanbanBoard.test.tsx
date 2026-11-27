import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiError } from '../api/client'
import { updateTask } from '../api/tasks'
import KanbanBoard from '../components/KanbanBoard'
import type { Task } from '../types'

vi.mock('../api/tasks')

const base: Task = {
  id: '',
  title: '',
  description: null,
  status: 'pending',
  priority: 'medium',
  department: 'Ops',
  due_date: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

const tasks: Task[] = [
  {
    ...base,
    id: '1',
    title: 'Revisar relatório',
    priority: 'urgent',
    department: 'Comercial',
    due_date: '2026-03-15',
    description: 'Conferir os números do trimestre.',
  },
  { ...base, id: '2', title: 'Fechar proposta', status: 'in_progress' },
  { ...base, id: '3', title: 'Arquivar contratos', status: 'completed' },
  { ...base, id: '4', title: 'Atualizar planilha' },
]

function renderBoard({ onApiError = vi.fn((_err: unknown) => false), list = tasks } = {}) {
  const onChanged = vi.fn()
  const onAssist = vi.fn()
  const user = userEvent.setup()
  const { rerender } = render(
    <KanbanBoard tasks={list} onChanged={onChanged} onAssist={onAssist} onApiError={onApiError} />,
  )
  const update = (next: Task[]) =>
    rerender(<KanbanBoard tasks={next} onChanged={onChanged} onAssist={onAssist} onApiError={onApiError} />)
  return { user, onChanged, onAssist, onApiError, update }
}

// Each column is a section named by its heading ("Pendente 2 tarefas").
const column = (name: string) => screen.getByRole('region', { name: new RegExp(`^${name} `) })
const card = (title: string) => screen.getByText(title).closest('li')!
const moveSelect = (title: string) => screen.getByLabelText(`Mover para: ${title}`)

// jsdom has no DataTransfer; the board only uses these members.
function fakeDataTransfer() {
  const data: Record<string, string> = {}
  return {
    data,
    dropEffect: 'none',
    effectAllowed: 'all',
    setData: (type: string, value: string) => {
      data[type] = value
    },
    getData: (type: string) => data[type] ?? '',
  }
}

describe('KanbanBoard', () => {
  it('shows one column per status, with its count, and each task in its column', async () => {
    const { user, onAssist } = renderBoard()
    expect(screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)).toEqual([
      'Pendente 2 tarefas',
      'Em andamento 1 tarefa',
      'Concluída 1 tarefa',
    ])
    const titles = (name: string) =>
      within(column(name)).getAllByRole('listitem').map((li) => li.querySelector('.task-title')?.textContent)
    expect(titles('Pendente')).toEqual(['Revisar relatório', 'Atualizar planilha'])
    expect(titles('Em andamento')).toEqual(['Fechar proposta'])
    expect(titles('Concluída')).toEqual(['Arquivar contratos'])

    const first = within(card('Revisar relatório'))
    expect(first.getByText('Urgente')).toBeInTheDocument()
    expect(first.getByText('Comercial')).toBeInTheDocument()
    expect(first.getByText('Prazo: 15/03/2026')).toHaveAttribute('dateTime', '2026-03-15')
    expect(first.getByText('Conferir os números do trimestre.')).toBeInTheDocument()
    expect(moveSelect('Revisar relatório')).toHaveValue('pending')
    expect(within(moveSelect('Revisar relatório')).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Pendente',
      'Em andamento',
      'Concluída',
    ])
    expect(card('Revisar relatório')).toHaveAttribute('draggable', 'true')
    expect(card('Arquivar contratos')).toHaveClass('task-completed') // struck through, as in the list
    expect(first.queryByRole('button', { name: /Excluir/ })).not.toBeInTheDocument()

    await user.click(first.getByRole('button', { name: 'Pedir ajuda à IA' }))
    expect(onAssist).toHaveBeenCalledWith(tasks[0])
  })

  it('shows "Nenhuma tarefa" in an empty column', () => {
    renderBoard({ list: [tasks[0]] })
    expect(within(column('Pendente')).queryByText('Nenhuma tarefa')).not.toBeInTheDocument()
    expect(within(column('Em andamento')).getByText('Nenhuma tarefa')).toBeInTheDocument()
    expect(within(column('Concluída')).getByText('Nenhuma tarefa')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Concluída 0 tarefas' })).toBeInTheDocument()
  })

  it('moves a card with "Mover para" at once, busy until the PATCH answers, then calls onChanged', async () => {
    let answer!: (task: Task) => void
    vi.mocked(updateTask).mockReturnValue(new Promise((resolve) => (answer = resolve)))
    const { user, onChanged } = renderBoard()

    await user.selectOptions(moveSelect('Revisar relatório'), 'in_progress')
    expect(updateTask).toHaveBeenCalledWith('1', { status: 'in_progress' })
    const moved = card('Revisar relatório')
    expect(column('Em andamento')).toContainElement(moved)
    expect(screen.getByRole('heading', { name: 'Pendente 1 tarefa' })).toBeInTheDocument()
    expect(moved).toHaveAttribute('aria-busy', 'true')
    expect(moveSelect('Revisar relatório')).toBeDisabled()
    expect(moved).toHaveFocus() // the select was replaced: the focus stays on the card
    expect(onChanged).not.toHaveBeenCalled()

    await act(async () => answer({ ...tasks[0], status: 'in_progress' }))
    expect(onChanged).toHaveBeenCalledTimes(1)
    expect(column('Em andamento')).toContainElement(moved)
    expect(moved).toHaveAttribute('aria-busy', 'false')
    expect(moveSelect('Revisar relatório')).toBeEnabled()
    expect(moveSelect('Revisar relatório')).toHaveValue('in_progress')
    expect(screen.getByRole('status')).toHaveTextContent('“Revisar relatório” movida para Em andamento.')
  })

  it('takes fresh tasks from the parent over a saved move', async () => {
    vi.mocked(updateTask).mockResolvedValue({ ...tasks[0], status: 'completed' })
    const { user, onChanged, update } = renderBoard()
    await user.selectOptions(moveSelect('Revisar relatório'), 'completed')
    await waitFor(() => expect(onChanged).toHaveBeenCalled())
    expect(column('Concluída')).toContainElement(card('Revisar relatório'))

    // The reload brings the task as the server has it now (changed again elsewhere).
    update([{ ...tasks[0], status: 'in_progress' }, ...tasks.slice(1)])
    expect(column('Em andamento')).toContainElement(card('Revisar relatório'))
  })

  it('drops a dragged card on another column, and not on its own', async () => {
    vi.mocked(updateTask).mockResolvedValue({ ...tasks[1], status: 'completed' })
    const { onChanged } = renderBoard()
    const dataTransfer = fakeDataTransfer()

    // Its own column does not take the drop: dragover is not canceled and drop does nothing.
    fireEvent.dragStart(card('Fechar proposta'), { dataTransfer })
    expect(dataTransfer.data['text/plain']).toBe('2')
    const own = column('Em andamento')
    expect(fireEvent.dragOver(own, { dataTransfer })).toBe(true)
    expect(own).not.toHaveClass('is-over')
    fireEvent.drop(own, { dataTransfer })
    expect(updateTask).not.toHaveBeenCalled()

    fireEvent.dragStart(card('Fechar proposta'), { dataTransfer })
    const target = column('Concluída')
    fireEvent.dragEnter(target, { dataTransfer })
    expect(fireEvent.dragOver(target, { dataTransfer })).toBe(false) // canceled: the drop is allowed
    expect(target).toHaveClass('is-over')
    expect(dataTransfer.dropEffect).toBe('move')
    fireEvent.drop(target, { dataTransfer })
    expect(updateTask).toHaveBeenCalledTimes(1)
    expect(updateTask).toHaveBeenCalledWith('2', { status: 'completed' })
    expect(column('Concluída')).toContainElement(card('Fechar proposta'))
    expect(column('Concluída')).not.toHaveClass('is-over')
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('“Fechar proposta” movida para Concluída.'),
    )
    expect(onChanged).toHaveBeenCalledTimes(1)
  })

  it('puts the card back and shows an alert when the move fails', async () => {
    const failure = new ApiError(500, 'Internal Server Error')
    vi.mocked(updateTask).mockRejectedValue(failure)
    const { user, onChanged, onApiError } = renderBoard()

    await user.selectOptions(moveSelect('Revisar relatório'), 'completed')
    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível mover a tarefa.')
    expect(onApiError).toHaveBeenCalledWith(failure)
    expect(column('Pendente')).toContainElement(card('Revisar relatório'))
    expect(card('Revisar relatório')).toHaveFocus() // the focus came back with the card
    expect(screen.getByRole('heading', { name: 'Concluída 1 tarefa' })).toBeInTheDocument()
    expect(card('Revisar relatório')).toHaveAttribute('aria-busy', 'false')
    expect(moveSelect('Revisar relatório')).toHaveValue('pending')
    expect(onChanged).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toBeEmptyDOMElement()
  })

  it('leaves a 401 to onApiError (logout) without the alert', async () => {
    vi.mocked(updateTask).mockRejectedValue(new ApiError(401, 'Unauthorized'))
    const onApiError = vi.fn((_err: unknown) => true)
    const { user } = renderBoard({ onApiError })
    await user.selectOptions(moveSelect('Revisar relatório'), 'completed')
    await waitFor(() => expect(onApiError).toHaveBeenCalled())
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(column('Pendente')).toContainElement(card('Revisar relatório'))
  })
})
