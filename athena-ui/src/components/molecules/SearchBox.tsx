import { Icon } from '@/components/atoms/Icon'

export interface SearchBoxProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  className?: string
}

export function SearchBox({ value, onChange, placeholder = '搜索...', className }: SearchBoxProps) {
  return (
    <div
      className={`flex items-center gap-2 px-3.5 py-2.5 rounded-md border border-border-100 bg-bg-100 transition-all duration-150 focus-within:border-brand-000/50 focus-within:shadow-[0_0_0_3px_hsl(var(--brand-000)/10%)] ${className ?? ''}`}
    >
      <Icon name="search" size={16} className="text-text-500" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="border-none bg-transparent outline-none text-sm text-text-100 font-ui w-60 placeholder:text-text-500"
      />
    </div>
  )
}
