import { forwardRef, type InputHTMLAttributes } from 'react'

export interface InputProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  error?: string
  helperText?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error, helperText, className, disabled, ...props }, ref) => {
    return (
      <div className="w-full">
        <input
          ref={ref}
          className={`w-full px-3.5 py-2.5 rounded-md border bg-bg-100 text-text-100 text-sm font-ui transition-all duration-150 outline-none placeholder:text-text-500 focus:border-brand-000/50 focus:shadow-[0_0_0_3px_hsl(var(--brand-000)/10%)] disabled:opacity-50 disabled:cursor-not-allowed ${error ? 'border-danger-000' : 'border-border-100'} ${className ?? ''}`}
          disabled={disabled}
          {...props}
        />
        {error && (
          <p className="mt-1 text-xs text-danger-000">{error}</p>
        )}
        {helperText && !error && (
          <p className="mt-1 text-xs text-text-400">{helperText}</p>
        )}
      </div>
    )
  },
)

Input.displayName = 'Input'
