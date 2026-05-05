export { api, ApiError } from './client'

export {
  fetchAgents,
  fetchAgent,
  createAgent,
  deleteAgent,
} from './agents'

export {
  fetchTasks,
  fetchTask,
  createTask,
  deleteTask,
  cancelTask,
} from './tasks'

export {
  fetchConversations,
  createConversation,
  sendMessage,
  fetchMessages,
} from './conversations'

export {
  fetchSkills,
  fetchSkill,
  toggleSkill,
  updateSkill,
} from './skills'
export type { Skill } from './skills'

export {
  fetchSystemMetrics,
  fetchMetricsHistory,
} from './metrics'
export type { MetricPoint } from './metrics'

export {
  fetchSettings,
  updateSettings,
} from './settings'
export type { Settings } from './settings'

export {
  fetchSandboxStatus,
  executeCode,
  restartSandbox,
} from './sandbox'
export type { SandboxStatus, ExecutionResult } from './sandbox'

export { wsClient } from './ws'
export type {
  WsEventType,
  WsEvent,
  WsAgentStatusData,
  WsTaskProgressData,
  WsMetricUpdateData,
  WsAlertData,
  WsLogData,
} from './ws'

export {
  createSSEStream,
  streamConversation,
} from './sse'
export type { SSEDelta, SSEComplete, SSEHandler } from './sse'
