export type EventEnvelope = {
  id: string;
  type: string;
  channel?: string;
  payload?: any;
  ts?: number;
};

export const bus = new EventTarget();

const DEFAULT_URL = (import.meta.env.VITE_API_BASE || '') + '/events/sse';

function backoff(attempt:number){
  const ms = Math.min(1000 * Math.pow(2, attempt), 10000);
  return ms + Math.round(Math.random()*200);
}

export function connectSSE(onOpen?: ()=>void) {
  let es: EventSource | null = null;
  let closed = false;
  let attempt = 0;

  function start() {
    const url = DEFAULT_URL;
    es = new EventSource(url, { withCredentials: false });

    es.onopen = () => {
      attempt = 0;
      if (onOpen) onOpen();
      bus.dispatchEvent(new CustomEvent('realtime:connected'));
    };

    es.onmessage = (e) => {
      try {
        const data: EventEnvelope = JSON.parse(e.data);
        bus.dispatchEvent(new CustomEvent('realtime:event', { detail: data }));
      } catch (err) {
        console.error('SSE parse error', err);
      }
    };

    es.onerror = () => {
      if (es) {
        try { es.close(); } catch {}
        es = null;
      }
      bus.dispatchEvent(new CustomEvent('realtime:disconnected'));
      if (!closed) {
        const wait = backoff(attempt++);
        setTimeout(() => start(), wait);
      }
    };
  }

  start();

  return () => {
    closed = true;
    if (es) {
      try { es.close(); } catch {}
      es = null;
    }
  };
}
