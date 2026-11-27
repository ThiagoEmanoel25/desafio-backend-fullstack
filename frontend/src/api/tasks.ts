import { apiFetch } from './client'
import type { Task, TaskAssistance, TaskCreate, TaskFilters, TaskUpdate } from '../types'

// Empty filters are left out, so "Todos" lists everything.
export async function listTasks(filters: TaskFilters = {}): Promise<Task[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.priority) params.set('priority', filters.priority)
  const query = params.toString()
  return apiFetch<Task[]>(`/v1/tasks/${query ? `?${query}` : ''}`)
}

export async function createTask(data: TaskCreate): Promise<Task> {
  return apiFetch<Task>('/v1/tasks/', { method: 'POST', body: JSON.stringify(data) })
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
