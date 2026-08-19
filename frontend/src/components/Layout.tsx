import { useState, useEffect } from 'react'
import { Outlet, NavLink, useLocation, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  ArrowLeftRight,
  Wallet,
  Calculator,
  FileText,
  Building2,
  BotMessageSquare,
  Search,
  Bell,
  Menu,
  X,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'

const navItems = [
  { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { path: '/budgets', label: 'Budgets', icon: Wallet },
  { path: '/tax', label: 'Tax', icon: Calculator },
  { path: '/reports', label: 'Reports', icon: FileText },
  { path: '/accounts', label: 'Accounts', icon: Building2 },
  { path: '/assistant', label: 'AI Assistant', icon: BotMessageSquare },
]

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/transactions': 'Transactions',
  '/budgets': 'Budgets',
  '/tax': 'Tax Estimator',
  '/reports': 'Reports',
  '/accounts': 'Accounts',
  '/assistant': 'AI Assistant',
}

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const navigate = useNavigate()

  const pageTitle = pageTitles[location.pathname] ?? 'Finora'

  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const displayName = user?.name
    ? user.name.charAt(0).toUpperCase() + user.name.slice(1)
    : user?.email?.split('@')[0] ?? 'User'
  const userInitial = displayName.charAt(0).toUpperCase()

  return (
    <div className="flex h-screen overflow-hidden" style={{ backgroundColor: 'var(--bg-app)' }}>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 backdrop-blur-sm lg:hidden"
          style={{ backgroundColor: 'var(--bg-overlay)' }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[260px] flex-col border-r transition-transform duration-300 ease-in-out lg:static lg:translate-x-0 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-sidebar)' }}
      >
        <div className="flex h-14 items-center gap-3 border-b px-5" style={{ borderColor: 'var(--border-default)' }}>
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent-purple shadow-sm shadow-primary/20">
            <span className="text-sm font-bold text-white">F</span>
          </div>
          <span className="bg-gradient-to-r from-primary to-accent-purple bg-clip-text text-lg font-bold text-transparent">
            FINORA
          </span>
          <button
            type="button"
            onClick={() => setSidebarOpen(false)}
            className="ml-auto rounded-lg p-1.5 lg:hidden"
            style={{ color: 'var(--text-tertiary)' }}
          >
            <X size={20} />
          </button>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-[var(--nav-active-bg)] text-[var(--nav-active-text)]'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--nav-hover-bg)] hover:text-[var(--text-primary)]'
                }`
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="border-t p-3" style={{ borderColor: 'var(--border-default)' }}>
          <div className="flex items-center gap-3 rounded-lg px-3 py-2">
            <div
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent-purple"
            >
              <span className="text-xs font-semibold text-white">{userInitial}</span>
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{displayName}</p>
              <p className="truncate text-xs" style={{ color: 'var(--text-tertiary)' }}>{user?.email ?? ''}</p>
            </div>
            <button
              type="button"
              onClick={handleLogout}
              title="Sign out"
              className="shrink-0 rounded-lg p-1.5 text-[var(--text-tertiary)] transition-colors hover:bg-danger/10 hover:text-danger"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header
          className="flex h-14 shrink-0 items-center justify-between border-b px-4 backdrop-blur-md sm:px-6"
          style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-topbar)' }}
        >
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-2 lg:hidden"
              style={{ color: 'var(--text-secondary)' }}
            >
              <Menu size={20} />
            </button>
            <h1 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{pageTitle}</h1>
          </div>

          <div className="flex items-center gap-2">
            <div
              className="hidden items-center gap-2 rounded-lg border px-3 py-1.5 sm:flex"
              style={{ borderColor: 'var(--border-default)', backgroundColor: 'var(--bg-surface-secondary)' }}
            >
              <Search size={15} style={{ color: 'var(--text-tertiary)' }} />
              <input
                type="text"
                placeholder="Search..."
                className="w-40 bg-transparent text-sm outline-none placeholder-[var(--text-tertiary)]"
                style={{ color: 'var(--text-primary)' }}
              />
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              className="rounded-lg p-2 transition-colors hover:bg-[var(--nav-hover-bg)]"
              style={{ color: 'var(--text-secondary)' }}
              title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>

            <button
              type="button"
              className="relative rounded-lg p-2 transition-colors hover:bg-[var(--nav-hover-bg)]"
              style={{ color: 'var(--text-secondary)' }}
            >
              <Bell size={18} />
              <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-danger" />
            </button>

            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-primary to-accent-purple"
            >
              <span className="text-xs font-semibold text-white">{userInitial}</span>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6" style={{ backgroundColor: 'var(--bg-app)' }}>
          <div className="mx-auto max-w-[1440px]">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
