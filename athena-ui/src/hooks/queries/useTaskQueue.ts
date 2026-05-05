import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTasks, cancelTask } from '@/api/tasks'
import type { Task } from '@/types'

export function useTaskQueue() {
  return useQuery<Task[]>({
    queryKey: ['tasks'],
    queryFn: fetchTasks,
    refetchInterval: 3000,
    staleTime: 2000,
  })
}

export function useCancelTask() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: cancelTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] })
    },
  })
}
