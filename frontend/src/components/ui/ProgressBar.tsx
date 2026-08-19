interface ProgressBarProps {
  value: number
  max?: number
  color?: 'green' | 'amber' | 'red' | 'blue'
  height?: number
}

const colorMap = {
  green: 'bg-success',
  amber: 'bg-warning',
  red: 'bg-danger',
  blue: 'bg-primary',
}

export default function ProgressBar({ value, max = 100, color = 'blue', height = 8 }: ProgressBarProps) {
  const pct = Math.min(Math.max((value / max) * 100, 0), 100)
  return (
    <div
      className="w-full overflow-hidden rounded-full"
      style={{ height, backgroundColor: 'var(--skeleton-from)' }}
    >
      <div
        className={`h-full rounded-full transition-all duration-300 ${colorMap[color]}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  )
}
