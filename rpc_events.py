import os
import time
import json
import asyncio
from typing import Dict, Any, Set, Optional

from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware

# Prometheus client
from prometheus_client import Counter, Gauge, generate_latest, CONTENT_TYPE_LATEST

# Optional Redis support (async)
try:
    import redis.asyncio as aioredis
except Exception:
    aioredis = None  # type: ignore

# Config via env
EVENTS_PUBLISH_TOKEN = os.environ.get("EVENTS_PUBLISH_TOKEN")  # required for publish endpoints in prod
EVENTS_ALLOWED_ORIGINS = os.environ.get("EVENTS_ALLOWED_ORIGINS", "")  # comma-separated list
MAX_ENVELOPE_BYTES = int(os.environ.get("MAX_ENVELOPE_BYTES", str(64 * 1024)))  # 64KB default
DEBUG_ALLOW_PUBLISH = os.environ.get("DEBUG_ALLOW_PUBLISH", "false").lower() in ("1", "true", "yes")
EVENTS_REDIS_URL = os.environ.get("EVENTS_REDIS_URL")  # e.g. redis://localhost:6379/0
EVENTS_REDIS_CHANNEL = os.environ.get("EVENTS_REDIS_CHANNEL", "events")

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

# Prometheus metrics
CONNECTED_CLIENTS = Gauge("events_connected_clients", "Number of connected SSE clients")
EVENTS_PUBLISHED = Counter("events_published_total", "Number of events published via HTTP")
EVENTS_BROADCASTED = Counter("events_broadcasted_total", "Number of events broadcast to clients")
EVENTS_RECEIVED_REDIS = Counter("events_received_from_redis_total", "Number of events received from Redis and forwarded")

# Async set of connected client queues
clients: Set[asyncio.Queue] = set()
clients_lock = asyncio.Lock()

# Redis client and pubsub (optional)
redis_client: Optional["aioredis.Redis"] = None  # type: ignore
redis_pubsub: Optional["aioredis.client.PubSub"] = None  # type: ignore
redis_listener_task: Optional[asyncio.Task] = None


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
        return


@app.get("/events/sse")
async def sse(request: Request):
    # Validate origin if configured
    if allowed_origins:
        _validate_origin(request)

    q: asyncio.Queue = asyncio.Queue()
    async with clients_lock:
        clients.add(q)
        # update gauge
        try:
            CONNECTED_CLIENTS.set(len(clients))
        except Exception:
            pass

    # send a small connected envelope immediately
    await q.put({"id": f"conn-{int(time.time()*1000)}", "type": "connection.open", "channel": "global", "payload": {}, "ts": time.time()})

    generator = _event_generator(q)

    async def streaming():
        try:
            async for chunk in generator:
                yield chunk.encode("utf-8")
                await asyncio.sleep(0)
        finally:
            # cleanup client queue on disconnect
            async with clients_lock:
                try:
                    clients.discard(q)
                except Exception:
                    pass
                try:
                    CONNECTED_CLIENTS.set(len(clients))
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


async def _broadcast_local(payload: Dict[str, Any]):
    sent = 0
    async with clients_lock:
        for q in list(clients):
            try:
                q.put_nowait(payload)
                sent += 1
            except Exception:
                try:
                    clients.discard(q)
                except Exception:
                    pass
        try:
            if sent:
                EVENTS_BROADCASTED.inc(sent)
        except Exception:
            pass


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

    # increment published counter
    try:
        EVENTS_PUBLISHED.inc()
    except Exception:
        pass

    # If Redis configured, publish to Redis channel so all broker instances will receive it
    if redis_client:
        try:
            await redis_client.publish(EVENTS_REDIS_CHANNEL, json.dumps(payload, default=str))
        except Exception:
            # fall back to local broadcast if Redis fails
            await _broadcast_local(payload)
    else:
        await _broadcast_local(payload)

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

    # If Redis is available, publish there; otherwise broadcast locally
    if redis_client:
        try:
            await redis_client.publish(EVENTS_REDIS_CHANNEL, json.dumps(envelope, default=str))
        except Exception:
            await _broadcast_local(envelope)
    else:
        await _broadcast_local(envelope)

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


@app.get("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# Redis listener: subscribe to EVENTS_REDIS_CHANNEL and forward incoming messages to local clients
async def _redis_listener(pubsub: "aioredis.client.PubSub"):
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not message:
                await asyncio.sleep(0.01)
                continue
            # message data can be bytes or str
            data = message.get("data")
            if not data:
                continue
            if isinstance(data, bytes):
                try:
                    payload = json.loads(data.decode("utf-8"))
                except Exception:
                    continue
            elif isinstance(data, str):
                try:
                    payload = json.loads(data)
                except Exception:
                    continue
            else:
                # unknown type
                continue

            # metrics: increment redis received
            try:
                EVENTS_RECEIVED_REDIS.inc()
            except Exception:
                pass

            # broadcast locally
            await _broadcast_local(payload)
    except asyncio.CancelledError:
        return
    except Exception:
        return


@app.on_event("startup")
async def startup_event():
    global redis_client, redis_pubsub, redis_listener_task
    if EVENTS_REDIS_URL and aioredis:
        try:
            redis_client = aioredis.from_url(EVENTS_REDIS_URL)
            redis_pubsub = redis_client.pubsub(ignore_subscribe_messages=True)
            await redis_pubsub.subscribe(EVENTS_REDIS_CHANNEL)
            # start background listener task
            redis_listener_task = asyncio.create_task(_redis_listener(redis_pubsub))
        except Exception:
            # fail open: leave redis_client None and continue running
            redis_client = None
            redis_pubsub = None
            redis_listener_task = None


@app.on_event("shutdown")
async def shutdown_event():
    global redis_client, redis_pubsub, redis_listener_task
    if redis_listener_task:
        try:
            redis_listener_task.cancel()
            await redis_listener_task
        except Exception:
            pass
    if redis_pubsub:
        try:
            await redis_pubsub.unsubscribe(EVENTS_REDIS_CHANNEL)
            await redis_pubsub.close()
        except Exception:
            pass
    if redis_client:
        try:
            await redis_client.close()
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    # Use uvicorn for async performance in production
    uvicorn.run("rpc_events:app", host="0.0.0.0", port=port, log_level="info")
