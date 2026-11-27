import { useState } from 'react'
import { deleteTask, duplicateTask, updateTask } from '../api/tasks'
import { PRIORITY_LABEL, STATUS_LABEL } from '../labels'
import type { Task, TaskStatus } from '../types'
import Badge from './Badge'
import EmptyState from './EmptyState'
import TaskTags from './TaskTags'

interface TaskListProps {
  onEdit?: (task: Task) => void
  tasks: Task[]
  /** True when a filter is active, to tell "no tasks" from "no matches". */
  filtered: boolean
  onChanged: () => void
  onAssist: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

export default function TaskList({ tasks, filtered, onChanged, onAssist, onApiError, onEdit }: TaskListProps) {
  const [busyId, setBusyId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [confirmBatch, setConfirmBatch] = useState(false)
  const [notice, setNotice] = useState('')
  const selectedTasks = tasks.filter(task => selected.has(task.id))
  const allSelected = tasks.length > 0 && selectedTasks.length === tasks.length

  function toggle(id: string) {
    setConfirmBatch(false)
    setSelected(current => { const next = new Set(current); if (next.has(id)) next.delete(id); else next.add(id); return next })
  }

  async function batch(action: 'complete' | 'delete') {
    if (busyId || selectedTasks.length === 0) return
    setBusyId('batch')
    setError(null)
    setNotice('')
    let done = 0
    const failed = new Set<string>()
    try {
      for (const task of selectedTasks) {
        try {
          if (action === 'delete') await deleteTask(task.id)
          else await updateTask(task.id, { status: 'completed' })
          done++
        } catch (err) {
          failed.add(task.id)
          if (onApiError(err)) break
        }
        setNotice(`Processando ${done + failed.size} de ${selectedTasks.length} tarefa(s)…`)
      }
      setSelected(failed)
      if (failed.size) {
        setNotice('')
        setError(`${done} tarefa(s) ${action === 'delete' ? 'excluída(s)' : 'concluída(s)'}; ${failed.size} falharam. Atualize a lista e tente novamente.`)
      }
      else setNotice(`${done} tarefa(s) ${action === 'delete' ? 'excluída(s)' : 'concluída(s)'}.`)
      onChanged()
    } finally {
      setBusyId(null)
      setConfirmBatch(false)
    }
  }

  async function mutate(id: string, action: () => Promise<unknown>) {
    if (busyId) return
    setBusyId(id)
    setError(null)
    try {
      await action()
      onChanged()
    } catch (err) {
      if (!onApiError(err)) setError('Não foi possível atualizar a tarefa.')
    } finally {
      setBusyId(null)
      setConfirmId(null)
    }
  }

  if (tasks.length === 0) {
    return filtered ? (
      <EmptyState title="Nenhuma tarefa com esses filtros.">Mude os filtros para ver outras tarefas.</EmptyState>
    ) : (
      <EmptyState title="Nenhuma tarefa ainda.">Crie uma no formulário ou peça ao assistente.</EmptyState>
    )
  }

  return (
    <>
      <div className="bulk-toolbar">
        <label className="row"><input type="checkbox" aria-label="Selecionar todas as tarefas exibidas" checked={allSelected}
          disabled={Boolean(busyId)} onChange={() => { setSelected(allSelected ? new Set() : new Set(tasks.map(t => t.id))); setConfirmBatch(false) }} />
          Selecionar todas</label>
        <span className="muted">{selectedTasks.length} selecionada(s)</span>
        {selectedTasks.length > 0 && <>
          <button className="secondary" disabled={Boolean(busyId)} onClick={() => void batch('complete')}>Concluir selecionadas</button>
          <button className="ghost danger-text" disabled={Boolean(busyId)} onClick={() => setConfirmBatch(true)}>Excluir selecionadas</button>
        </>}
      </div>
      {confirmBatch && <div className="error-state" role="alert">
        <p>Excluir {selectedTasks.length} tarefa(s)? Esta ação não pode ser desfeita.</p>
        <div className="row"><button className="danger" disabled={Boolean(busyId)} onClick={() => void batch('delete')}>Confirmar exclusão em lote</button>
          <button className="secondary" disabled={Boolean(busyId)} onClick={() => setConfirmBatch(false)}>Cancelar</button></div>
      </div>}
      {notice && <p role="status">{notice}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="task-list">
        {tasks.map((task) => {
          const busy = Boolean(busyId)
          const confirming = confirmId === task.id
          return (
            <li key={task.id} className={`task task-${task.status}`}>
              <input type="checkbox" aria-label={`Selecionar ${task.title}`} checked={selected.has(task.id)} disabled={busy} onChange={() => toggle(task.id)} />
              <div className="task-main">
                <strong className="task-title">{task.title}</strong>
                {task.description && <p className="task-desc">{task.description}</p>}
                <TaskTags tags={task.tags} />
                <div className="task-meta">
                  <Badge tone={task.priority}>{PRIORITY_LABEL[task.priority]}</Badge>
                  <Badge tone={task.status}>{STATUS_LABEL[task.status]}</Badge>
                  <span className="muted">{task.department}</span>
                  {task.due_date && <time dateTime={task.due_date}>Prazo: {task.due_date.split('-').reverse().join('/')}</time>}
                </div>
              </div>
              <div className="task-actions">
                {onEdit && <button className="secondary" disabled={busy} onClick={() => onEdit(task)}>Editar</button>}
                <button className="secondary" disabled={busy} onClick={() => void mutate(task.id, () => duplicateTask(task))}>Duplicar</button>
                <select
                  aria-label={`Status de ${task.title}`}
                  value={task.status}
                  disabled={busy}
                  onChange={(e) =>
                    void mutate(task.id, () =>
                      updateTask(task.id, { status: e.target.value as TaskStatus }),
                    )
                  }
                >
                  {Object.entries(STATUS_LABEL).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <button type="button" className="secondary" disabled={busy} onClick={() => onAssist(task)}>
                  Pedir ajuda à IA
                </button>
                {confirming ? (
                  <span className="confirm">
                    <button
                      type="button"
                      className="danger"
                      disabled={busy}
                      onClick={() => void mutate(task.id, () => deleteTask(task.id))}
                    >
                      Confirmar exclusão
                    </button>
                    <button type="button" className="ghost" disabled={busy} onClick={() => setConfirmId(null)}>
                      Cancelar
                    </button>
                  </span>
                ) : (
                  <button
                    type="button"
                    className="ghost danger-text"
                    disabled={busy}
                    aria-label={`Excluir ${task.title}`}
                    onClick={() => setConfirmId(task.id)}
                  >
                    Excluir
                  </button>
                )}
              </div>
            </li>
          )
        })}
      </ul>
    </>
  )
}
