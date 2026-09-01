import React, { useEffect, useRef, useState } from 'react'
import { connectToSSE, EventEnvelope } from './sse'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export default function App() {
  const [messages, setMessages] = useState<EventEnvelope[]>([])
  const [status, setStatus] = useState<'idle' | 'connecting' | 'open' | 'closed' | 'error'>('idle')
  const evtSourceRef = useRef<EventSource | null>(null)

  useEffect(() => {
    setStatus('connecting')
    const channel = 'global'
    const url = new URL('/events/sse', API_BASE || window.location.origin)
    url.searchParams.set('channel', channel)

    const { source, disconnect } = connectToSSE(url.toString(), {
      onOpen: () => setStatus('open'),
      onEnvelope: (env) => setMessages((m) => [env, ...m]),
      onError: () => setStatus('error'),
      onClose: () => setStatus('closed')
    })

    evtSourceRef.current = source
    return () => disconnect()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="app">
      <header>
        <h1>Max‑View</h1>
        <p>Status: <strong>{status}</strong></p>
      </header>

      <main>
        <PublishForm apiBase={API_BASE} onPublished={(env) => setMessages((m) => [env, ...m])} />

        <section className="feed">
          <h2>Events</h2>
          {messages.length === 0 && <div className="empty">No events yet</div>}
          <ul>
            {messages.map((m, i) => (
              <li key={m.id || `${i}-${m.ts}`}>
                <div className="meta">
                  <span className="type">{m.type}</span>
                  <span className="ts">{new Date((m.ts || 0) * 1000).toLocaleTimeString()}</span>
                </div>
                <pre className="payload">{JSON.stringify(m.payload, null, 2)}</pre>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  )
}

function PublishForm({ apiBase, onPublished }: { apiBase: string; onPublished?: (e: any) => void }) {
  const [token, setToken] = useState<string>('')
  const [payload, setPayload] = useState<string>('{"type":"message.enqueued","payload":{"text":"hello world"},"channel":"global"}')
  const [busy, setBusy] = useState(false)

  const publish = async () => {
    setBusy(true)
    try {
      const url = new URL('/events/publish', apiBase || window.location.origin).toString()
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: payload
      })
      const json = await res.json().catch(() => null)
      if (!res.ok) {
        alert(`Publish failed: ${res.status} ${res.statusText}\n${JSON.stringify(json)}`)
      } else {
        if (onPublished) onPublished(JSON.parse(payload))
      }
    } catch (e) {
      alert(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="publisher">
      <h2>Publish</h2>
      <div className="form-row">
        <label>Auth token (optional)</label>
        <input value={token} onChange={(e) => setToken(e.target.value)} placeholder="Bearer token" />
      </div>
      <div className="form-row">
        <label>Payload</label>
        <textarea value={payload} onChange={(e) => setPayload(e.target.value)} rows={6} />
      </div>
      <div className="form-row">
        <button onClick={publish} disabled={busy}>{busy ? 'Publishing…' : 'Publish'}</button>
      </div>
    </section>
  )
}
