import { useState, type FormEvent } from 'react'
import { login } from '../api/auth'
import { ApiError } from '../api/client'

interface LoginPageProps {
  onLogin: () => void
}

export default function LoginPage({ onLogin }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      onLogin()
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? 'E-mail ou senha inválidos'
          : 'Não foi possível entrar. Tente novamente.',
      )
      setLoading(false)
    }
  }

  return (
    <main className="login">
      <section className="login-story" aria-label="Sobre o Tarefas IA">
        <span className="login-monogram" aria-hidden="true">t.</span>
        <p className="eyebrow">Tarefas IA · Seu trabalho, com direção</p>
        <h2>Menos ruído.<br />Mais próximo<br />de concluir.</h2>
        <p>Reúna suas prioridades, transforme ideias em tarefas e encontre o próximo passo com seu assistente.</p>
        <div className="login-preview"><span>SEU PRÓXIMO PASSO</span><strong>Uma tarefa de cada vez.</strong><p>Organizar → Planejar → Concluir</p></div>
      </section>
      <form onSubmit={handleSubmit} className="card stack login-card">
        <div>
          <p className="brand">Tarefas IA</p>
          <h1>Entrar</h1>
          <p className="muted">Gerencie suas tarefas com ajuda de um assistente.</p>
        </div>
        <label className="input-label" htmlFor="login-email">E-mail</label>
        <input id="login-email" autoComplete="username"
          type="email"
          aria-label="E-mail"
          placeholder="E-mail"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label className="input-label" htmlFor="login-password">Senha</label>
        <input id="login-password" autoComplete="current-password"
          type="password"
          aria-label="Senha"
          placeholder="Senha"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={loading}>
          {loading ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </main>
  )
}
