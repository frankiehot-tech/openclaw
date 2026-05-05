import { FormattedMessage, useIntl } from 'react-intl'
import { PageHeader } from '@/components/organisms/PageHeader'
import { StatCard } from '@/components/molecules/StatCard'
import { ProgressBar } from '@/components/atoms/ProgressBar'
import { Tag } from '@/components/atoms/Tag'
import { EmptyState } from '@/components/organisms/EmptyState'
import { useSystemMetrics } from '@/hooks/queries/useSystemMetrics'

export function MonitoringView() {
  const intl = useIntl()
  const { data: metrics, isLoading, error } = useSystemMetrics()

  if (error) {
    return (
      <div>
        <PageHeader
          title={<FormattedMessage id="monitoring.title" />}
          subtitle={<FormattedMessage id="monitoring.subtitle" />}
        />
        <EmptyState
          icon="⚠️"
          title={<FormattedMessage id="monitoring.loadError" />}
          description={<FormattedMessage id="monitoring.loadErrorDesc" />}
        />
      </div>
    )
  }

  if (isLoading || !metrics) {
    return (
      <div>
        <PageHeader
          title={<FormattedMessage id="monitoring.title" />}
          subtitle={<FormattedMessage id="monitoring.subtitle" />}
        />
        <div className="flex-1 p-6 flex items-center justify-center">
          <span className="anim-pulse text-text-400"><FormattedMessage id="monitoring.loading" /></span>
        </div>
      </div>
    )
  }

  const alertCount = metrics.gpuTemp > 75 ? 1 : 0
  const status = alertCount > 0 ? '⚠️' : <FormattedMessage id="monitoring.normal" />

  return (
    <div>
      <PageHeader
        title={<FormattedMessage id="monitoring.title" />}
        subtitle={intl.formatMessage({ id: 'monitoring.clusterStatus' }, {
          status,
          alerts: alertCount > 0 ? `${alertCount} ${intl.formatMessage({ id: 'monitoring.alerts' })}` : intl.formatMessage({ id: 'monitoring.noAlerts' }),
        })}
      />
      <div className="flex-1 overflow-y-auto p-6">
        <div className="space-y-6">
          <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4">
            <StatCard label={<FormattedMessage id="monitoring.cpu" />} value={`${Math.round(metrics.cpu)}%`} trend={intl.formatMessage({ id: 'monitoring.realtime' })} trendDirection="up" />
            <StatCard label={<FormattedMessage id="monitoring.memory" />} value={`${Math.round(metrics.memory)}%`} trend={intl.formatMessage({ id: 'monitoring.realtime' })} trendDirection="up" />
            <StatCard label={<FormattedMessage id="monitoring.gpu" />} value={`${Math.round(metrics.gpu)}%`} trend={intl.formatMessage({ id: 'monitoring.realtime' })} trendDirection="up" />
            <StatCard label={<FormattedMessage id="monitoring.activeAgents" />} value={String(metrics.activeAgents)} trend={intl.formatMessage({ id: 'monitoring.realtime' })} trendDirection="up" />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div className="bg-surface-000 border border-border-100 rounded-2xl p-5">
              <h3 className="text-sm font-bold text-text-100 mb-4"><FormattedMessage id="monitoring.systemResources" /></h3>
              <div className="space-y-3">
                <MetricRow label={intl.formatMessage({ id: 'monitoring.cpu' })} value={Math.round(metrics.cpu)} color="brand" />
                <MetricRow label={intl.formatMessage({ id: 'monitoring.memory' })} value={Math.round(metrics.memory)} color="info" />
                <MetricRow label={intl.formatMessage({ id: 'monitoring.gpu' })} value={Math.round(metrics.gpu)} color="warning" />
                <MetricRow label={intl.formatMessage({ id: 'monitoring.gpuTemp' })} value={Math.round(metrics.gpuTemp)} unit="°C" color={metrics.gpuTemp > 75 ? 'danger' : 'brand'} />
              </div>
            </div>
            <div className="bg-surface-000 border border-border-100 rounded-2xl p-5">
              <h3 className="text-sm font-bold text-text-100 mb-4"><FormattedMessage id="monitoring.alertEvents" /></h3>
              {metrics.gpuTemp > 75 ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-danger-000/10 border border-danger-000/20">
                    <span className="w-2 h-2 rounded-full bg-danger-000 anim-pulse" />
                    <div className="flex-1">
                      <span className="text-[13px] text-danger-000 font-medium"><FormattedMessage id="monitoring.gpuTempHigh" /></span>
                      <span className="text-xs text-text-400 ml-2">{Math.round(metrics.gpuTemp)}°C</span>
                    </div>
                    <Tag color="danger"><FormattedMessage id="monitoring.severity.critical" /></Tag>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-text-400 text-center py-8"><FormattedMessage id="monitoring.noAlertEvents" /></div>
              )}
            </div>
          </div>

          <div className="bg-surface-000 border border-border-100 rounded-2xl p-5">
            <h3 className="text-sm font-bold text-text-100 mb-4">
              <FormattedMessage id="monitoring.queueHealth" /> · {intl.formatMessage({ id: 'monitoring.queuePending' }, { count: metrics.queueDepth })}
            </h3>
            <ProgressBar value={Math.min((metrics.queueDepth / 50) * 100, 100)} color={metrics.queueDepth > 30 ? 'warning' : 'brand'} />
          </div>
        </div>
      </div>
    </div>
  )
}

function MetricRow({ label, value, unit = '%', color }: { label: string; value: number; unit?: string; color: 'brand' | 'info' | 'warning' | 'danger' }) {
  return (
    <div>
      <div className="flex justify-between mb-1.5">
        <span className="text-xs text-text-300">{label}</span>
        <span className="text-xs font-semibold text-text-100">{value}{unit}</span>
      </div>
      <ProgressBar value={value} color={color} />
    </div>
  )
}
