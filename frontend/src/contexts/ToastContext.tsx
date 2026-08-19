import { createContext, useContext, useState, useCallback } from 'react'
import type { ReactNode } from 'react'
import { X, CheckCircle, AlertCircle, AlertTriangle } from 'lucide-react'

type ToastType = 'success' | 'error' | 'warning'

interface Toast {
  id: string
  type: ToastType
  message: string
}

interface ToastContextType {
  toast: (type: ToastType, message: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((type: ToastType, message: string) => {
    const id = crypto.randomUUID()
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id))
    }, 4000)
  }, [])

  const remove = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const icons = {
    success: <CheckCircle size={18} className="text-success" />,
    error: <AlertCircle size={18} className="text-danger" />,
    warning: <AlertTriangle size={18} className="text-warning" />,
  }

  const borderColors = {
    success: 'border-success/30',
    error: 'border-danger/30',
    warning: 'border-warning/30',
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed right-4 top-4 z-[100] flex flex-col gap-2">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`toast-enter flex items-center gap-3 rounded-xl border ${borderColors[t.type]} bg-[var(--toast-bg)] px-4 py-3 shadow-lg`}
            style={{ boxShadow: 'var(--shadow-card)' }}
          >
            {icons[t.type]}
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{t.message}</span>
            <button
              type="button"
              onClick={() => remove(t.id)}
              className="ml-2 shrink-0 rounded p-0.5"
              style={{ color: 'var(--text-tertiary)' }}
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextType {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used within a ToastProvider')
  return context
}
