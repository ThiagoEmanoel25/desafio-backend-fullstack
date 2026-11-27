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
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const task = await createTask({
        title,
        description: description || null,
        priority,
        department,
      })
      setTitle('')
      setDescription('')
      setPriority('medium')
      setDepartment('')
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
    <section className="card stack">
      <h2>Nova tarefa</h2>
      <form onSubmit={handleSubmit} className="stack">
        <input
          aria-label="Título"
          placeholder="Título"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          minLength={3}
        />
        <textarea
          aria-label="Descrição"
          placeholder="Descrição (opcional)"
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
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Criando…' : 'Criar tarefa'}
        </button>
      </form>
    </section>
  )
}
