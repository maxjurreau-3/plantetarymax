# Substrate Schema

This document describes the Durable Object (DO) and KV key naming patterns and example payloads used by the substrate layer.

Key patterns

- kernel:status
  - Purpose: current kernel boot phase and metadata
  - Storage: Durable Object (strong) and persisted to local kernel/status.json for dev
  - Example value:

```json
{
  "phase": "ready",
  "updated_at": 1693570000.123,
  "meta": { "note": "boot_complete" }
}
```

- session:<session_id>:meta
  - Purpose: session metadata and routing hints
  - Storage: KV (eventual)
  - Example value:

```json
{
  "id": "session-123",
  "user": "user-abc",
  "created_at": 1693570000.0,
  "expires_at": 1693573600.0,
  "state": "running"
}
```

- user:<user_id>:profile
  - Purpose: user profile and capabilities
  - Storage: KV (eventual)
  - Example value:

```json
{
  "id": "user-abc",
  "display_name": "Alice",
  "roles": ["admin"],
  "preferences": {}
}
```

- audit:<iso_ts>:<id>
  - Purpose: append-only audit log entries
  - Storage: KV (eventual) or external log sink
  - Example value:

```json
{
  "id": "audit-2026-09-01T12:00:00Z-1",
  "actor": "user-abc",
  "action": "message.enqueue",
  "target": "session-123",
  "meta": {"message_id":"..."},
  "timestamp": "2026-09-01T12:00:00Z"
}
```

Replication & consistency guidance

- Durable Objects (DO) are used for strongly consistent, low-latency state (kernel:status, locks, critical per-object state).
- KV is used for eventually consistent, highly-replicated data (profiles, sessions, audit entries). When reading application data prefer DO where strong consistency is required.

Operational notes

- The kernel persists its boot phase via `kernel:status`. Workers (HTTP API) read this key to expose /kernel/status.
- For local development the substrate helpers write kernel/status.json under the kernel/ directory as a best-effort fallback so dev servers can observe kernel boot state.
