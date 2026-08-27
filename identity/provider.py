"""
Identity Provider
Rebuild 2: Identity & Authentication

Manages identity resolution, verification, and lifecycle.
Every message requires valid identity.
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import uuid


class IdentityType(Enum):
    """Types of identity"""
    USER = "user"
    SERVICE = "service"
    SYSTEM = "system"
    EXTERNAL = "external"


class VerificationStatus(Enum):
    """Identity verification status"""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class Identity:
    """A verified identity"""
    id: str
    type: IdentityType
    name: str
    status: VerificationStatus
    attributes: Dict[str, Any]
    created_at: float
    expires_at: Optional[float] = None


class IdentityResolver:
    """Resolves and verifies identities"""
    
    def __init__(self):
        self.identities: Dict[str, Identity] = {}
    
    def register_identity(
        self,
        identity_type: IdentityType,
        name: str,
        attributes: Dict[str, Any],
    ) -> str:
        """Register a new identity"""
        identity_id = str(uuid.uuid4())
        identity = Identity(
            id=identity_id,
            type=identity_type,
            name=name,
            status=VerificationStatus.VERIFIED,
            attributes=attributes,
            created_at=0.0,
        )
        self.identities[identity_id] = identity
        return identity_id
    
    def verify_identity(self, identity_id: str) -> Optional[Identity]:
        """Verify an identity"""
        identity = self.identities.get(identity_id)
        if identity and identity.status == VerificationStatus.VERIFIED:
            return identity
        return None
    
    def lookup_by_name(self, name: str) -> Optional[Identity]:
        """Lookup identity by name"""
        for identity in self.identities.values():
            if identity.name == name:
                return identity
        return None


class IdentityProvider:
    """
    Identity provider layer.
    Manages identity lifecycle and verification.
    """
    
    def __init__(self):
        self.resolver = IdentityResolver()
    
    def create_identity(
        self,
        identity_type: IdentityType,
        name: str,
        attributes: Dict[str, Any],
    ) -> str:
        """Create a new identity"""
        return self.resolver.register_identity(identity_type, name, attributes)
    
    def check_identity(self, identity_id: str) -> bool:
        """Check if identity is valid"""
        return self.resolver.verify_identity(identity_id) is not None
