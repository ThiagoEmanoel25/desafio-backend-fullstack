import { apiFetch } from './client'
import type { Task, TaskAssistance, TaskCreate, TaskUpdate } from '../types'

export async function listTasks(): Promise<Task[]> {
  return apiFetch<Task[]>('/v1/tasks/')
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
