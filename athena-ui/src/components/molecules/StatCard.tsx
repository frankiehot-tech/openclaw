import type { ReactNode } from 'react'

export interface StatCardProps {
  label: ReactNode
  value: string
  trend?: ReactNode
  trendDirection?: 'up' | 'down'
  className?: string
}

export function StatCard({ label, value, trend, trendDirection, className }: StatCardProps) {
  return (
    <div
      className={`bg-surface-000 border border-border-100 rounded-2xl p-5 flex flex-col gap-2 transition-all duration-200 hover:border-brand-000/30 hover:shadow-md ${className ?? ''}`}
    >
      <span className="text-xs font-semibold text-text-400 uppercase tracking-[0.05em]">
        {label}
      </span>
      <span className="text-[32px] font-extrabold text-text-000 tracking-[-0.03em] leading-none">
        {value}
      </span>
      {trend && (
        <span
          className={`text-xs font-medium flex items-center gap-1 ${trendDirection === 'up' ? 'text-success-000' : 'text-danger-000'}`}
        >
          {trendDirection === 'up' ? '↑' : '↓'} {trend}
        </span>
      )}
    </div>
  )
}
