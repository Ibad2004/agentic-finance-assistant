import type { InputHTMLAttributes } from 'react'
import { cn } from '../../utils/format'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export default function Input({ label, error, className, ...props }: InputProps) {
  return (
    <div>
      {label && (
        <label className="mb-1.5 block text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
          {label}
        </label>
      )}
      <input
        className={cn(
          'w-full rounded-lg border px-3 py-2 text-sm outline-none transition-colors',
          'border-[var(--border-default)] bg-[var(--bg-input)] placeholder-[var(--text-tertiary)]',
          'focus:border-primary focus:ring-1 focus:ring-primary',
          error && 'border-danger focus:border-danger focus:ring-danger',
          className,
        )}
        style={{ color: 'var(--text-primary)' }}
        {...props}
      />
      {error && <p className="mt-1 text-xs text-danger">{error}</p>}
    </div>
  )
}
