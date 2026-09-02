from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from enum import Enum
import time
import uuid


class HandlerStage(str, Enum):
    PLAN = "plan"
    VALIDATE = "validate"
    AUTHORIZE = "authorize"
    EXECUTE = "execute"
    VERIFY = "verify"
    ROLLBACK = "rollback"


@dataclass
class TECEnvelope:
    """Standard message envelope for TEC pipeline"""
    type: str
    body: Dict[str, Any]
    meta: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "body": self.body,
            "meta": self.meta,
            "id": self.id,
            "ts": self.ts,
        }


@dataclass
class TECResult:
    """Result from TEC pipeline execution"""
    envelope_id: str
    stage: HandlerStage
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    trace: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    ts: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "stage": self.stage.value,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "trace": self.trace,
            "latency_ms": self.latency_ms,
            "ts": self.ts,
        }


@dataclass
class TECContext:
    """Context passed through the TEC pipeline"""
    envelope: TECEnvelope
    plan: Optional[Dict[str, Any]] = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    principal: Optional[Dict[str, Any]] = None
    authorization: Dict[str, Any] = field(default_factory=dict)
    execution_result: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None
    rollback_actions: List[Dict[str, Any]] = field(default_factory=list)
    stages_completed: List[HandlerStage] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    def elapsed_ms(self) -> float:
        return (time.time() - self.start_time) * 1000
