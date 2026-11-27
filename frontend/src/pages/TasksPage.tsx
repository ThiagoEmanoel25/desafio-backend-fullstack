import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getCurrentUser } from '../api/auth'
import { listTasks } from '../api/tasks'
import AppHeader from '../components/AppHeader'
import ChatPanel from '../components/ChatPanel'
import TaskAssistantPanel from '../components/TaskAssistantPanel'
import ErrorState from '../components/ErrorState'
import Skeleton from '../components/Skeleton'
import TaskFilters from '../components/TaskFilters'
import TaskForm from '../components/TaskForm'
import TaskList from '../components/TaskList'
import type { Task, TaskFilters as Filters, User } from '../types'

interface TasksPageProps {
  onLogout: () => void
}

/** Main page: owns the task list; children report mutations and API errors back. */
export default function TasksPage({ onLogout }: TasksPageProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>({})
  const [user, setUser] = useState<User | null>(null)
  const [assistedId, setAssistedId] = useState<string | null>(null)
  // Derived from the list, so a deleted task closes the panel and an edited one stays fresh.
  const assistedTask = tasks.find((t) => t.id === assistedId) ?? null

  // Keep the latest onLogout in a ref so handleApiError (and the effects that depend on it)
  // keep a stable identity even if the parent re-renders with a new callback.
  const onLogoutRef = useRef(onLogout)
  useEffect(() => {
    onLogoutRef.current = onLogout
  }, [onLogout])

  // The single place where an expired session (401) logs the user out.
  // Returns true when the error was a 401 and has been handled.
  const handleApiError = useCallback((err: unknown): boolean => {
    if (err instanceof ApiError && err.status === 401) {
      onLogoutRef.current()
      return true
    }
    return false
  }, [])

  // Only the latest request may write the list, so a slow response for an old
  // filter cannot overwrite the one the user picked after it.
  const requestId = useRef(0)
  const refresh = useCallback(async () => {
    const id = ++requestId.current
    try {
      const data = await listTasks(filters)
      if (id !== requestId.current) return
      setTasks(data)
      setError(null)
    } catch (err) {
      if (id !== requestId.current) return
      if (!handleApiError(err)) setError('Não foi possível carregar as tarefas.')
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [filters, handleApiError])

  // Runs on mount and every time a filter changes (refresh depends on filters).
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- fetch; state is set after await
    void refresh()
  }, [refresh])

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .catch((err) => handleApiError(err)) // without the name the header shows only "Sair"
  }, [handleApiError])

  function changeFilters(next: Filters) {
    setLoading(true)
    setFilters(next)
  }

  function retry() {
    setLoading(true)
    void refresh()
  }

  const filtered = Boolean(filters.status || filters.priority)

  return (
    <>
      <AppHeader user={user} onLogout={onLogout} />
      <main className="container">
        <h1>Minhas tarefas</h1>

        {assistedTask && (
          <TaskAssistantPanel
            key={assistedTask.id}
            task={assistedTask}
            onClose={() => setAssistedId(null)}
            onApiError={handleApiError}
          />
        )}

        <div className="grid">
          <div className="stack">
            <TaskForm onCreated={() => void refresh()} onApiError={handleApiError} />
            <section className="card stack">
              <div className="section-head">
                <h2>Tarefas {!loading && !error && <span className="count">({tasks.length})</span>}</h2>
                <TaskFilters value={filters} onChange={changeFilters} />
              </div>
              {loading ? (
                <Skeleton label="Carregando tarefas…" />
              ) : error ? (
                <ErrorState message={error} onRetry={retry} />
              ) : (
                <TaskList
                  tasks={tasks}
                  filtered={filtered}
                  onChanged={() => void refresh()}
                  onAssist={(task) => setAssistedId(task.id)}
                  onApiError={handleApiError}
                />
              )}
            </section>
          </div>

          <ChatPanel onTaskCreated={() => void refresh()} onApiError={handleApiError} />
        </div>
      </main>
    </>
  )
}
