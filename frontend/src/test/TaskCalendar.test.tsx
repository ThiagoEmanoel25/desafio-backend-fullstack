import { render, screen } from '@testing-library/react'
import { expect, test } from 'vitest'
import TaskCalendar from '../components/TaskCalendar'
import type { Task } from '../types'

test('shows only tasks with deadlines', () => {
  const now = new Date()
  const date = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-15`
  const base = { status: 'pending', priority: 'medium', department: 'Ops' } as Task
  render(<TaskCalendar tasks={[
    { ...base, id: '1', title: 'Com prazo', due_date: date },
    { ...base, id: '2', title: 'Sem prazo', due_date: null },
  ]} onAssist={() => {}} />)
  expect(screen.getByRole('button', { name: 'Com prazo' })).toBeInTheDocument()
  expect(screen.queryByText('Sem prazo')).not.toBeInTheDocument()
})
