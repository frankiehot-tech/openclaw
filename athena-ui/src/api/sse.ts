export interface SSEDelta {
  delta: string
}

export interface SSEComplete {
  usage?: {
    tokens: number
  }
}

export type SSEHandler = {
  onDelta?: (delta: SSEDelta) => void
  onComplete?: (complete: SSEComplete) => void
  onError?: (error: Error) => void
}

export function createSSEStream(
  url: string,
  handlers: SSEHandler,
): AbortController {
  const controller = new AbortController()

  fetch(url, {
    signal: controller.signal,
    headers: { Accept: 'text/event-stream' },
  })
    .then(async (res) => {
      if (!res.ok) {
        handlers.onError?.(new Error(`SSE request failed: ${res.status}`))
        return
      }

      const reader = res.body?.getReader()
      if (!reader) {
        handlers.onError?.(new Error('ReadableStream not supported'))
        return
      }

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() ?? ''

        let eventType = ''
        let data = ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            data = line.slice(6).trim()
          } else if (line === '') {
            if (eventType === 'done') {
              try {
                handlers.onComplete?.(JSON.parse(data))
              } catch {
                handlers.onComplete?.({})
              }
            } else {
              try {
                handlers.onDelta?.({ delta: JSON.parse(data).delta ?? data })
              } catch {
                handlers.onDelta?.({ delta: data })
              }
            }
            eventType = ''
            data = ''
          }
        }
      }
    })
    .catch((err) => {
      handlers.onError?.(err)
    })

  return controller
}

export function streamConversation(
  conversationId: string,
  handlers: SSEHandler,
): AbortController {
  const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8123/api/v1'
  return createSSEStream(`${base}/conversations/${conversationId}/stream`, handlers)
}
