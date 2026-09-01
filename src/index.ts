/**
 * Portal-OS Worker Entrypoint (enhanced)
 *
 * Cloudflare Workers entry point (Hono framework)
 * Bridges HTTP requests → Kernel message routing (dev-friendly adapters)
 */

import { Hono } from 'hono';

const app = new Hono();

// Dev-friendly in-memory queue if no external queue URL is provided
const localQueue: Array<any> = [];

const KERNEL_STATUS_URL = (typeof process !== 'undefined' && process.env && process.env.KERNEL_STATUS_URL) || undefined;
const MESSAGE_QUEUE_URL = (typeof process !== 'undefined' && process.env && process.env.MESSAGE_QUEUE_URL) || undefined;
const MESSAGE_QUEUE_RPC_URL = (typeof process !== 'undefined' && process.env && process.env.MESSAGE_QUEUE_RPC_URL) || undefined;
const IDENTITY_URL = (typeof process !== 'undefined' && process.env && process.env.IDENTITY_URL) || undefined;
const IDENTITY_ADAPTER_RPC = (typeof process !== 'undefined' && process.env && process.env.IDENTITY_ADAPTER_RPC) || undefined;
const GOVERNANCE_URL = (typeof process !== 'undefined' && process.env && process.env.GOVERNANCE_URL) || undefined;
const GOVERNANCE_ADAPTER_RPC = (typeof process !== 'undefined' && process.env && process.env.GOVERNANCE_ADAPTER_RPC) || undefined;

/**
 * Health check / Service status
 */
app.get('/health', (c) => {
  return c.json({ status: 'ok', timestamp: new Date().toISOString() });
});

/**
 * Kernel initialization / boot status
 */
app.get('/kernel/status', async (c) => {
  // Try configured status URL first (dev or prod adapter)
  if (KERNEL_STATUS_URL) {
    try {
      const res = await fetch(KERNEL_STATUS_URL);
      if (res.ok) {
        const body = await res.json();
        return c.json(body);
      }
    } catch (e) {
      // fallthrough to fallback
    }
  }

  // Fallback: environment-provided JSON or a default response
  try {
    if (typeof process !== 'undefined' && process.env && process.env.KERNEL_STATUS) {
      const parsed = JSON.parse(process.env.KERNEL_STATUS);
      return c.json(parsed);
    }
  } catch (e) {
    // ignore
  }

  // last-resort: unknown
  return c.json({ kernel: 'unknown', rebuild: 2 });
});

/**
 * Message routing endpoint
 * Routes incoming messages to Kernel for processing
 */
app.post('/message', async (c) => {
  const body = await c.req.json();

  // Basic envelope validation
  if (!body || typeof body !== 'object') {
    return c.json({ error: 'invalid_payload' }, 400);
  }

  const envelope = body;
  if (!envelope.type || !envelope.body) {
    return c.json({ error: 'missing_fields', required: ['type', 'body'] }, 400);
  }

  // Attach correlation/trace id
  const messageId = (globalThis.crypto && (globalThis.crypto as any).randomUUID) ? (globalThis.crypto as any).randomUUID() : `msg-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const timestamp = new Date().toISOString();
  const queuedMessage = {
    id: messageId,
    source: 'worker',
    envelope,
    timestamp,
  };

  // Forward to external queue if configured
  if (MESSAGE_QUEUE_URL) {
    try {
      const res = await fetch(MESSAGE_QUEUE_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(queuedMessage),
      });
      if (!res.ok) {
        return c.json({ message_id: messageId, status: 'queue_error' }, 502);
      }
      const qres = await res.json();
      return c.json({ message_id: messageId, status: 'queued', queue_response: qres });
    } catch (e) {
      return c.json({ message_id: messageId, status: 'queue_error', error: String(e) }, 502);
    }
  }

  // Forward to local RPC enqueue if configured (useful for local integration)
  if (MESSAGE_QUEUE_RPC_URL) {
    try {
      const res = await fetch(MESSAGE_QUEUE_RPC_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(queuedMessage),
      });
      if (res.ok) {
        const rj = await res.json();
        return c.json({ message_id: messageId, status: 'queued', queue_response: rj });
      }
      // fallthrough to localQueue
    } catch (e) {
      // fallthrough to localQueue
    }
  }

  // Otherwise, use in-memory queue (dev-friendly)
  localQueue.push(queuedMessage);

  return c.json({
    message_id: messageId,
    status: 'queued',
    queue_size: localQueue.length,
    timestamp,
  });
});

/**
 * Inspect local queue (dev only)
 */
app.get('/queue', (c) => {
  // return basic queue health and first 10 message ids
  const preview = localQueue.slice(0, 10).map((m) => ({ id: m.id, type: m.envelope?.type }));
  return c.json({ queue_size: localQueue.length, preview });
});

/**
 * Message lookup (dev only) — checks in-memory queue for message id
 */
app.get('/message/:id', (c) => {
  const id = c.req.param('id');
  const found = localQueue.find((m) => m.id === id);
  if (found) {
    return c.json({ message_id: id, status: 'queued', envelope: found.envelope, timestamp: found.timestamp });
  }
  return c.json({ message_id: id, status: 'not_found' }, 404);
});

/**
 * Identity authentication endpoint
 */
app.post('/auth', async (c) => {
  // Development-friendly auth: forward to IDENTITY_URL if configured
  if (IDENTITY_URL) {
    try {
      const res = await fetch(IDENTITY_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: await c.req.text(),
      });
      const body = await res.json();
      return c.json(body, res.status);
    } catch (e) {
      return c.json({ authenticated: false, error: String(e) }, 502);
    }
  }

  // Local fallback: simple token check
  const auth = c.req.header('Authorization') || '';
  if (auth.startsWith('Bearer ')) {
    const token = auth.slice(7);
    // dev token
    if (token === 'dev-token') {
      return c.json({ authenticated: true, principal: { id: 'dev', roles: ['admin'] } });
    }

    // Try local identity adapter RPC
    if (IDENTITY_ADAPTER_RPC) {
      try {
        const res = await fetch(IDENTITY_ADAPTER_RPC, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        });
        if (res.ok) {
          const pj = await res.json();
          return c.json({ authenticated: !!pj && Object.keys(pj).length > 0, principal: pj });
        }
      } catch (e) {
        // fall through
      }
    }
  }

  return c.json({ authenticated: false });
});

/**
 * Governance policy check
 */
app.get('/governance/check', async (c) => {
  const q = c.req.query('q') || '';

  if (GOVERNANCE_URL) {
    try {
      const res = await fetch(GOVERNANCE_URL + (q ? `?q=${encodeURIComponent(q)}` : ''));
      const body = await res.json();
      return c.json(body, res.status);
    } catch (e) {
      return c.json({ policy_check: 'error', error: String(e) }, 502);
    }
  }

  if (GOVERNANCE_ADAPTER_RPC) {
    try {
      const rpc = GOVERNANCE_ADAPTER_RPC + (q ? `?q=${encodeURIComponent(q)}` : '');
      const res = await fetch(rpc, { method: 'GET' });
      if (res.ok) {
        const pj = await res.json();
        return c.json(pj);
      }
    } catch (e) {
      // fallthrough
    }
  }

  // Default: pending
  return c.json({ policy_check: 'pending' });
});

export default app;
