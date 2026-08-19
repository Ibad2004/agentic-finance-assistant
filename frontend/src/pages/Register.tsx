import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { User, Mail, Lock, Eye, EyeOff, Loader2, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

export default function Register() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!name.trim()) {
      setError('Full name is required')
      return
    }
    if (!email.trim()) {
      setError('Email is required')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await register(name.trim(), email, password)
      navigate('/login', { state: { success: 'Account created successfully. Please sign in.' } })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="flex min-h-screen items-center justify-center px-4 py-12"
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
            Create your account
          </h1>
          <p className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
            Start managing your finances with AI
          </p>
        </div>

        <div
          className="rounded-2xl border p-8 shadow-2xl shadow-black/30"
          style={{
            borderColor: 'var(--border-default)',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
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
                htmlFor="reg-name"
                className="mb-2 block text-sm font-medium"
                style={{ color: 'var(--text-secondary)' }}
              >
                Full name
              </label>
              <div className="relative">
                <User
                  size={18}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-tertiary)' }}
                />
                <input
                  id="reg-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="John Doe"
                  autoComplete="name"
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
                htmlFor="reg-email"
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
                  id="reg-email"
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
                htmlFor="reg-password"
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
                  id="reg-password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Min. 8 characters"
                  autoComplete="new-password"
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

            <div>
              <label
                htmlFor="reg-confirm"
                className="mb-2 block text-sm font-medium"
                style={{ color: 'var(--text-secondary)' }}
              >
                Confirm password
              </label>
              <div className="relative">
                <Lock
                  size={18}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-tertiary)' }}
                />
                <input
                  id="reg-confirm"
                  type={showConfirm ? 'text' : 'password'}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter your password"
                  autoComplete="new-password"
                  className="w-full rounded-lg border px-3 py-2.5 pl-11 pr-11 text-sm outline-none transition-colors focus:border-primary focus:ring-1 focus:ring-primary"
                  style={{
                    borderColor: 'var(--border-default)',
                    backgroundColor: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowConfirm(!showConfirm)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-0.5 transition-colors"
                  style={{ color: 'var(--text-tertiary)' }}
                  tabIndex={-1}
                >
                  {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
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
                  Creating account...
                </>
              ) : (
                'Create account'
              )}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-sm" style={{ color: 'var(--text-secondary)' }}>
          Already have an account?{' '}
          <Link
            to="/login"
            className="font-medium text-primary transition-colors hover:text-[#6B8FFF]"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
