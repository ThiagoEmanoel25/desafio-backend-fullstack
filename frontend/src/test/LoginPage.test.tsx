import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import LoginPage from '../pages/LoginPage'

function mockFetch(status: number, body: unknown) {
  return vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }),
  )
}

async function submit(email: string, password: string) {
  const user = userEvent.setup()
  await user.type(screen.getByLabelText('E-mail'), email)
  await user.type(screen.getByLabelText('Senha'), password)
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

afterEach(() => localStorage.clear())

describe('LoginPage', () => {
  it('shows the API error on 401 and keeps no token', async () => {
    mockFetch(401, { detail: 'Incorrect email or password' })
    const onLogin = vi.fn()
    render(<LoginPage onLogin={onLogin} />)
    await submit('ana@example.com', 'wrong')
    expect(await screen.findByRole('alert')).toHaveTextContent('E-mail ou senha inválidos')
    expect(onLogin).not.toHaveBeenCalled()
    expect(localStorage.getItem('access_token')).toBeNull()
  })

  it('saves the token and calls onLogin on success', async () => {
    const fetchMock = mockFetch(200, { access_token: 'jwt-123', token_type: 'bearer' })
    const onLogin = vi.fn()
    render(<LoginPage onLogin={onLogin} />)
    await submit('ana@example.com', 'password123')
    await vi.waitFor(() => expect(onLogin).toHaveBeenCalled())
    expect(localStorage.getItem('access_token')).toBe('jwt-123')
    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toMatch(/\/v1\/auth\/login$/)
    expect((init!.body as URLSearchParams).get('username')).toBe('ana@example.com')
  })
})
