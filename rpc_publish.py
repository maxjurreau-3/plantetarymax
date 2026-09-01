import requests
import os
import time

EVENTS_PUBLISH_URL = os.environ.get("EVENTS_PUBLISH_URL", "http://127.0.0.1:8000/events/publish")
TIMEOUT = 0.5


def publish_event(envelope: dict) -> bool:
    """Best-effort: POST envelope to events publish endpoint. Returns True on HTTP 200/201/204."""
    try:
        if "ts" not in envelope:
            envelope["ts"] = time.time()
        requests.post(EVENTS_PUBLISH_URL, json=envelope, timeout=TIMEOUT)
        return True
    except Exception:
        return False
