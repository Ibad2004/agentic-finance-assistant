import type { SelectHTMLAttributes } from 'react'
import { cn } from '../../utils/format'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: Array<{ value: string; label: string }>
  placeholder?: string
}

export default function Select({ options, placeholder, className, ...props }: SelectProps) {
  return (
    <select
      className={cn(
        'rounded-lg border px-3 py-2 text-sm outline-none transition-colors',
        'border-[var(--border-default)] bg-[var(--bg-input)] focus:border-primary focus:ring-1 focus:ring-primary',
        className,
      )}
      style={{ color: 'var(--text-primary)' }}
      {...props}
    >
      {placeholder && (
        <option value="">{placeholder}</option>
      )}
      {options.map(opt => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </select>
  )
}
