import { useQuery } from '@tanstack/react-query'
import { fetchAgents } from '@/api/agents'
import type { Agent } from '@/types'

export function useAgents() {
  return useQuery<Agent[]>({
    queryKey: ['agents'],
    queryFn: fetchAgents,
    refetchInterval: 5000,
    staleTime: 3000,
  })
}
