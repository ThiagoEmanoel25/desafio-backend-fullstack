import { expect, test, vi } from 'vitest'
import { apiFetch } from '../api/client'
import { duplicateTask } from '../api/tasks'
import type { Task } from '../types'

vi.mock('../api/client', () => ({ apiFetch: vi.fn() }))

test('duplicate sends only editable data and resets identity and status', async () => {
  const task = {
    id: 'old-id', title: 'A'.repeat(200), description: 'Contexto', department: 'Ops',
    priority: 'urgent', status: 'completed', due_date: '2026-12-15',
    tags: [{ name: 'Urgente', color: '#ff0000' }],
  } as Task
  await duplicateTask(task)
  const [, options] = vi.mocked(apiFetch).mock.calls[0]
  const body = JSON.parse(options!.body as string)
  expect(body.title).toHaveLength(200)
  expect(body.title).toMatch(/\(cópia\)$/)
  expect(body.tags).toEqual(task.tags)
  expect(body.due_date).toBe(task.due_date)
  expect(body).not.toHaveProperty('id')
  expect(body).not.toHaveProperty('status')
  expect(body).not.toHaveProperty('user_id')
})
