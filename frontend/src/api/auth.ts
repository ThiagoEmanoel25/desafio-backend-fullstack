import { apiFetch, tokenStorage } from './client'
import type { TokenResponse, User } from '../types'

export async function login(email: string, password: string): Promise<void> {
  // OAuth2PasswordRequestForm: form data, e-mail goes in `username`.
  const { access_token } = await apiFetch<TokenResponse>('/v1/auth/login', {
    method: 'POST',
    body: new URLSearchParams({ username: email, password }),
  })
  tokenStorage.set(access_token)
}

export function logout(): void {
  tokenStorage.clear()
}

export function isAuthenticated(): boolean {
  return tokenStorage.get() !== null
}

export async function getCurrentUser(): Promise<User> {
  return apiFetch<User>('/v1/auth/me')
}
