import { useState } from 'react'
import { deleteTask, updateTask } from '../api/tasks'
import type { Task, TaskStatus } from '../types'

interface TaskListProps {
  tasks: Task[]
  onChanged: () => void
  onAssist: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

const PRIORITY_LABEL = { low: 'Baixa', medium: 'Média', high: 'Alta', urgent: 'Urgente' }
const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: 'Pendente',
  in_progress: 'Em andamento',
  completed: 'Concluída',
}

export default function TaskList({ tasks, onChanged, onAssist, onApiError }: TaskListProps) {
  const [busyId, setBusyId] = useState<string | null>(null)
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
    }
  }

  return (
    <section className="card stack">
      <h2>Tarefas ({tasks.length})</h2>
      {error && <p className="error">{error}</p>}
      {tasks.length === 0 && <p className="muted">Nenhuma tarefa ainda.</p>}
      <ul className="task-list">
        {tasks.map((task) => {
          const busy = busyId === task.id
          return (
            <li key={task.id} className="task">
              <div>
                <strong>{task.title}</strong>
                <div className="muted">
                  {task.department} · {PRIORITY_LABEL[task.priority]}
                </div>
              </div>
              <div className="row">
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
                <button disabled={busy} onClick={() => onAssist(task)}>
                  Pedir ajuda à IA
                </button>
                <button
                  className="danger"
                  disabled={busy}
                  onClick={() => void mutate(task.id, () => deleteTask(task.id))}
                >
                  Excluir
                </button>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
