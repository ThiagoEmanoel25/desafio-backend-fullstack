import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getTaskAssistance } from '../api/tasks'
import type { Task, TaskAssistance } from '../types'

interface TaskAssistantPanelProps {
  task: Task
  onClose: () => void
  onApiError: (err: unknown) => boolean
}

export default function TaskAssistantPanel({ task, onClose, onApiError }: TaskAssistantPanelProps) {
  const [result, setResult] = useState<TaskAssistance | null>(null)
  const [error, setError] = useState<string | null>(null)

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
    <section className="card stack">
      <header className="row between">
        <h2>Ajuda da IA: {task.title}</h2>
        <button onClick={onClose}>Fechar</button>
      </header>
      {error && <p className="error">{error}</p>}
      {!result && !error && (
        <p className="muted">Analisando a tarefa… a IA pode levar alguns segundos.</p>
      )}
      {result && (
        <div className="stack">
          <p>{result.summary}</p>
          <p>
            <strong>Complexidade:</strong> {result.complexity} ·{' '}
            <strong>Estimativa:</strong> {result.estimated_hours} h
          </p>
          <p>
            <strong>Prioridade sugerida:</strong> {result.suggested_priority} —{' '}
            {result.priority_reason}
          </p>
          <div>
            <strong>Passos</strong>
            <ol>
              {result.steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          </div>
          <div>
            <strong>Riscos</strong>
            <ul>
              {result.risks.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
          <div>
            <strong>Perguntas para esclarecer</strong>
            <ul>
              {result.clarifying_questions.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  )
}
