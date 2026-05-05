export type LogLevel = 'info' | 'warn' | 'error'

export interface LogEntryProps {
  time: string
  level: LogLevel
  message: string
  className?: string
}

const levelStyles: Record<LogLevel, string> = {
  info: 'text-info-000',
  warn: 'text-warning-000',
  error: 'text-danger-000',
}

export function LogEntry({ time, level, message, className }: LogEntryProps) {
  return (
    <div className={`flex gap-2 py-1.5 font-mono text-xs leading-relaxed ${className ?? ''}`}>
      <span className="text-text-500 flex-shrink-0 min-w-[160px]">{time}</span>
      <span className={`font-semibold flex-shrink-0 min-w-[48px] ${levelStyles[level]}`}>
        {level.toUpperCase()}
      </span>
      <span className="text-text-200 break-all">{message}</span>
    </div>
  )
}
