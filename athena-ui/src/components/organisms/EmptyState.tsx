import type { ReactNode } from 'react'

export interface EmptyStateProps {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-16 px-6 text-center ${className ?? ''}`}
    >
      {icon && (
        <div className="text-5xl opacity-40 mb-4">{icon}</div>
      )}
      <h3 className="text-sm font-semibold text-text-300 mb-1">{title}</h3>
      {description && <p className="text-xs text-text-400 mb-4">{description}</p>}
      {action && <div>{action}</div>}
    </div>
  )
}
