import { useEffect, useState } from 'react'
import { apiFetch, ApiError } from '../api/client'

interface Tenant {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_admin: boolean
}

export default function AdminPage({ onBack, onLogout }: {
  onBack: () => void; onLogout: () => void
}) {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [skip, setSkip] = useState(0)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let active = true
    apiFetch<Tenant[]>(`/v1/admin/tenants?skip=${skip}&limit=20`)
      .then(data => { if (active) setTenants(data) })
      .catch(err => {
        if (err instanceof ApiError && err.status === 401) onLogout()
        if (active) setError('Não foi possível carregar os tenants.')
      })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [skip, onLogout])
  async function toggle(tenant: Tenant) {
    setBusy(true)
    setError('')
    try {
      const updated = await apiFetch<Tenant>(`/v1/admin/tenants/${tenant.id}`, {
        method: 'PATCH', body: JSON.stringify({ is_active: !tenant.is_active }),
      })
      setTenants(items => items.map(item => item.id === updated.id ? updated : item))
    } catch {
      setError('Não foi possível atualizar a conta.')
    } finally { setBusy(false) }
  }
  return <main className="container stack">
    <header className="row between"><h1>Administração de tenants</h1>
      <button onClick={onBack}>Voltar às tarefas</button></header>
    <p>Cada tenant corresponde a uma conta de usuário.</p>
    {error && <p role="alert">{error}</p>}
    {loading ? <p role="status">Carregando...</p> : <>
      {tenants.length === 0 && <p>Nenhuma conta nesta página.</p>}
      {tenants.map(tenant => <article className="card row between" key={tenant.id}>
        <div><strong>{tenant.full_name}</strong><p>{tenant.email}</p>
          <span>{tenant.is_admin ? 'Administrador' : tenant.is_active ? 'Ativo' : 'Inativo'}</span></div>
        {!tenant.is_admin && <button disabled={busy} onClick={() => void toggle(tenant)}>
          {tenant.is_active ? 'Desativar' : 'Ativar'}</button>}
      </article>)}
    </>}
    <nav className="row" aria-label="Paginação de tenants">
      <button disabled={loading || skip === 0} onClick={() => { setLoading(true); setSkip(skip - 20) }}>Anterior</button>
      <button disabled={loading || tenants.length < 20} onClick={() => { setLoading(true); setSkip(skip + 20) }}>Próxima</button>
    </nav>
  </main>
}
