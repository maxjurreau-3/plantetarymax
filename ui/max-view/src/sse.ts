export type EventEnvelope = {
  id?: string
  type?: string
  channel?: string
  payload?: any
  ts?: number
}

export function connectToSSE(url: string, handlers: {
  onOpen?: () => void
  onEnvelope?: (e: EventEnvelope) => void
  onError?: (err?: any) => void
  onClose?: () => void
}) {
  let source: EventSource | null = null

  try {
    source = new EventSource(url, { withCredentials: false })
  } catch (e) {
    handlers.onError?.(e)
    handlers.onClose?.()
    return { source: null, disconnect: () => {} }
  }

  source.onopen = () => handlers.onOpen?.()
  source.onerror = (err) => {
    handlers.onError?.(err)
  }
  source.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data)
      handlers.onEnvelope?.(data)
    } catch (e) {
      // If not JSON, forward raw
      handlers.onEnvelope?.({ type: 'raw', payload: ev.data, ts: Date.now() / 1000 })
    }
  }

  const disconnect = () => {
    if (source) {
      source.close()
      handlers.onClose?.()
      source = null
    }
  }

  return { source, disconnect }
}
