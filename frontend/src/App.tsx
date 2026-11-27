import { useEffect, useState } from 'react'
import { getCurrentUser } from './api/auth'
import AdminPage from './pages/AdminPage'
import { isAuthenticated, logout } from './api/auth'
import LoginPage from './pages/LoginPage'
import TasksPage from './pages/TasksPage'

// Root component — already implemented.
// Shows the login page or the tasks page depending on the stored token.
// (Using a router library such as react-router is optional.)
export default function App() {
  const [loggedIn, setLoggedIn] = useState(isAuthenticated())
  const [isAdmin, setIsAdmin] = useState(false)
  const [adminOpen, setAdminOpen] = useState(false)
  useEffect(() => {
    let active = true
    if (loggedIn) getCurrentUser().then(user => {
      if (active) setIsAdmin(Boolean(user.is_admin))
    }).catch(() => { if (active) setIsAdmin(false) })
    return () => { active = false }
  }, [loggedIn])

  function handleLogout() {
    logout()
    setLoggedIn(false)
    setIsAdmin(false)
    setAdminOpen(false)
  }

  if (!loggedIn) {
    return <LoginPage onLogin={() => setLoggedIn(true)} />
  }

  if (isAdmin && adminOpen) return <AdminPage onBack={() => setAdminOpen(false)} onLogout={handleLogout} />
  return <>{isAdmin && <button onClick={() => setAdminOpen(true)}>Administrar tenants</button>}
    <TasksPage onLogout={handleLogout} /></>
}
