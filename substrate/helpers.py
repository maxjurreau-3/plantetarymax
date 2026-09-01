"""
Substrate State helpers

Provides convenience helpers for kernel status persistence and retrieval.
"""
from typing import Dict, Any, Optional
from .state import SubstrateState
import time
import json
import os

# Single global substrate instance for simple adapter
substrate = SubstrateState()

KERNEL_STATUS_KEY = "kernel:status"
LOCAL_STATUS_PATH = os.path.join(os.path.dirname(__file__), "..", "kernel", "status.json")


def _write_local_status_file(payload: Dict[str, Any]) -> None:
    """
    For local development / integration tests, write a JSON status file
    at kernel/status.json so other local components (e.g., Worker dev server)
    can observe kernel boot status. This is optional and best-effort.
    """
    try:
        # ensure directory exists
        dirpath = os.path.dirname(LOCAL_STATUS_PATH)
        os.makedirs(dirpath, exist_ok=True)
        with open(LOCAL_STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f)
    except Exception:
        # best-effort only; don't raise
        pass


def set_kernel_status(phase: str, meta: Optional[Dict[str, Any]] = None) -> bool:
    payload = {
        "phase": phase,
        "updated_at": time.time(),
        "meta": meta or {},
    }
    # persist into the in-memory substrate (Durable Object adapter)
    try:
        substrate.write_persistent(KERNEL_STATUS_KEY, payload)
    except Exception:
        # ignore persistence errors in adapter
        pass

    # best-effort: write local status file for dev servers
    try:
        _write_local_status_file(payload)
    except Exception:
        pass

    return True


def get_kernel_status() -> Optional[Dict[str, Any]]:
    try:
        status = substrate.read(KERNEL_STATUS_KEY)
        if status:
            return status
    except Exception:
        pass

    # best-effort: read local status file if present
    try:
        with open(LOCAL_STATUS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None
