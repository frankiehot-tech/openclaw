export type StatusDotStatus = 'online' | 'offline' | 'warning' | 'error'

export interface StatusDotProps {
  status: StatusDotStatus
  className?: string
}

const statusStyles: Record<StatusDotStatus, string> = {
  online: 'bg-success-000',
  offline: 'bg-text-500',
  warning: 'bg-warning-000',
  error: 'bg-danger-000 anim-pulse',
}

export function StatusDot({ status, className }: StatusDotProps) {
  return (
    <span
      className={`w-2 h-2 rounded-full inline-block flex-shrink-0 ${statusStyles[status]} ${className ?? ''}`}
    />
  )
}
