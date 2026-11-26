import { useCallback, useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { listTasks } from '../api/tasks'
import ChatPanel from '../components/ChatPanel'
import TaskAssistantPanel from '../components/TaskAssistantPanel'
import TaskForm from '../components/TaskForm'
import TaskList from '../components/TaskList'
import type { Task } from '../types'

interface TasksPageProps {
  onLogout: () => void
}

/** Main page: owns the task list; children report mutations and API errors back. */
export default function TasksPage({ onLogout }: TasksPageProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [assistedTask, setAssistedTask] = useState<Task | null>(null)

  // The single place where an expired session (401) logs the user out.
  // Returns true when the error was a 401 and has been handled.
  const handleApiError = useCallback(
    (err: unknown): boolean => {
      if (err instanceof ApiError && err.status === 401) {
        onLogout()
        return true
      }
      return false
    },
    [onLogout],
  )

  const refresh = useCallback(async () => {
    try {
      setTasks(await listTasks())
      setError(null)
    } catch (err) {
      if (!handleApiError(err)) setError('Não foi possível carregar as tarefas.')
    } finally {
      setLoading(false)
    }
  }, [handleApiError])

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- initial fetch; state is set after await
    void refresh()
  }, [refresh])

  function retry() {
    setLoading(true)
    void refresh()
  }

  return (
    <main className="container">
      <header className="row between">
        <h1>Minhas tarefas</h1>
        <button onClick={onLogout}>Sair</button>
      </header>

      <div className="grid">
        <section className="stack">
          <TaskForm onCreated={() => void refresh()} onApiError={handleApiError} />
          {loading ? (
            <p className="muted">Carregando tarefas…</p>
          ) : error ? (
            <div className="card stack">
              <p className="error">{error}</p>
              <button onClick={retry}>Tentar novamente</button>
            </div>
          ) : (
            <TaskList
              tasks={tasks}
              onChanged={() => void refresh()}
              onAssist={setAssistedTask}
              onApiError={handleApiError}
            />
          )}
        </section>

        <ChatPanel onTaskCreated={() => void refresh()} onApiError={handleApiError} />
      </div>

      {assistedTask && (
        <TaskAssistantPanel
          key={assistedTask.id}
          task={assistedTask}
          onClose={() => setAssistedTask(null)}
          onApiError={handleApiError}
        />
      )}
    </main>
  )
}
