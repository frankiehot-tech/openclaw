import { FormattedMessage } from 'react-intl'
import { PageHeader } from '@/components/organisms/PageHeader'
import { StatCard } from '@/components/molecules/StatCard'
import { ProgressBar } from '@/components/atoms/ProgressBar'
import { Tag } from '@/components/atoms/Tag'
import { DataTable } from '@/components/organisms/DataTable'
import { Button } from '@/components/atoms/Button'
import type { Column } from '@/components/organisms/DataTable'
import { useSystemMetrics } from '@/hooks/queries/useSystemMetrics'
import { useTaskQueue } from '@/hooks/queries/useTaskQueue'

interface TaskRow {
  id: string
  name: string
  status: string
  agent: string
  time: string
}

const statusColorMap: Record<string, 'info' | 'success' | 'danger'> = {
  running: 'info', done: 'success', completed: 'success', failed: 'danger',
}

function statusColor(s: string) {
  return statusColorMap[s] ?? ('default' as never)
}

function formatRelative(ts: number) {
  const mins = Math.floor((Date.now() - ts) / 60000)
  if (mins < 60) return `${mins} minutes ago`
  return `${Math.floor(mins / 60)} hours ago`
}

const resources = [
  { label: 'CPU', value: 67, color: 'brand' as const },
  { label: '内存', value: 43, color: 'info' as const },
  { label: '硬盘', value: 72, color: 'warning' as const },
  { label: 'GPU', value: 88, color: 'danger' as const },
]

export function DashboardView() {
  const { data: metrics } = useSystemMetrics()
  const { data: tasks } = useTaskQueue()

  const stats = [
    {
      label: <FormattedMessage id="monitoring.activeAgents" />,
      value: String(metrics?.activeAgents ?? '—'),
      trend: '+3 /week' as const,
      trendDirection: 'up' as const,
    },
    {
      label: '任务队列',
      value: String(tasks?.length ?? '—'),
      trend: '-5 /week' as const,
      trendDirection: 'down' as const,
    },
    { label: <FormattedMessage id="monitoring.cpu" />, value: `${Math.round(metrics?.cpu ?? 0)}%`, trend: '+2% vs yesterday' as const, trendDirection: 'up' as const },
    { label: <FormattedMessage id="monitoring.gpuTemp" />, value: `${Math.round(metrics?.gpuTemp ?? 0)}°C`, trend: '-3°C vs yesterday' as const, trendDirection: 'down' as const },
  ]

  const taskColumns: readonly Column<TaskRow>[] = [
    { key: 'id', header: 'ID', width: '100px', render: (r) => <span className="font-mono text-xs">{r.id}</span> },
    { key: 'name', header: '任务', render: (r) => r.name },
    { key: 'agent', header: 'Agent', width: '140px', render: (r) => <code className="text-[11px] text-text-300">{r.agent}</code> },
    { key: 'status', header: <FormattedMessage id="agents.col.status" />, width: '90px', render: (r) => <Tag color={statusColor(r.status)}>{r.status}</Tag> },
    { key: 'time', header: '时间', width: '90px', render: (r) => <span className="text-text-400">{r.time}</span> },
  ]

  const taskRows: TaskRow[] = (tasks ?? []).slice(0, 5).map((t) => ({
    id: t.id, name: t.name, status: t.status, agent: t.agentId, time: formatRelative(t.createdAt),
  }))

  return (
    <div>
      <PageHeader
        title={<FormattedMessage id="dashboard.title" />}
        subtitle={<FormattedMessage id="dashboard.subtitle" />}
        actions={<Button variant="secondary" size="sm"><FormattedMessage id="dashboard.export" /></Button>}
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex flex-col gap-6">
          <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
            {stats.map((s, i) => (
              <StatCard key={i} {...s} />
            ))}
          </div>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <div className="text-sm font-bold text-text-100 mb-3"><FormattedMessage id="dashboard.taskPipeline" /></div>
              <DataTable columns={taskColumns} data={taskRows} />
            </div>
            <div className="flex flex-col gap-4">
              <div className="bg-surface-000 border border-border-100 rounded-2xl p-5">
                <h3 className="text-sm font-bold text-text-100 mb-3"><FormattedMessage id="dashboard.systemResources" /></h3>
                <div className="flex flex-col gap-3">
                  {resources.map((r) => (
                    <div key={r.label}>
                      <div className="flex justify-between mb-1.5">
                        <span className="text-xs text-text-300">{r.label}</span>
                        <span className="text-xs font-semibold text-text-100">{r.value}%</span>
                      </div>
                      <ProgressBar value={r.value} color={r.color} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
