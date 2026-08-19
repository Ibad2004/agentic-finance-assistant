import type { ReactNode } from 'react'
import { cn } from '../../utils/format'

type BadgeVariant = 'green' | 'red' | 'amber' | 'blue' | 'purple' | 'default'

interface BadgeProps {
  variant?: BadgeVariant
  children: ReactNode
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  green: 'bg-[var(--badge-green-bg)] text-[var(--badge-green-text)]',
  red: 'bg-[var(--badge-red-bg)] text-[var(--badge-red-text)]',
  amber: 'bg-[var(--badge-amber-bg)] text-[var(--badge-amber-text)]',
  blue: 'bg-[var(--badge-blue-bg)] text-[var(--badge-blue-text)]',
  purple: 'bg-[var(--badge-purple-bg)] text-[var(--badge-purple-text)]',
  default: 'bg-[var(--nav-hover-bg)] text-[var(--text-secondary)]',
}

export default function Badge({ variant = 'default', children, className }: BadgeProps) {
  return (
    <span className={cn('inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium', variantStyles[variant], className)}>
      {children}
    </span>
  )
}
