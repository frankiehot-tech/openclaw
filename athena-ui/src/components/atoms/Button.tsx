import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg'

export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'size'> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  icon?: ReactNode
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    'bg-brand-000 text-white border-brand-000 hover:bg-brand-100 hover:shadow-md active:scale-[0.97]',
  secondary:
    'bg-bg-200 text-text-100 border-border-100 hover:bg-bg-300 active:scale-[0.97]',
  ghost:
    'bg-transparent text-text-300 hover:bg-bg-200 hover:text-text-100 active:scale-[0.97]',
  danger:
    'bg-danger-000/12 text-danger-000 border-transparent hover:bg-danger-000/18 active:scale-[0.97]',
}

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'px-2.5 py-1 text-xs rounded gap-1.5',
  md: 'px-4 py-2 text-[13px] rounded-md gap-1.5',
  lg: 'px-6 py-3 text-[15px] rounded-lg gap-2',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, icon, disabled, children, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={`inline-flex items-center justify-center font-semibold cursor-pointer border transition-all duration-150 font-ui select-none ${variantStyles[variant]} ${sizeStyles[size]} ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className ?? ''}`}
        {...props}
      >
        {loading && (
          <span className="anim-pulse">⏳</span>
        )}
        {icon && !loading && icon}
        {children}
      </button>
    )
  },
)

Button.displayName = 'Button'
