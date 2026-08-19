import type { ReactNode } from 'react'
import { cn } from '../../utils/format'

interface CardProps {
  children: ReactNode
  className?: string
  hover?: boolean
}

export default function Card({ children, className, hover = false }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5',
        hover && 'transition-colors duration-150 hover:bg-[var(--bg-surface-hover)]',
        className,
      )}
      style={{ boxShadow: 'var(--shadow-card)' }}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('mb-4 flex items-center justify-between', className)}>
      {children}
    </div>
  )
}

export function CardTitle({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <h3 className={cn('text-sm font-semibold', className)} style={{ color: 'var(--text-primary)' }}>
      {children}
    </h3>
  )
}
