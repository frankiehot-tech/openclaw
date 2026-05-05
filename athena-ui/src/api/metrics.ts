import { api } from './client'
import type { SystemMetrics } from '@/types'

export interface MetricPoint {
  timestamp: number
  cpu: number
  memory: number
  gpu: number
  gpuTemp: number
  activeAgents: number
  queueDepth: number
}

export async function fetchSystemMetrics(): Promise<SystemMetrics> {
  return api.get<SystemMetrics>('/metrics')
}

export async function fetchMetricsHistory(
  range: '1h' | '6h' | '24h' | '7d' = '1h',
): Promise<MetricPoint[]> {
  return api.get<MetricPoint[]>(`/metrics/history?range=${range}`)
}
