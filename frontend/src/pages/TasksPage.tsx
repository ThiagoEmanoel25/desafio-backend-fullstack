import { useCallback, useEffect, useId, useRef, useState, type KeyboardEvent } from 'react'
import { ApiError } from '../api/client'
import { getCurrentUser } from '../api/auth'
import { listTasks } from '../api/tasks'
import AppHeader from '../components/AppHeader'
import ChatPopup from '../components/ChatPopup'
import TaskAssistantPanel from '../components/TaskAssistantPanel'
import ErrorState from '../components/ErrorState'
import KanbanBoard from '../components/KanbanBoard'
import Skeleton from '../components/Skeleton'
import TaskFilters from '../components/TaskFilters'
import TaskForm from '../components/TaskForm'
import TaskList from '../components/TaskList'
import TaskCalendar from '../components/TaskCalendar'
import type { Task, TaskFilters as Filters, User } from '../types'

interface TasksPageProps {
  onLogout: () => void
}

type View = 'list' | 'kanban' | 'calendar'

const VIEWS: { id: View; label: string }[] = [
  { id: 'list', label: 'Lista' },
  { id: 'kanban', label: 'Kanban' },
  { id: 'calendar', label: 'Calendário' },
]

/** The API's maximum page size, so the board's columns do not miss tasks. */
const TASK_LIMIT = 100

/** Main page: owns the task list; children report mutations and API errors back. */
export default function TasksPage({ onLogout }: TasksPageProps) {
  const [tasks, setTasks] = useState<Task[]>([])
  const [view, setView] = useState<View>('list')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<Filters>({})
  const [user, setUser] = useState<User | null>(null)
  const [assistedId, setAssistedId] = useState<string | null>(null)
  // Derived from the list, so a deleted task closes the panel and an edited one stays fresh.
  const assistedTask = tasks.find((t) => t.id === assistedId) ?? null
  const tabsId = useId()
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])

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

  // The Kanban columns are the statuses, so the board loads every status; the status
  // filter keeps its value and applies again in the list and the calendar.
  const statusFilter = view === 'kanban' ? undefined : filters.status
  const priorityFilter = filters.priority

  // Only the latest request may write the list, so a slow response for an old
  // filter cannot overwrite the one the user picked after it.
  const requestId = useRef(0)
  const refresh = useCallback(async () => {
    const id = ++requestId.current
    try {
      const data = await listTasks({ status: statusFilter, priority: priorityFilter }, TASK_LIMIT)
      if (id !== requestId.current) return
      setTasks(data)
      setError(null)
    } catch (err) {
      if (id !== requestId.current) return
      if (!handleApiError(err)) setError('Não foi possível carregar as tarefas.')
    } finally {
      if (id === requestId.current) setLoading(false)
    }
  }, [statusFilter, priorityFilter, handleApiError])

  // Runs on mount and every time the query changes (refresh depends on it).
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- fetch; state is set after await
    void refresh()
  }, [refresh])

  // Callbacks that finish later (a chat reply, a save) captured the refresh of the render
  // that started them; through this ref they reload with the filter and tab shown now.
  const refreshRef = useRef(refresh)
  useEffect(() => {
    refreshRef.current = refresh
  }, [refresh])
  const reload = useCallback(() => void refreshRef.current(), [])

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

  function selectView(next: View) {
    if (next === view) return
    // Entering or leaving the Kanban changes the query only when a status is chosen.
    if (filters.status && (next === 'kanban') !== (view === 'kanban')) setLoading(true)
    setView(next)
  }

  // Tabs pattern: arrows (and Home/End) move and select; only the active tab is in the Tab order.
  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const last = VIEWS.length - 1
    const targets: Record<string, number> = {
      ArrowRight: index === last ? 0 : index + 1,
      ArrowLeft: index === 0 ? last : index - 1,
      Home: 0,
      End: last,
    }
    const target = targets[event.key]
    if (target === undefined) return
    event.preventDefault()
    selectView(VIEWS[target].id)
    tabRefs.current[target]?.focus()
  }

  const assist = (task: Task) => setAssistedId(task.id)
  const filtered = Boolean(filters.status || filters.priority)

  function viewContent() {
    if (loading) return <Skeleton label="Carregando tarefas…" />
    if (error) return <ErrorState message={error} onRetry={retry} />
    if (view === 'kanban') {
      return <KanbanBoard tasks={tasks} onChanged={reload} onAssist={assist} onApiError={handleApiError} />
    }
    if (view === 'calendar') return <TaskCalendar tasks={tasks} onAssist={assist} />
    return (
      <TaskList tasks={tasks} filtered={filtered} onChanged={reload} onAssist={assist} onApiError={handleApiError} />
    )
  }

  return (
    <>
      <AppHeader user={user} onLogout={onLogout} />
      <main className="container workspace">
        <div className="workspace-heading">
          <div><p className="eyebrow">Seu espaço de trabalho</p>
            <h1>Clareza para o seu dia.</h1>
            <p className="muted">Organize o que importa. Conte com a IA para dar o próximo passo.</p>
          </div>
          <a className="quick-create" href="#new-task">+ Nova tarefa</a>
        </div>
        {!loading && !error && <div className="workspace-stats" aria-label="Resumo das tarefas exibidas">
          <div><span>Na lista atual</span><strong>{tasks.length}</strong></div>
          <div><span>Em andamento</span><strong>{tasks.filter(t => t.status === 'in_progress').length}</strong></div>
          <div><span>Concluídas</span><strong>{tasks.filter(t => t.status === 'completed').length}</strong></div>
        </div>}

        {assistedTask && (
          <TaskAssistantPanel
            key={assistedTask.id}
            task={assistedTask}
            onClose={() => setAssistedId(null)}
            onApiError={handleApiError}
          />
        )}

        <div className="grid">
          <TaskForm onCreated={reload} onApiError={handleApiError} />
          <section className="card stack">
            <div className="section-head">
              <h2>Tarefas {!loading && !error && <span className="count">({tasks.length})</span>}</h2>
              <TaskFilters value={filters} onChange={changeFilters} hideStatus={view === 'kanban'} />
            </div>
            <div className="row view-tabs" role="tablist" aria-label="Visualização das tarefas">
              {VIEWS.map(({ id, label }, index) => {
                const selected = view === id
                return (
                  <button
                    key={id}
                    ref={(el) => {
                      tabRefs.current[index] = el
                    }}
                    type="button"
                    role="tab"
                    id={`${tabsId}-tab-${id}`}
                    aria-selected={selected}
                    aria-controls={`${tabsId}-panel-${id}`}
                    tabIndex={selected ? 0 : -1}
                    className={selected ? undefined : 'secondary'}
                    onClick={() => selectView(id)}
                    onKeyDown={(e) => handleTabKeyDown(e, index)}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
            {!loading && !error && tasks.length === TASK_LIMIT && (
              <p className="muted hint">Mostrando as {TASK_LIMIT} tarefas mais recentes.</p>
            )}
            {/* One panel per tab, so every aria-controls points at an element; only the active one has content. */}
            {VIEWS.map(({ id }) => (
              <div
                key={id}
                role="tabpanel"
                id={`${tabsId}-panel-${id}`}
                aria-labelledby={`${tabsId}-tab-${id}`}
                className="stack tab-panel"
                hidden={view !== id}
                tabIndex={0}
              >
                {view === id && viewContent()}
              </div>
            ))}
          </section>
        </div>

        <ChatPopup onTaskCreated={reload} onApiError={handleApiError} />
      </main>
    </>
  )
}
