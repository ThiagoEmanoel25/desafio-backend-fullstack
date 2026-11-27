import { useEffect, useRef, useState, type FormEvent } from 'react'
import { ApiError } from '../api/client'
import { createTask, updateTask } from '../api/tasks'
import { PRIORITY_LABEL, STATUS_LABEL } from '../labels'
import type { Task, TaskPriority, TaskStatus, TaskTag } from '../types'
import TagEditor from './TagEditor'

interface TaskFormProps {
  task?: Task
  onCancel?: () => void
  onCreated: (task: Task) => void
  onApiError: (err: unknown) => boolean
}

export default function TaskForm({ onCreated, onApiError, task, onCancel }: TaskFormProps) {
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [priority, setPriority] = useState<TaskPriority>(task?.priority ?? 'medium')
  const [department, setDepartment] = useState(task?.department ?? '')
  const [dueDate, setDueDate] = useState(task?.due_date ?? '')
  const [status, setStatus] = useState<TaskStatus>(task?.status ?? 'pending')
  const [tags, setTags] = useState<TaskTag[]>(task?.tags ?? [])
  const titleRef = useRef<HTMLInputElement>(null)
  useEffect(() => { if (task) titleRef.current?.focus() }, [task])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting) return
    setError(null)
    setSubmitting(true)
    try {
      const data = {
        due_date: dueDate || null,
        title,
        description: description || null,
        priority,
        department,
        tags,
      }
      const saved = task ? await updateTask(task.id, { ...data, status }) : await createTask(data)
      setTitle('')
      setDescription('')
      setPriority('medium')
      setDepartment('')
      setDueDate('')
      setTags([])
      onCreated(saved)
    } catch (err) {
      if (onApiError(err)) return
      setError(
        err instanceof ApiError && err.status === 422
          ? `Verifique os campos — ${err.message}`
          : 'Não foi possível salvar a tarefa.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="card stack task-composer" id="new-task">
      <div><p className="eyebrow">Do plano à ação</p><h2>{task ? 'Editar tarefa' : 'Nova tarefa'}</h2></div>
      <form onSubmit={handleSubmit} className="stack">
        <fieldset className="stack form-fields" disabled={submitting}>
        <label className="input-label" htmlFor="task-title">O que precisa ser feito?</label>
        <input id="task-title" ref={titleRef} maxLength={200} disabled={submitting}
          aria-label="Título"
          placeholder="Ex.: Revisar a proposta comercial"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          minLength={3}
        />
        <label className="input-label" htmlFor="task-description">Contexto <span className="muted">· opcional</span></label>
        <textarea id="task-description" maxLength={2000}
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
            minLength={2}
            maxLength={100}
          />
        </div>
        <label className="input-label" htmlFor="task-due">Prazo · opcional</label>
        <input id="task-due" type="date" value={dueDate} onChange={e => setDueDate(e.target.value)} />
        {task && <label className="field">Status<select aria-label="Status da tarefa" value={status}
          onChange={e => setStatus(e.target.value as TaskStatus)}>
          {Object.entries(STATUS_LABEL).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
        </select></label>}
        <TagEditor tags={tags} onChange={setTags} disabled={submitting} />
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? 'Salvando…' : task ? 'Salvar alterações' : 'Criar tarefa'}
        </button>
        {task && <button type="button" className="secondary" disabled={submitting} onClick={onCancel}>Cancelar edição</button>}
        </fieldset>
      </form>
    </section>
  )
}
