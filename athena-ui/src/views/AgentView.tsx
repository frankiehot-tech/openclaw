import { useState } from 'react'
import { FormattedMessage, useIntl } from 'react-intl'
import { PageHeader } from '@/components/organisms/PageHeader'
import { DataTable } from '@/components/organisms/DataTable'
import { Modal } from '@/components/molecules/Modal'
import { SearchBox } from '@/components/molecules/SearchBox'
import { Button } from '@/components/atoms/Button'
import { ProgressBar } from '@/components/atoms/ProgressBar'
import { StatusDot } from '@/components/atoms/StatusDot'
import { Tag } from '@/components/atoms/Tag'
import { EmptyState } from '@/components/organisms/EmptyState'
import { useAgentStore, selectAgentById } from '@/stores/agentStore'
import type { Column } from '@/components/organisms/DataTable'
import type { Agent, AgentStatus } from '@/types'

const typeColor = (type: string): 'brand' | 'info' | undefined => {
  const map: Record<string, 'brand' | 'info'> = {
    '内容生产': 'brand', '数据研究': 'info', '自动化测试': 'info',
    '消息桥接': 'brand', '语义理解': 'info', '视觉处理': 'brand',
  }
  return map[type]
}

function formatUptime(seconds: number): string {
  if (seconds === 0) return '—'
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}h ${m}m`
}

export function AgentView() {
  const intl = useIntl()
  const { agents, loading, selectedAgentId, fetchAgents, selectAgent, updateAgentStatus } =
    useAgentStore()
  const [search, setSearch] = useState('')
  const [detailOpen, setDetailOpen] = useState(false)

  const selectedAgent = selectedAgentId
    ? selectAgentById(selectedAgentId)(useAgentStore.getState())
    : null

  const filtered = agents.filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.type.includes(search),
  )

  if (!agents.length && !loading) {
    return (
      <div>
        <PageHeader
          title={<FormattedMessage id="agents.title" />}
          subtitle={<FormattedMessage id="agents.subtitle" />}
          actions={
            <Button variant="primary" size="sm" onClick={fetchAgents}>
              <FormattedMessage id="agents.loadAgent" />
            </Button>
          }
        />
        <EmptyState
          icon="🐝"
          title={<FormattedMessage id="agents.emptyTitle" />}
          description={<FormattedMessage id="agents.emptyDesc" />}
          action={
            <Button variant="primary" onClick={fetchAgents} loading={loading}>
              <FormattedMessage id="agents.loadAgent" />
            </Button>
          }
        />
      </div>
    )
  }

  const columns: readonly Column<Agent>[] = [
    { key: 'status', header: '', width: '40px', render: (a) => <StatusDot status={a.status} /> },
    { key: 'name', header: 'Agent', render: (a) => <span className="font-mono text-xs">{a.name}</span> },
    { key: 'type', header: <FormattedMessage id="agents.col.type" />, render: (a) => <Tag color={typeColor(a.type)}>{a.type}</Tag> },
    { key: 'stat', header: <FormattedMessage id="agents.col.status" />, render: (a) => <span className="text-[13px]">{intl.formatMessage({ id: `agents.status.${a.status}` })}</span> },
    { key: 'load', header: <FormattedMessage id="agents.col.load" />, width: '150px', render: (a) => (
      <div className="flex items-center gap-2">
        <ProgressBar value={a.load} color={a.load > 80 ? 'danger' : 'brand'} className="flex-1" />
        <span className="text-xs text-text-400 w-8">{a.load}%</span>
      </div>
    )},
    { key: 'uptime', header: <FormattedMessage id="agents.col.uptime" />, width: '100px', render: (a) => <span className="text-xs text-text-400">{formatUptime(a.uptime)}</span> },
  ]

  const statusLabel: Record<AgentStatus, string> = {
    online: intl.formatMessage({ id: 'agents.status.online' }),
    offline: intl.formatMessage({ id: 'agents.status.offline' }),
    warning: intl.formatMessage({ id: 'agents.status.warning' }),
    error: intl.formatMessage({ id: 'agents.status.error' }),
  }

  return (
    <div>
      <PageHeader
        title={<FormattedMessage id="agents.title" />}
        subtitle={intl.formatMessage({ id: 'agents.onlineCount' }, {
          count: agents.length,
          online: agents.filter((a) => a.status === 'online').length,
        })}
        actions={
          <div className="flex gap-2">
            <SearchBox value={search} onChange={setSearch} placeholder={intl.formatMessage({ id: 'agents.searchPlaceholder' })} />
            <Button variant="secondary" size="sm" onClick={fetchAgents} loading={loading}>
              <FormattedMessage id="agents.refresh" />
            </Button>
          </div>
        }
      />
      <div className="flex-1 overflow-y-auto p-6">
        <DataTable columns={columns} data={filtered} onRowClick={(agent) => { selectAgent(agent.id); setDetailOpen(true) }} />
      </div>

      {selectedAgent && (
        <Modal open={detailOpen} onClose={() => setDetailOpen(false)} title={selectedAgent.name}>
          <div className="space-y-4">
            <div>
              <div className="text-xs text-text-400 uppercase tracking-[0.05em] mb-1"><FormattedMessage id="agents.detail.type" /></div>
              <Tag color={typeColor(selectedAgent.type)}>{selectedAgent.type}</Tag>
            </div>
            <div>
              <div className="text-xs text-text-400 uppercase tracking-[0.05em] mb-1"><FormattedMessage id="agents.detail.status" /></div>
              <div className="flex items-center gap-2">
                <StatusDot status={selectedAgent.status} />
                <span className="text-[13px] text-text-100">{statusLabel[selectedAgent.status]}</span>
              </div>
            </div>
            <div>
              <div className="text-xs text-text-400 uppercase tracking-[0.05em] mb-1"><FormattedMessage id="agents.detail.load" /></div>
              <ProgressBar value={selectedAgent.load} color={selectedAgent.load > 80 ? 'danger' : 'brand'} />
            </div>
            <div>
              <div className="text-xs text-text-400 uppercase tracking-[0.05em] mb-1"><FormattedMessage id="agents.detail.uptime" /></div>
              <span className="text-[13px] text-text-100">{formatUptime(selectedAgent.uptime)}</span>
            </div>
            <div className="flex gap-2 pt-2">
              {selectedAgent.status === 'offline' ? (
                <Button variant="primary" size="sm" onClick={() => updateAgentStatus(selectedAgent.id, 'online')}>
                  <FormattedMessage id="agents.action.start" />
                </Button>
              ) : (
                <Button variant="secondary" size="sm" onClick={() => updateAgentStatus(selectedAgent.id, 'offline')}>
                  <FormattedMessage id="agents.action.stop" />
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={() => updateAgentStatus(selectedAgent.id, 'offline')}>
                <FormattedMessage id="agents.action.restart" />
              </Button>
              <Button variant="danger" size="sm">
                <FormattedMessage id="agents.action.delete" />
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
