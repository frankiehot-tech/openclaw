export type ProgressColor = 'brand' | 'success' | 'warning' | 'danger' | 'info'

export interface ProgressBarProps {
  value: number
  color?: ProgressColor
  showLabel?: boolean
  className?: string
}

const colorStyles: Record<ProgressColor, string> = {
  brand: 'bg-brand-000',
  success: 'bg-success-000',
  warning: 'bg-warning-000',
  danger: 'bg-danger-000',
  info: 'bg-info-000',
}

export function ProgressBar({
  value,
  color = 'brand',
  showLabel = false,
  className,
}: ProgressBarProps) {
  const clamped = Math.min(Math.max(value, 0), 100)

  return (
    <div className={`w-full ${className ?? ''}`}>
      <div className="h-1 rounded-sm bg-bg-300 overflow-hidden">
        <div
          className={`h-full rounded-sm transition-[width] duration-[600ms] ${colorStyles[color]}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel && (
        <span className="text-xs text-text-400 mt-1 block">{Math.round(clamped)}%</span>
      )}
    </div>
  )
}
