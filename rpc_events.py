from flask import Flask, request, Response, stream_with_context, jsonify
import time, json, queue, threading

app = Flask(__name__)

# List of client queues for SSE
clients = []  # each is a queue.Queue()

# Simple lock for client list
clients_lock = threading.Lock()


def event_stream(q):
    try:
        while True:
            msg = q.get()
            # SSE format
            yield f"data: {json.dumps(msg)}\n\n"
    except GeneratorExit:
        return


@app.route('/events/sse')
def sse():
    q = queue.Queue()
    with clients_lock:
        clients.append(q)

    def cleanup(response):
        try:
            with clients_lock:
                clients.remove(q)
        except Exception:
            pass

    return Response(stream_with_context(event_stream(q)), mimetype='text/event-stream')


@app.route('/events/publish', methods=['POST'])
def publish():
    msg = request.get_json()
    if not msg:
        return jsonify({"ok": False, "error": "invalid_payload"}), 400

    # Broadcast to connected SSE clients (best-effort)
    with clients_lock:
        for q in list(clients):
            try:
                q.put_nowait(msg)
            except Exception:
                pass

    return jsonify({"ok": True})


# Minimal helper endpoints to exercise event publishing from CLI
@app.route('/debug/publish', methods=['POST'])
def debug_publish():
    payload = request.get_json() or {}
    envelope = {
        "id": payload.get("id") or f"evt-{int(time.time()*1000)}",
        "type": payload.get("type", "debug.event"),
        "channel": payload.get("channel", "global"),
        "payload": payload.get("payload", {}),
        "ts": time.time(),
    }
    # reuse publisher
    with clients_lock:
        for q in list(clients):
            try:
                q.put_nowait(envelope)
            except Exception:
                pass
    return jsonify({"ok": True, "envelope": envelope})
