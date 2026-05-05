import type { ReactNode } from 'react'

export type TagColor = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'brand'

export interface TagProps {
  children: ReactNode
  color?: TagColor
  className?: string
}

const colorStyles: Record<TagColor, string> = {
  default: 'bg-bg-300 text-text-300',
  success: 'bg-success-000/12 text-success-000',
  warning: 'bg-warning-000/12 text-warning-000',
  danger: 'bg-danger-000/12 text-danger-000',
  info: 'bg-info-000/12 text-info-000',
  brand: 'bg-brand-000/12 text-brand-000',
}

export function Tag({ children, color = 'default', className }: TagProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-medium text-[11px] tracking-[0.02em] ${colorStyles[color]} ${className ?? ''}`}
    >
      {children}
    </span>
  )
}
