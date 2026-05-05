import type { ReactNode } from 'react'

export interface PageHeaderProps {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, subtitle, actions, className }: PageHeaderProps) {
  return (
    <div
      className={`px-6 h-14 border-b border-border-100 bg-surface-000/80 flex items-center justify-between ${className ?? ''}`}
    >
      <div>
        <h1 className="text-lg font-semibold text-text-000 tracking-tight">{title}</h1>
        {subtitle && <p className="text-[13px] text-text-400 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2 items-center">{actions}</div>}
    </div>
  )
}
