"""
Governance adapter for Worker and local dev
Provides evaluate(context) -> { decision: 'allow'|'deny'|'pending', reason: str }
"""
from typing import Dict, Any


def evaluate(context: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate governance policies for a given context.

    Simple default policy for dev:
      - If context contains principal with role 'admin' => allow
      - If action == 'read' => allow
      - Otherwise => pending (or deny)
    """
    principal = context.get("principal") or {}
    action = context.get("action")

    roles = principal.get("roles", []) if isinstance(principal, dict) else []
    if "admin" in roles:
        return {"decision": "allow", "reason": "principal has admin role"}

    if action == "read":
        return {"decision": "allow", "reason": "read-only action"}

    # default: pending (requires external policy engine)
    return {"decision": "pending", "reason": "requires external governance evaluation"}
