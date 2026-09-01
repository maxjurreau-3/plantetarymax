import os
import time
import json
import asyncio
from typing import Dict, Any, Set

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Config via env
EVENTS_PUBLISH_TOKEN = os.environ.get("EVENTS_PUBLISH_TOKEN")  # required for publish endpoints in prod
EVENTS_ALLOWED_ORIGINS = os.environ.get("EVENTS_ALLOWED_ORIGINS", "")  # comma-separated list
MAX_ENVELOPE_BYTES = int(os.environ.get("MAX_ENVELOPE_BYTES", str(64 * 1024)))  # 64KB default
DEBUG_ALLOW_PUBLISH = os.environ.get("DEBUG_ALLOW_PUBLISH", "false").lower() in ("1", "true", "yes")

app = FastAPI(title="RPC Events Broker")

# Configure CORS based on allowed origins env var. If empty, allow only same-origin.
allowed_origins = [o.strip() for o in EVENTS_ALLOWED_ORIGINS.split(",") if o.strip()]
if allowed_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

# Async set of connected client queues
clients: Set[asyncio.Queue] = set()
clients_lock = asyncio.Lock()

# Helper: simple origin validator for SSE
def _validate_origin(request: Request) -> None:
    if allowed_origins:
        origin = request.headers.get("origin") or request.headers.get("referer")
        if not origin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin header required")
        # origin may include scheme+host; match against allowed_origins prefixes
        ok = any(origin.startswith(a) for a in allowed_origins)
        if not ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")


async def _event_generator(q: asyncio.Queue):
    try:
        while True:
            msg = await q.get()
            # SSE framing
            data = json.dumps(msg, default=str)
            yield f"data: {data}\n\n"
    except asyncio.CancelledError:
        return
    finally:
        # generator exit cleanup handled by caller
        return


@app.get("/events/sse")
async def sse(request: Request):
    # Validate origin if configured
    try:
        _validate_origin(request)
    except HTTPException:
        # Allow in dev if allowed_origins not set
        raise

    q: asyncio.Queue = asyncio.Queue()
    async with clients_lock:
        clients.add(q)

    # send a small connected envelope immediately
    await q.put({"id": f"conn-{int(time.time()*1000)}", "type": "connection.open", "channel": "global", "payload": {}, "ts": time.time()})

    generator = _event_generator(q)

    async def streaming():
        try:
            async for chunk in generator:
                # If client disconnects, request.client_disconnect will be set
                yield chunk.encode("utf-8")
                # yield control
                await asyncio.sleep(0)
        finally:
            # cleanup client queue on disconnect
            async with clients_lock:
                try:
                    clients.discard(q)
                except Exception:
                    pass

    return StreamingResponse(streaming(), media_type="text/event-stream")


def _require_publish_auth(request: Request):
    # If no token configured, allow only when DEBUG_ALLOW_PUBLISH is true
    if not EVENTS_PUBLISH_TOKEN:
        if DEBUG_ALLOW_PUBLISH:
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Publish disabled")

    # Accept Authorization: Bearer <token> or X-EVENTS-TOKEN header
    auth = request.headers.get("authorization", "")
    token = None
    if auth.lower().startswith("bearer "):
        token = auth.split(None, 1)[1].strip()
    if not token:
        token = request.headers.get("x-events-token")
    if not token or token != EVENTS_PUBLISH_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid publish token")


@app.post("/events/publish")
async def publish(request: Request):
    _require_publish_auth(request)
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    # basic validation & size limit
    raw = json.dumps(payload, default=str)
    if len(raw.encode("utf-8")) > MAX_ENVELOPE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Envelope too large")

    # ensure required fields
    if not isinstance(payload, dict) or "type" not in payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Envelope must be an object with a 'type' field")

    # add timestamp if missing
    if "ts" not in payload:
        payload["ts"] = time.time()

    # Broadcast to connected clients (best-effort)
    async with clients_lock:
        for q in list(clients):
            try:
                # use put_nowait to avoid blocking
                q.put_nowait(payload)
            except Exception:
                # drop client if queue full/closed
                try:
                    clients.discard(q)
                except Exception:
                    pass

    return JSONResponse({"ok": True})


@app.post("/debug/publish")
async def debug_publish(request: Request):
    # Allow debug publish only when DEBUG_ALLOW_PUBLISH is true, or token provided
    if not DEBUG_ALLOW_PUBLISH and not EVENTS_PUBLISH_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Debug publish disabled")
    # If token configured, require it
    if EVENTS_PUBLISH_TOKEN:
        _require_publish_auth(request)

    try:
        payload = await request.json() or {}
    except Exception:
        payload = {}

    envelope = {
        "id": payload.get("id") or f"evt-{int(time.time()*1000)}",
        "type": payload.get("type", "debug.event"),
        "channel": payload.get("channel", "global"),
        "payload": payload.get("payload", {}),
        "ts": time.time(),
    }

    async with clients_lock:
        for q in list(clients):
            try:
                q.put_nowait(envelope)
            except Exception:
                try:
                    clients.discard(q)
                except Exception:
                    pass

    return JSONResponse({"ok": True, "envelope": envelope})


@app.get("/events/snapshot")
async def snapshot():
    # Provide a simple snapshot: kernel status file (if present) and a small queue preview if available.
    data: Dict[str, Any] = {"kernel": None, "queue_preview": [], "queue_size": 0}
    try:
        # kernel status file path relative to repo
        here = os.path.dirname(__file__)
        ks_path = os.path.join(here, "kernel", "status.json")
        if os.path.exists(ks_path):
            with open(ks_path, "r", encoding="utf-8") as f:
                data["kernel"] = json.load(f)
    except Exception:
        data["kernel"] = None

    try:
        # attempt to import messaging.get_queue_size and maybe preview
        from messaging.queue import default_queue
        data["queue_size"] = default_queue.size()
        # preview: take up to 10 items (ids + types)
        rpt = []
        for i, item in enumerate(list(default_queue.queue)[:10]):
            rpt.append({"id": getattr(item, "id", None), "type": getattr(item, "payload", {}).get("type") if getattr(item, "payload", None) else None})
        data["queue_preview"] = rpt
    except Exception:
        pass

    return JSONResponse(data)


@app.get("/healthz")
async def healthz():
    return JSONResponse({"ok": True, "time": time.time()})


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    # Use uvicorn for async performance in production
    uvicorn.run("rpc_events:app", host="0.0.0.0", port=port, log_level="info")
