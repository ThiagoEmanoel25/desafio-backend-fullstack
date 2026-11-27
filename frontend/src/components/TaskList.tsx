import { useState } from 'react'
import { deleteTask, updateTask } from '../api/tasks'
import { PRIORITY_LABEL, STATUS_LABEL } from '../labels'
import type { Task, TaskStatus } from '../types'
import Badge from './Badge'
import EmptyState from './EmptyState'

interface TaskListProps {
  tasks: Task[]
  /** True when a filter is active, to tell "no tasks" from "no matches". */
  filtered: boolean
  onChanged: () => void
  onAssist: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

export default function TaskList({ tasks, filtered, onChanged, onAssist, onApiError }: TaskListProps) {
  const [busyId, setBusyId] = useState<string | null>(null)
  const [confirmId, setConfirmId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

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
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="task-list">
        {tasks.map((task) => {
          const busy = busyId === task.id
          const confirming = confirmId === task.id
          return (
            <li key={task.id} className={`task task-${task.status}`}>
              <div className="task-main">
                <strong className="task-title">{task.title}</strong>
                {task.description && <p className="task-desc">{task.description}</p>}
                <div className="task-meta">
                  <Badge tone={task.priority}>{PRIORITY_LABEL[task.priority]}</Badge>
                  <Badge tone={task.status}>{STATUS_LABEL[task.status]}</Badge>
                  <span className="muted">{task.department}</span>
                  {task.due_date && <time dateTime={task.due_date}>Prazo: {task.due_date.split('-').reverse().join('/')}</time>}
                </div>
              </div>
              <div className="task-actions">
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
