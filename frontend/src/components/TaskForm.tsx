import { useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { createTask } from '../api/tasks'
import { PRIORITY_LABEL } from '../labels'
import type { Task, TaskPriority } from '../types'

interface TaskFormProps {
  onCreated: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

export default function TaskForm({ onCreated, onApiError }: TaskFormProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState<TaskPriority>('medium')
  const [department, setDepartment] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const task = await createTask({
        due_date: dueDate || null,
        title,
        description: description || null,
        priority,
        department,
      })
      setTitle('')
      setDescription('')
      setPriority('medium')
      setDepartment('')
      setDueDate('')
      onCreated(task)
    } catch (err) {
      if (onApiError(err)) return
      setError(
        err instanceof ApiError && err.status === 422
          ? `Verifique os campos — ${err.message}`
          : 'Não foi possível criar a tarefa.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="card stack task-composer" id="new-task">
      <div><p className="eyebrow">Do plano à ação</p><h2>Nova tarefa</h2></div>
      <form onSubmit={handleSubmit} className="stack">
        <label className="input-label" htmlFor="task-title">O que precisa ser feito?</label>
        <input id="task-title"
          aria-label="Título"
          placeholder="Ex.: Revisar a proposta comercial"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          minLength={3}
        />
        <label className="input-label" htmlFor="task-description">Contexto <span className="muted">· opcional</span></label>
        <textarea id="task-description"
          aria-label="Descrição"
          placeholder="Inclua objetivos e detalhes para receber um plano melhor da IA."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div className="form-row">
          <select
            aria-label="Prioridade"
            value={priority}
            onChange={(e) => setPriority(e.target.value as TaskPriority)}
          >
            {Object.entries(PRIORITY_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input
            aria-label="Departamento"
            placeholder="Departamento"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            required
          />
        </div>
        <label className="input-label" htmlFor="task-due">Prazo · opcional</label>
        <input id="task-due" type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Criando…' : 'Criar tarefa'}
        </button>
      </form>
    </section>
  )
}
