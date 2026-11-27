import { useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/client'
import { getTaskAssistance } from '../api/tasks'
import { COMPLEXITY_LABEL, PRIORITY_LABEL } from '../labels'
import type { Task, TaskAssistance } from '../types'
import Badge from './Badge'
import ErrorState from './ErrorState'
import Skeleton from './Skeleton'

interface TaskAssistantPanelProps {
  task: Task
  onClose: () => void
  onApiError: (err: unknown) => boolean
}

export default function TaskAssistantPanel({ task, onClose, onApiError }: TaskAssistantPanelProps) {
  const [result, setResult] = useState<TaskAssistance | null>(null)
  const [error, setError] = useState<string | null>(null)
  const ref = useRef<HTMLElement>(null)

  // The panel renders above the list; bring it into view (matters on mobile).
  useEffect(() => {
    ref.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  }, [])

  // TasksPage keys this panel by task.id, so a new task remounts with fresh state.
  useEffect(() => {
    let ignore = false
    getTaskAssistance(task.id)
      .then((data) => {
        if (!ignore) setResult(data)
      })
      .catch((err) => {
        if (ignore || onApiError(err)) return
        setError(
          err instanceof ApiError && err.status === 503
            ? 'O assistente está indisponível agora.'
            : 'Não foi possível obter a ajuda da IA.',
        )
      })
    return () => {
      ignore = true
    }
  }, [task.id, onApiError])

  return (
    <section ref={ref} className="card stack assistant" aria-label="Ajuda da IA">
      <header className="section-head">
        <div>
          <p className="eyebrow">Ajuda da IA</p>
          <h2>{task.title}</h2>
        </div>
        <button type="button" className="secondary" onClick={onClose}>
          Fechar
        </button>
      </header>
      {error && <ErrorState message={error} />}
      {!result && !error && (
        <>
          <p className="muted">Analisando a tarefa… a IA pode levar alguns segundos.</p>
          <Skeleton label="Analisando a tarefa" rows={4} />
        </>
      )}
      {result && <AssistanceResult task={task} result={result} />}
    </section>
  )
}

function AssistanceResult({ task, result }: { task: Task; result: TaskAssistance }) {
  const samePriority = result.suggested_priority === task.priority
  return (
    <div className="stack">
      <p className="summary">{result.summary}</p>
      <div className="task-meta">
        <Badge tone={`complexity-${result.complexity}`}>
          Complexidade: {COMPLEXITY_LABEL[result.complexity]}
        </Badge>
        <Badge tone="neutral">Estimativa: {result.estimated_hours} h</Badge>
      </div>
      <div className="callout">
        <p className="priority-compare">
          <span>Prioridade atual</span>
          <Badge tone={task.priority}>{PRIORITY_LABEL[task.priority]}</Badge>
          <span aria-hidden="true">→</span>
          <span>sugerida</span>
          <Badge tone={result.suggested_priority}>{PRIORITY_LABEL[result.suggested_priority]}</Badge>
          {samePriority && <span className="muted">(mantida)</span>}
        </p>
        <p className="muted">{result.priority_reason}</p>
      </div>
      <div className="assist-columns">
        <div>
          <h3>Passos</h3>
          <ol className="steps">
            {result.steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>
        <div className="stack">
          {result.risks.length > 0 && (
            <div>
              <h3>Riscos</h3>
              <ul className="risks">
                {result.risks.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {result.clarifying_questions.length > 0 && (
            <div className="questions">
              <h3>Perguntas para esclarecer</h3>
              <ul>
                {result.clarifying_questions.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
