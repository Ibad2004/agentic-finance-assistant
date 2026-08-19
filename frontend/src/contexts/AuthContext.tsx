import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'

export interface User {
  email: string
  name: string
}

interface AuthContextType {
  token: string | null
  user: User | null
  initialized: boolean
  login: (email: string, password: string) => Promise<void>
  register: (name: string, email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

const TOKEN_KEY = 'finora_token'
const USER_KEY = 'finora_user'

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function clearStoredAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken())
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem(USER_KEY)
    try {
      return stored ? (JSON.parse(stored) as User) : null
    } catch {
      return null
    }
  })
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setInitialized(true), 50)
    return () => clearTimeout(t)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || 'Invalid email or password')
    }

    const data = await response.json()
    const newToken = data.access_token
    const newUser: User = {
      email: data.email ?? email,
      name: data.full_name ?? data.name ?? email.split('@')[0],
    }

    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
    setToken(newToken)
    setUser(newUser)
  }, [])

  const register = useCallback(async (name: string, email: string, password: string) => {
    const response = await fetch('/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ full_name: name, email, password }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      if (response.status === 409) {
        throw new Error('An account with this email already exists')
      }
      throw new Error(data.detail || 'Registration failed. Please try again.')
    }
  }, [])

  const logout = useCallback(() => {
    clearStoredAuth()
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, user, initialized, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
