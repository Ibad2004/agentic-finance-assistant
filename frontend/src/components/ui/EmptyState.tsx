import type { ReactNode } from 'react'
import type { ElementType } from 'react'

interface EmptyStateProps {
  icon: ElementType
  title: string
  description: string
  action?: ReactNode
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl"
        style={{ backgroundColor: 'var(--skeleton-from)' }}
      >
        <Icon size={28} style={{ color: 'var(--text-tertiary)' }} />
      </div>
      <h3 className="mb-1 text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h3>
      <p className="mb-5 max-w-sm text-sm" style={{ color: 'var(--text-secondary)' }}>{description}</p>
      {action}
    </div>
  )
}
