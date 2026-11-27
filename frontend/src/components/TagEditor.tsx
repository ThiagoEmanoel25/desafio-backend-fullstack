import { useState } from 'react'
import type { TaskTag } from '../types'

export default function TagEditor({ tags, onChange, disabled }: {
  tags: TaskTag[]; onChange: (tags: TaskTag[]) => void; disabled: boolean
}) {
  const [name, setName] = useState('')
  const [color, setColor] = useState('#186451')
  function add() {
    const trimmed = name.trim()
    if (!trimmed || tags.length >= 8) return
    onChange([...tags, { name: trimmed, color }])
    setName('')
  }
  return <fieldset className="tag-editor" disabled={disabled}>
    <legend>Tags e cores</legend>
    <p className="muted hint">Até 8 tags. A primeira define a cor da tarefa no calendário.</p>
    {tags.map((tag, index) => <div className="row tag-editor-row" key={index}>
      <input aria-label={`Nome da tag ${index + 1}`} maxLength={30} required value={tag.name}
        onChange={e => onChange(tags.map((t, i) => i === index ? { ...t, name: e.target.value } : t))} />
      <input type="color" aria-label={`Cor da tag ${index + 1}`} value={tag.color}
        onChange={e => onChange(tags.map((t, i) => i === index ? { ...t, color: e.target.value } : t))} />
      <button type="button" className="ghost danger-text" aria-label={`Remover tag ${index + 1}`}
        onClick={() => onChange(tags.filter((_, i) => i !== index))}>Remover</button>
    </div>)}
    {tags.length < 8 && <div className="row tag-editor-row">
      <input aria-label="Nova tag" placeholder="Ex.: Cliente, pessoal..." maxLength={30} value={name}
        onChange={e => setName(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); add() } }} />
      <input type="color" aria-label="Cor da nova tag" value={color} onChange={e => setColor(e.target.value)} />
      <button type="button" className="secondary" disabled={!name.trim()} onClick={add}>Adicionar tag</button>
    </div>}
  </fieldset>
}
