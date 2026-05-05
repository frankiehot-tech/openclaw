import { useEffect, type ReactNode } from 'react'
import { Icon } from '@/components/atoms/Icon'

export type ModalSize = 'sm' | 'md' | 'lg'

export interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: ModalSize
}

const sizeStyles: Record<ModalSize, string> = {
  sm: 'min-w-[320px]',
  md: 'min-w-[480px]',
  lg: 'min-w-[640px]',
}

export function Modal({ open, onClose, title, children, size = 'md' }: ModalProps) {
  useEffect(() => {
    if (!open) return
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEsc)
    return () => document.removeEventListener('keydown', handleEsc)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 anim-fadeIn"
      onClick={onClose}
    >
      <div
        className={`bg-surface-000 border border-border-100 rounded-2xl p-6 max-w-[90vw] max-h-[85vh] overflow-y-auto anim-scaleIn shadow-xl ${sizeStyles[size]}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-bold text-text-000">{title}</h3>
          <button
            onClick={onClose}
            className="w-9 h-9 flex items-center justify-center rounded-lg text-text-300 hover:bg-bg-200 hover:text-text-100 transition-colors duration-150"
          >
            <Icon name="close" size={18} />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}
