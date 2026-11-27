import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, test, vi } from 'vitest'
import * as api from '../api/tasks'
import TaskForm from '../components/TaskForm'
import TaskList from '../components/TaskList'
import TaskCalendar from '../components/TaskCalendar'
import { tagTextColor } from '../tagColors'
import type { Task } from '../types'

vi.mock('../api/tasks')

const task: Task = {
  id: '1', title: 'Revisar contrato', description: 'Conferir valores',
  department: 'Comercial', status: 'in_progress', priority: 'high',
  due_date: '2026-12-15', tags: [{ name: 'Cliente', color: '#123456' }],
  created_at: '', updated_at: '',
}

beforeEach(() => vi.clearAllMocks())

test('edits fields, clears deadline and saves the selected tag color', async () => {
  vi.mocked(api.updateTask).mockResolvedValue(task)
  const saved = vi.fn()
  const user = userEvent.setup()
  render(<TaskForm task={task} onCreated={saved} onApiError={() => false} />)
  await user.clear(screen.getByLabelText('Título'))
  await user.type(screen.getByLabelText('Título'), 'Contrato atualizado')
  await user.clear(screen.getByLabelText('Prazo · opcional'))
  fireEvent.change(screen.getByLabelText('Cor da tag 1'), { target: { value: '#ff8800' } })
  await user.selectOptions(screen.getByLabelText('Status da tarefa'), 'completed')
  await user.click(screen.getByRole('button', { name: 'Salvar alterações' }))
  await waitFor(() => expect(saved).toHaveBeenCalledWith(task))
  expect(api.updateTask).toHaveBeenCalledWith('1', expect.objectContaining({
    title: 'Contrato atualizado', due_date: null, status: 'completed',
    tags: [{ name: 'Cliente', color: '#ff8800' }],
  }))
})

test('creates a task with a colored tag and can remove the tag', async () => {
  vi.mocked(api.createTask).mockResolvedValue(task)
  const user = userEvent.setup()
  render(<TaskForm onCreated={() => {}} onApiError={() => false} />)
  await user.type(screen.getByLabelText('Título'), 'Nova entrega')
  await user.type(screen.getByLabelText('Departamento'), 'Comercial')
  await user.type(screen.getByLabelText('Nova tag'), 'Financeiro')
  fireEvent.change(screen.getByLabelText('Cor da nova tag'), { target: { value: '#ff0000' } })
  await user.click(screen.getByRole('button', { name: 'Adicionar tag' }))
  expect(screen.getByLabelText('Cor da tag 1')).toHaveValue('#ff0000')
  await user.click(screen.getByRole('button', { name: 'Remover tag 1' }))
  expect(screen.queryByLabelText('Cor da tag 1')).not.toBeInTheDocument()
  await user.type(screen.getByLabelText('Nova tag'), 'Cliente')
  await user.click(screen.getByRole('button', { name: 'Adicionar tag' }))
  await user.click(screen.getByRole('button', { name: 'Criar tarefa' }))
  await waitFor(() => expect(api.createTask).toHaveBeenCalledWith(expect.objectContaining({
    tags: [{ name: 'Cliente', color: '#ff0000' }],
  })))
})

test('cancel editing does not save', async () => {
  const cancel = vi.fn()
  render(<TaskForm task={task} onCancel={cancel} onCreated={() => {}} onApiError={() => false} />)
  await userEvent.click(screen.getByRole('button', { name: 'Cancelar edição' }))
  expect(cancel).toHaveBeenCalledOnce()
  expect(api.updateTask).not.toHaveBeenCalled()
})

function renderList(tasks = [task]) {
  const changed = vi.fn()
  const edit = vi.fn()
  render(<TaskList tasks={tasks} filtered={false} onChanged={changed} onEdit={edit}
    onAssist={() => {}} onApiError={() => false} />)
  return { changed, edit }
}

test('duplicate and edit actions operate on the chosen task', async () => {
  vi.mocked(api.duplicateTask).mockResolvedValue(task)
  const { changed, edit } = renderList()
  await userEvent.click(screen.getByRole('button', { name: 'Editar' }))
  expect(edit).toHaveBeenCalledWith(task)
  await userEvent.click(screen.getByRole('button', { name: 'Duplicar' }))
  await waitFor(() => expect(changed).toHaveBeenCalledOnce())
  expect(api.duplicateTask).toHaveBeenCalledWith(task)
})

test('batch delete requires confirmation and processes only selected tasks', async () => {
  vi.mocked(api.deleteTask).mockResolvedValue(undefined)
  renderList([task, { ...task, id: '2', title: 'Outra tarefa' }])
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('Selecionar Revisar contrato'))
  await user.click(screen.getByRole('button', { name: 'Excluir selecionadas' }))
  expect(api.deleteTask).not.toHaveBeenCalled()
  await user.click(screen.getByRole('button', { name: 'Confirmar exclusão em lote' }))
  await waitFor(() => expect(api.deleteTask).toHaveBeenCalledExactlyOnceWith('1'))
})

test('batch completion reports partial failure and keeps failed task selected', async () => {
  vi.mocked(api.updateTask).mockResolvedValueOnce(task).mockRejectedValueOnce(new Error('offline'))
  renderList([task, { ...task, id: '2', title: 'Outra tarefa' }])
  const user = userEvent.setup()
  await user.click(screen.getByLabelText('Selecionar todas as tarefas exibidas'))
  await user.click(screen.getByRole('button', { name: 'Concluir selecionadas' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('1 falharam')
  expect(screen.getByLabelText('Selecionar Outra tarefa')).toBeChecked()
  expect(screen.getByLabelText('Selecionar Revisar contrato')).not.toBeChecked()
  expect(api.updateTask).toHaveBeenCalledWith('1', { status: 'completed' })
})

test('calendar uses the first tag color, readable text and opens the editor', async () => {
  const today = new Date()
  const due_date = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-15`
  const edit = vi.fn()
  const dated = { ...task, due_date, tags: [{ name: 'Cliente', color: '#ffffff' }] }
  render(<TaskCalendar tasks={[dated]} onAssist={() => {}} onEdit={edit} />)
  const entry = screen.getByRole('button', { name: task.title })
  expect(entry).toHaveStyle({ backgroundColor: '#ffffff', color: '#000000' })
  expect(tagTextColor('#000000')).toBe('#ffffff')
  await userEvent.click(entry)
  expect(edit).toHaveBeenCalledWith(dated)
})
