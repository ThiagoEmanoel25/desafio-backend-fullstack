import { apiFetch } from './client'
import type { Task, TaskAssistance, TaskCreate, TaskFilters, TaskUpdate } from '../types'

// Empty filters are left out, so "Todos" lists everything. Without `limit` the API
// sends 20 tasks; it accepts up to 100.
export async function listTasks(filters: TaskFilters = {}, limit?: number): Promise<Task[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  if (limit) params.set('limit', String(limit))
  const query = params.toString()
  return apiFetch<Task[]>(`/v1/tasks/${query ? `?${query}` : ''}`)
}

export async function createTask(data: TaskCreate): Promise<Task> {
  return apiFetch<Task>('/v1/tasks/', { method: 'POST', body: JSON.stringify(data) })
}

export async function duplicateTask(task: Task): Promise<Task> {
  // A new owner-scoped POST gives it a new id and resets status to pending.
  return createTask({
    title: `${Array.from(task.title).slice(0, 192).join('')} (cópia)`,
    description: task.description, priority: task.priority,
    department: task.department, due_date: task.due_date ?? null,
    tags: task.tags ?? [],
  })
}

export async function updateTask(id: string, data: TaskUpdate): Promise<Task> {
  return apiFetch<Task>(`/v1/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export async function deleteTask(id: string): Promise<void> {
  return apiFetch<void>(`/v1/tasks/${id}`, { method: 'DELETE' })
}

export async function getTaskAssistance(id: string): Promise<TaskAssistance> {
  return apiFetch<TaskAssistance>(`/v1/tasks/${id}/assist`, { method: 'POST' })
}
