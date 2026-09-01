# PlanetaryMax — Kernel & Worker Bridge

This branch implements a portable Worker → Kernel bridge, kernel status persistence, and simple dev-friendly adapters for identity and governance.

Public API surface (Worker)

- GET /health
  - Returns: { status: 'ok', timestamp }

- GET /kernel/status
  - Returns kernel boot status (reads from KERNEL_STATUS_URL when configured, otherwise uses dev fallback written by kernel/substrate helpers).
  - Example: { phase: 'ready', updated_at: 1693570000.123, meta: { ... } }

- POST /message
  - Accepts a message envelope and enqueues it for async processing.
  - Minimal envelope schema (required):
    - type: string
    - body: object
  - Example envelope:

```json
{
  "type": "task.execute",
  "body": { "task": "send_email", "to": "user@example.com" },
  "meta": { "priority": 0 }
}
```

  - Response: { message_id: '<uuid>', status: 'queued', ... }

- POST /auth
  - Dev-friendly behaviour: if Authorization: Bearer dev-token is provided, returns principal { id: 'dev', roles: ['admin'] }.
  - If IDENTITY_URL is configured, the Worker forwards the request to that endpoint.

- GET /governance/check?q=action
  - Returns policy decision. Uses GOVERNANCE_URL when configured, otherwise falls back to a simple local adapter.

Environment variables / adapters

- KERNEL_STATUS_URL — optional URL the Worker will call to read kernel status (production binding). If unset, Worker falls back to env KERNEL_STATUS or the local kernel/status.json file written by substrate helpers.
- MESSAGE_QUEUE_URL — optional external queue endpoint. If unset, Worker uses MESSAGE_QUEUE_RPC (RPC URL) or an in-memory queue in dev.
- MESSAGE_QUEUE_RPC_URL — optional RPC endpoint to call into the Python enqueue helper (useful for local integration tests).
- IDENTITY_URL — optional external identity service URL. If unset, Worker will use IDENTITY_ADAPTER_RPC or the dev-token fallback.
- IDENTITY_ADAPTER_RPC — optional RPC endpoint to call into the identity adapter (local dev).
- GOVERNANCE_URL — optional external governance service URL. If unset, Worker will use GOVERNANCE_ADAPTER_RPC or the local governance adapter.
- GOVERNANCE_ADAPTER_RPC — optional RPC endpoint to call into the governance adapter (local dev).

Local development

1. Boot the kernel (writes kernel/status.json for dev fallback):
   - python kernel/boot.py
2. Run the Worker app (Hono) in your TypeScript environment or use a dev server to serve src/index.ts.
3. Call the endpoints above.

Tests

- tests/test_kernel_status.py — verifies set_kernel_status / get_kernel_status dev flow.
- tests/test_message_envelope.py — verifies messaging.enqueue_message returns a stable id and increases queue size.

CI

A minimal GitHub Actions workflow runs the Python smoke tests on pull requests to the branch.

