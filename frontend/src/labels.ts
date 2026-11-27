import type { TaskPriority, TaskStatus } from './types'

// Portuguese labels shared by the list, the filters, the form and the assistant panel.
export const PRIORITY_LABEL: Record<TaskPriority, string> = {
  low: 'Baixa',
  medium: 'Média',
  high: 'Alta',
  urgent: 'Urgente',
}

export const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: 'Pendente',
  in_progress: 'Em andamento',
  completed: 'Concluída',
}

export const COMPLEXITY_LABEL = { low: 'Baixa', medium: 'Média', high: 'Alta' } as const
