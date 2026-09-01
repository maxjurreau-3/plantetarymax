```python
"""
Substrate State helpers

Provides convenience helpers for kernel status persistence and retrieval.
"""
from typing import Dict, Any, Optional
from .state import SubstrateState
import time

# Single global substrate instance for simple adapter
substrate = SubstrateState()

KERNEL_STATUS_KEY = "kernel:status"


def set_kernel_status(phase: str, meta: Optional[Dict[str, Any]] = None) -> bool:
    payload = {
        "phase": phase,
        "updated_at": time.time(),
        "meta": meta or {},
    }
    return substrate.write_persistent(KERNEL_STATUS_KEY, payload)


def get_kernel_status() -> Optional[Dict[str, Any]]:
    return substrate.read(KERNEL_STATUS_KEY)
```
