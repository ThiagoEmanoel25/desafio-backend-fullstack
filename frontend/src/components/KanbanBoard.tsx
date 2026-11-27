import { useId, useRef, useState, type DragEvent } from 'react'
import { flushSync } from 'react-dom'
import { updateTask } from '../api/tasks'
import { PRIORITY_LABEL, STATUS_LABEL } from '../labels'
import type { Task, TaskStatus } from '../types'
import Badge from './Badge'

interface KanbanBoardProps {
  tasks: Task[]
  /** Called after a move is saved, so the parent reloads the tasks. */
  onChanged: () => void
  onAssist: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

/** One column per status, in the order of STATUS_LABEL. */
const COLUMNS = Object.keys(STATUS_LABEL) as TaskStatus[]

/**
 * A move shown before the parent's tasks have it: `saving` until the PATCH answers, then
 * kept until fresh tasks arrive, so the card does not jump back while the list reloads.
 */
interface Move {
  status: TaskStatus
  saving: boolean
}

/** The tasks in one column per status; a card moves by drag and drop or by its "Mover para" select. */
export default function KanbanBoard({ tasks, onChanged, onAssist, onApiError }: KanbanBoardProps) {
  const [moves, setMoves] = useState<Record<string, Move>>({})
  const [movesBase, setMovesBase] = useState(tasks)
  const [draggedId, setDraggedId] = useState<string | null>(null)
  const [overColumn, setOverColumn] = useState<TaskStatus | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [announcement, setAnnouncement] = useState('')
  const boardRef = useRef<HTMLDivElement>(null)
  const id = useId()

  // Fresh tasks already carry the saved moves: keep only the ones still saving
  // (state adjusted while rendering, as in the React docs, instead of in an effect).
  if (movesBase !== tasks) {
    setMovesBase(tasks)
    setMoves((current) => Object.fromEntries(Object.entries(current).filter(([, move]) => move.saving)))
  }

  const statusOf = (task: Task) => moves[task.id]?.status ?? task.status
  const dragged = tasks.find((task) => task.id === draggedId)
  // Its own column (or a card still saving) does not take the drop.
  const canDrop = (column: TaskStatus) =>
    dragged !== undefined && !moves[dragged.id]?.saving && statusOf(dragged) !== column

  const findCard = (taskId: string) =>
    boardRef.current?.querySelector<HTMLElement>(`[data-task-id="${taskId}"]`)

  async function move(task: Task, to: TaskStatus) {
    const previous = moves[task.id]
    if (previous?.saving || statusOf(task) === to) return
    setError(null)
    setAnnouncement('')
    setMoves((current) => ({ ...current, [task.id]: { status: to, saving: true } }))
    try {
      await updateTask(task.id, { status: to })
      setMoves((current) => ({ ...current, [task.id]: { status: to, saving: false } }))
      setAnnouncement(`“${task.title}” movida para ${STATUS_LABEL[to]}.`)
      onChanged()
    } catch (err) {
      // Back to the column it came from, and the focus with it if it was on the card.
      const hadFocus = findCard(task.id)?.contains(document.activeElement) ?? false
      flushSync(() =>
        setMoves((current) => {
          const next = { ...current }
          if (previous) next[task.id] = previous
          else delete next[task.id]
          return next
        }),
      )
      if (hadFocus) findCard(task.id)?.focus()
      if (!onApiError(err)) setError('Não foi possível mover a tarefa.')
    }
  }

  // The card changes columns, so React mounts a new select: keep the focus on the card.
  function moveWithSelect(task: Task, to: TaskStatus) {
    flushSync(() => void move(task, to))
    findCard(task.id)?.focus()
  }

  function handleDragStart(event: DragEvent<HTMLLIElement>, task: Task) {
    event.dataTransfer.effectAllowed = 'move'
    event.dataTransfer.setData('text/plain', task.id) // Firefox only starts a drag with data
    setDraggedId(task.id)
  }

  function endDrag() {
    setDraggedId(null)
    setOverColumn(null)
  }

  // Taking dragover (preventDefault) is what makes the browser allow the drop.
  function handleDragOver(event: DragEvent<HTMLElement>, column: TaskStatus) {
    if (!canDrop(column)) return
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
    setOverColumn(column)
  }

  // dragleave also fires when the pointer goes onto a card inside the column.
  function handleDragLeave(event: DragEvent<HTMLElement>, column: TaskStatus) {
    if (event.currentTarget.contains(event.relatedTarget as Node | null)) return
    setOverColumn((current) => (current === column ? null : current))
  }

  function handleDrop(event: DragEvent<HTMLElement>, column: TaskStatus) {
    event.preventDefault()
    const task = dragged
    const accepted = canDrop(column)
    endDrag()
    if (task && accepted) void move(task, column)
  }

  return (
    <div className="kanban">
      <p className="muted hint">Arraste os cartões entre as colunas ou use “Mover para”.</p>
      {error && <p className="error" role="alert">{error}</p>}
      <p className="sr-only" role="status" aria-live="polite">
        {announcement}
      </p>
      <div ref={boardRef} className="kanban-board">
        {COLUMNS.map((column) => {
          const cards = tasks.filter((task) => statusOf(task) === column)
          const headingId = `${id}-${column}`
          return (
            <section
              key={column}
              className={overColumn === column ? 'kanban-column is-over' : 'kanban-column'}
              aria-labelledby={headingId}
              onDragEnter={(e) => handleDragOver(e, column)}
              onDragOver={(e) => handleDragOver(e, column)}
              onDragLeave={(e) => handleDragLeave(e, column)}
              onDrop={(e) => handleDrop(e, column)}
            >
              <h3 id={headingId} className="kanban-heading">
                {STATUS_LABEL[column]}{' '}
                {/* The spaces sit outside the spans: each span's text is trimmed in the name. */}
                <span className="kanban-count">
                  {cards.length}{' '}
                  <span className="sr-only">{cards.length === 1 ? 'tarefa' : 'tarefas'}</span>
                </span>
              </h3>
              {cards.length === 0 ? (
                <p className="kanban-empty">Nenhuma tarefa</p>
              ) : (
                <ul className="kanban-cards">
                  {cards.map((task) => {
                    const status = statusOf(task)
                    const saving = moves[task.id]?.saving ?? false
                    return (
                      <li
                        key={task.id}
                        data-task-id={task.id}
                        className={`kanban-card task-${status}`}
                        tabIndex={-1}
                        draggable={!saving}
                        aria-busy={saving}
                        onDragStart={(e) => handleDragStart(e, task)}
                        onDragEnd={endDrag}
                      >
                        <strong className="task-title">{task.title}</strong>
                        <div className="task-meta">
                          <Badge tone={task.priority}>{PRIORITY_LABEL[task.priority]}</Badge>
                          <span className="muted">{task.department}</span>
                          {task.due_date && (
                            <time dateTime={task.due_date}>Prazo: {task.due_date.split('-').reverse().join('/')}</time>
                          )}
                        </div>
                        {task.description && <p className="task-desc kanban-desc">{task.description}</p>}
                        <div className="kanban-actions">
                          <label className="kanban-move">
                            <span aria-hidden="true">Mover para</span>
                            <select
                              aria-label={`Mover para: ${task.title}`}
                              value={status}
                              disabled={saving}
                              onChange={(e) => moveWithSelect(task, e.target.value as TaskStatus)}
                            >
                              {COLUMNS.map((value) => (
                                <option key={value} value={value}>
                                  {STATUS_LABEL[value]}
                                </option>
                              ))}
                            </select>
                          </label>
                          <button type="button" className="secondary" onClick={() => onAssist(task)}>
                            Pedir ajuda à IA
                          </button>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </section>
          )
        })}
      </div>
    </div>
  )
}
