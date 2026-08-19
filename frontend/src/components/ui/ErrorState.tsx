import type { ReactNode } from 'react'
import { AlertCircle } from 'lucide-react'
import Button from './Button'

interface ErrorStateProps {
  title?: string
  message: string
  onRetry?: () => void
}

export default function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-danger/10">
        <AlertCircle size={28} className="text-danger" />
      </div>
      <h3 className="mb-1 text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h3>
      <p className="mb-5 max-w-sm text-sm" style={{ color: 'var(--text-secondary)' }}>{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
