import { describe, expect, it, vi } from 'vitest'
import { listTasks } from '../api/tasks'

describe('listTasks', () => {
  it('sends only the filters that are set as query params', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async () => new Response('[]'))
    await listTasks({ status: 'completed', priority: '' })
    await listTasks({ status: '', priority: 'high' })
    await listTasks({})
    const urls = fetchMock.mock.calls.map(([url]) => String(url))
    expect(urls[0]).toMatch(/\/v1\/tasks\/\?status=completed$/)
    expect(urls[1]).toMatch(/\/v1\/tasks\/\?priority=high$/)
    expect(urls[2]).toMatch(/\/v1\/tasks\/$/)
  })
})
