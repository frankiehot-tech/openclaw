import { useQuery } from '@tanstack/react-query'
import { fetchSystemMetrics } from '@/api/metrics'
import type { SystemMetrics } from '@/types'

export function useSystemMetrics() {
  return useQuery<SystemMetrics>({
    queryKey: ['metrics'],
    queryFn: fetchSystemMetrics,
    refetchInterval: 2000,
    staleTime: 1000,
  })
}
