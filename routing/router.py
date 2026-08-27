"""
Message Router
Rebuild 2: Message Routing & Delivery

Deterministic routing from Worker → Kernel → SIM → TEC → Substrate → Worker.
Maintains message ordering within domains.
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum
import uuid


class RoutingDomain(Enum):
    """Message routing domains"""
    WORKER = "worker"
    KERNEL = "kernel"
    COGNITIVE = "cognitive"
    TEC = "tec"
    SUBSTRATE = "substrate"


@dataclass
class RoutedMessage:
    """A message with routing metadata"""
    id: str
    source_domain: RoutingDomain
    target_domain: RoutingDomain
    identity_id: str
    payload: Dict[str, Any]
    priority: int = 0
    sequence: int = 0


class RoutingTable:
    """Maps routing decisions"""
    
    def __init__(self):
        self.routes: Dict[str, Callable] = {}
    
    def register_route(
        self,
        source: RoutingDomain,
        target: RoutingDomain,
        handler: Callable,
    ) -> None:
        """Register a route"""
        route_key = f"{source.value}->{target.value}"
        self.routes[route_key] = handler
    
    def route(self, message: RoutedMessage) -> bool:
        """Route a message"""
        route_key = f"{message.source_domain.value}->{message.target_domain.value}"
        handler = self.routes.get(route_key)
        
        if not handler:
            print(f"[ROUTING] No route for {route_key}")
            return False
        
        try:
            handler(message)
            return True
        except Exception as e:
            print(f"[ROUTING] Route handler error: {e}")
            return False


class Router:
    """
    Message router.
    Routes messages through system layers deterministically.
    """
    
    def __init__(self):
        self.table = RoutingTable()
        self.sequence_counter: Dict[str, int] = {}
    
    def submit_message(
        self,
        source: RoutingDomain,
        target: RoutingDomain,
        identity_id: str,
        payload: Dict[str, Any],
    ) -> str:
        """Submit a message for routing"""
        msg_id = str(uuid.uuid4())
        
        # Get sequence number for source domain
        seq_key = source.value
        sequence = self.sequence_counter.get(seq_key, 0) + 1
        self.sequence_counter[seq_key] = sequence
        
        message = RoutedMessage(
            id=msg_id,
            source_domain=source,
            target_domain=target,
            identity_id=identity_id,
            payload=payload,
            sequence=sequence,
        )
        
        if self.table.route(message):
            return msg_id
        
        return ""
