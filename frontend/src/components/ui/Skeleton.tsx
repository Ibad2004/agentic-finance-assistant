interface SkeletonProps {
  className?: string
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return <div className={`skeleton ${className}`} />
}

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-5">
      <div className="skeleton mb-3 h-4 w-24 rounded" />
      <div className="skeleton mb-2 h-8 w-32 rounded" />
      <div className="skeleton h-3 w-20 rounded" />
    </div>
  )
}

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 border-b px-4 py-3" style={{ borderColor: 'var(--border-default)' }}>
      <div className="skeleton h-4 w-20 rounded" />
      <div className="skeleton h-4 flex-1 rounded" />
      <div className="skeleton h-4 w-24 rounded" />
      <div className="skeleton h-4 w-16 rounded" />
    </div>
  )
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="overflow-hidden rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)]">
      <div className="border-b px-4 py-3" style={{ borderColor: 'var(--border-default)' }}>
        <div className="skeleton h-4 w-32 rounded" />
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonRow key={i} />
      ))}
    </div>
  )
}
