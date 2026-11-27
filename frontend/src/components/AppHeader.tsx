import type { User } from '../types'

interface AppHeaderProps {
  user: User | null
  onLogout: () => void
}

export default function AppHeader({ user, onLogout }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div className="container app-header-inner">
        <span className="brand">Tarefas IA</span>
        <div className="row">
          {user && (
            <span className="user" title={user.email}>
              {user.full_name || user.email}
            </span>
          )}
          <button type="button" className="secondary" onClick={onLogout}>
            Sair
          </button>
        </div>
      </div>
    </header>
  )
}
