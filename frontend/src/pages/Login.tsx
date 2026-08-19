import { useState, useEffect, type FormEvent } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Mail, Lock, Eye, EyeOff, Loader2, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, token, initialized } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    const state = location.state as { success?: string } | null
    if (state?.success) {
      setSuccessMsg(state.success)
      window.history.replaceState({}, '')
    }
  }, [location])

  useEffect(() => {
    if (initialized && token) {
      navigate('/dashboard', { replace: true })
    }
  }, [initialized, token, navigate])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccessMsg('')

    if (!email.trim()) {
      setError('Email is required')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address')
      return
    }
    if (!password) {
      setError('Password is required')
      return
    }

    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4"
      style={{ backgroundColor: 'var(--bg-app)' }}
    >
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center gap-2.5">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent-purple shadow-lg shadow-primary/25">
              <span className="text-lg font-bold text-white">F</span>
            </div>
            <span className="bg-gradient-to-r from-primary to-accent-purple bg-clip-text text-2xl font-bold text-transparent">
              FINORA
            </span>
          </div>
          <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Welcome back
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Sign in to your account
          </p>
        </div>

        <div
          className="rounded-2xl border p-8 shadow-2xl shadow-black/30"
          style={{
            borderColor: 'var(--border-default)',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
          {successMsg && (
            <div className="mb-6 flex items-center gap-2 rounded-lg border border-success/20 bg-success/10 px-4 py-3 text-sm text-success">
              <span className="flex-1">{successMsg}</span>
              <button
                type="button"
                onClick={() => setSuccessMsg('')}
                className="shrink-0 rounded p-0.5 hover:bg-success/20"
              >
                <X size={14} />
              </button>
            </div>
          )}

          {error && (
            <div className="mb-6 flex items-center gap-2 rounded-lg border border-danger/20 bg-danger/10 px-4 py-3 text-sm text-danger">
              <span className="flex-1">{error}</span>
              <button
                type="button"
                onClick={() => setError('')}
                className="shrink-0 rounded p-0.5 hover:bg-danger/20"
              >
                <X size={14} />
              </button>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="login-email"
                className="mb-2 block text-sm font-medium"
                style={{ color: 'var(--text-secondary)' }}
              >
                Email
              </label>
              <div className="relative">
                <Mail
                  size={18}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-tertiary)' }}
                />
                <input
                  id="login-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  autoComplete="email"
                  className="w-full rounded-lg border px-3 py-2.5 pl-11 text-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
                  style={{
                    borderColor: 'var(--border-default)',
                    backgroundColor: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                  }}
                />
              </div>
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="mb-2 block text-sm font-medium"
                style={{ color: 'var(--text-secondary)' }}
              >
                Password
              </label>
              <div className="relative">
                <Lock
                  size={18}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-tertiary)' }}
                />
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  className="w-full rounded-lg border px-3 py-2.5 pl-11 pr-11 text-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
                  style={{
                    borderColor: 'var(--border-default)',
                    backgroundColor: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-0.5 transition-colors"
                  style={{ color: 'var(--text-tertiary)' }}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-primary to-[#6366F1] py-2.5 text-sm font-semibold text-white shadow-lg shadow-primary/25 transition-all hover:shadow-xl hover:shadow-primary/30 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
          Don&apos;t have an account?{' '}
          <Link
            to="/register"
            className="font-medium text-primary transition-colors hover:text-[#6B8FFF]"
          >
            Sign up
          </Link>
        </p>
      </div>
    </div>
  )
}
