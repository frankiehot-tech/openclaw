import { type ReactNode } from 'react'

export interface Column<T> {
  key: string
  header: ReactNode
  width?: string
  sortable?: boolean
  render: (row: T) => ReactNode
}

export interface DataTableProps<T> {
  columns: readonly Column<T>[]
  data: readonly T[]
  onRowClick?: (row: T) => void
  sortable?: boolean
  className?: string
}

export function DataTable<T extends { id?: string }>({
  columns,
  data,
  onRowClick,
  sortable = false,
  className,
}: DataTableProps<T>) {
  if (!data.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-text-400 text-sm">
        <span className="text-5xl opacity-40 mb-4">📋</span>
        暂无数据
      </div>
    )
  }

  return (
    <div
      className={`overflow-x-auto rounded-lg border border-border-100 ${className ?? ''}`}
    >
      <table className="w-full border-collapse text-[13px]">
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                style={col.width ? { width: col.width } : undefined}
                className={`text-left px-4 py-2.5 font-semibold text-text-300 text-[11px] uppercase tracking-[0.05em] bg-bg-200 border-b border-border-100 ${sortable && col.sortable ? 'cursor-pointer hover:text-text-100' : ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={row.id ?? i}
              onClick={() => onRowClick?.(row)}
              className={`${onRowClick ? 'cursor-pointer' : ''}`}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className="px-4 py-3 border-b border-border-100 text-text-100 hover:bg-bg-200/50 last:border-b-0"
                >
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
