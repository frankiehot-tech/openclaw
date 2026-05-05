const WS_URL = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8123/ws'

export type WsEventType =
  | 'agent.status'
  | 'task.progress'
  | 'metric.update'
  | 'alert'
  | 'log'

export interface WsEvent {
  type: WsEventType
  data: Record<string, unknown>
}

export interface WsAgentStatusData {
  id: string
  status: string
}

export interface WsTaskProgressData {
  id: string
  progress: number
  stage: string
}

export interface WsMetricUpdateData {
  cpu: number
  memory: number
  gpu: number
}

export interface WsAlertData {
  level: 'info' | 'warn' | 'error'
  message: string
  time: number
}

export interface WsLogData {
  time: string
  level: 'info' | 'warn' | 'error'
  message: string
}

type EventHandler = (event: WsEvent) => void

class WsClient {
  private ws: WebSocket | null = null
  private handlers = new Map<WsEventType, Set<EventHandler>>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private reconnectDelay = 1000
  private maxReconnectDelay = 30000

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return

    this.ws = new WebSocket(WS_URL)

    this.ws.onopen = () => {
      this.reconnectDelay = 1000
    }

    this.ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data)
        const typeHandlers = this.handlers.get(event.type)
        if (typeHandlers) {
          for (const handler of typeHandlers) {
            handler(event)
          }
        }
      } catch {
        // ignore malformed messages
      }
    }

    this.ws.onclose = () => {
      this.scheduleReconnect()
    }

    this.ws.onerror = () => {
      this.ws?.close()
    }
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.ws?.close()
  }

  subscribe(type: WsEventType, handler: EventHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler)
    return () => {
      this.handlers.get(type)?.delete(handler)
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, this.reconnectDelay)
    this.reconnectDelay = Math.min(
      this.reconnectDelay * 2,
      this.maxReconnectDelay,
    )
  }
}

export const wsClient = new WsClient()
