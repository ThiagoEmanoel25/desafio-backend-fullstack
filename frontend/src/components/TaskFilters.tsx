import { PRIORITY_LABEL, STATUS_LABEL } from '../labels'
import type { TaskFilters as Filters, TaskPriority, TaskStatus } from '../types'

interface TaskFiltersProps {
  value: Filters
  onChange: (filters: Filters) => void
  /** Hides the status filter (the Kanban columns are the statuses); its value is kept. */
  hideStatus?: boolean
}

export default function TaskFilters({ value, onChange, hideStatus = false }: TaskFiltersProps) {
  return (
    <div className="filters">
      {!hideStatus && (
        <label className="field">
          <span>Status</span>
          <select
            aria-label="Filtrar por status"
            value={value.status ?? ''}
            onChange={(e) => onChange({ ...value, status: e.target.value as TaskStatus | '' })}
          >
            <option value="">Todos</option>
            {Object.entries(STATUS_LABEL).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="field">
        <span>Prioridade</span>
        <select
          aria-label="Filtrar por prioridade"
          value={value.priority ?? ''}
          onChange={(e) => onChange({ ...value, priority: e.target.value as TaskPriority | '' })}
        >
          <option value="">Todas</option>
          {Object.entries(PRIORITY_LABEL).map(([v, label]) => (
            <option key={v} value={v}>
              {label}
            </option>
          ))}
        </select>
      </label>
    </div>
  )
}
