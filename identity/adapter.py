"""
Minimal identity service adapter for Worker API
Provides a simple validate_token(token) -> principal dict for local/dev use.
"""
from typing import Optional, Dict, Any
from .provider import IdentityProvider, IdentityType
import time

provider = IdentityProvider()

# Register a dev identity for the 'dev-token' bearer token
DEV_PRINCIPAL = {
    "id": "dev",
    "name": "developer",
    "roles": ["admin"],
    "created_at": time.time(),
}


def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a token and return principal dict or None if invalid.

    Dev behavior: token == 'dev-token' => returns DEV_PRINCIPAL
    """
    if not token:
        return None

    if token == "dev-token":
        return DEV_PRINCIPAL

    # TODO: integrate with real identity provider or external IDENTITY_URL
    return None
