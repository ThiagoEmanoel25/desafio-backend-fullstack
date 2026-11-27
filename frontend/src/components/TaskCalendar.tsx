import { useState } from 'react'
import type { Task } from '../types'
import TaskTags from './TaskTags'
import { tagTextColor } from '../tagColors'

export default function TaskCalendar({ tasks, onAssist, onEdit }: { tasks: Task[]; onAssist: (task: Task) => void; onEdit?: (task: Task) => void }) {
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1))
  const days = new Date(month.getFullYear(), month.getMonth() + 1, 0).getDate()
  const offset = (month.getDay() + 6) % 7
  const dated = tasks.filter(t => t.due_date)
  function move(delta: number) { setMonth(new Date(month.getFullYear(), month.getMonth() + delta, 1)) }
  return <div className="stack">
    <div className="section-head"><button className="secondary" onClick={() => move(-1)} aria-label="Mês anterior">←</button>
      <h3 aria-live="polite">{month.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })}</h3>
      <button className="secondary" onClick={() => move(1)} aria-label="Próximo mês">→</button></div>
    <p className="muted hint">Somente tarefas com prazo da lista atual. A primeira tag define a cor. Clique para {onEdit ? 'editar a tarefa' : 'pedir ajuda à IA'}.</p>
    <div className="calendar-scroll"><div className="calendar-grid">
      {['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'].map(day => <strong key={day}>{day}</strong>)}
      {Array.from({ length: offset }, (_, i) => <div key={`empty-${i}`} />)}
      {Array.from({ length: days }, (_, i) => {
        const key = `${month.getFullYear()}-${String(month.getMonth() + 1).padStart(2, '0')}-${String(i + 1).padStart(2, '0')}`
        return <div className="calendar-day" key={key}><time dateTime={key}>{i + 1}</time>
          {dated.filter(t => t.due_date === key).map(t => <div key={t.id} className="calendar-entry">
            <button className="calendar-task" style={t.tags?.[0] ? { backgroundColor: t.tags[0].color, borderColor: t.tags[0].color, color: tagTextColor(t.tags[0].color) } : undefined}
              onClick={() => (onEdit ?? onAssist)(t)}>{t.title}</button>
            <TaskTags tags={t.tags} />
          </div>)}
        </div>
      })}
    </div></div>
    {dated.length === 0 && <p>Nenhuma tarefa com prazo nesta lista. Adicione um prazo ao criar uma tarefa.</p>}
  </div>
}
