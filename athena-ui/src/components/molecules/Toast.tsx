import { useState, useCallback, type ReactNode } from 'react'
import { ToastContext } from '@/hooks/useToast'
import type { ToastItem, ToastType } from '@/hooks/useToast'

export type { ToastType, ToastItem } from '@/hooks/useToast'

const iconMap: Record<ToastType, string> = {
  success: '✓',
  error: '✗',
  warning: '⚠',
  info: 'ℹ',
}

const colorStyles: Record<ToastType, string> = {
  success: 'text-success-000',
  error: 'text-danger-000',
  warning: 'text-warning-000',
  info: 'text-info-000',
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).slice(2, 10)
    setToasts((prev) => [...prev, { id, message, type }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 3500)
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 flex flex-col gap-2 z-50">
        {toasts.map((t) => (
          <div
            key={t.id}
            className="px-4 py-3 rounded-lg bg-surface-000 border border-border-100 shadow-lg text-[13px] font-medium text-text-100 flex items-center gap-2.5 min-w-[300px] anim-slideRight"
          >
            <span className={`font-bold ${colorStyles[t.type]}`}>{iconMap[t.type]}</span>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
