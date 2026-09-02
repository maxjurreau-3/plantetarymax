"""
Transaction Execution Context (TEC)
Orchestrates request → plan → validate → authorize → execute → verify → rollback pipeline
"""

from .handlers import (
    PlanHandler,
    ValidateHandler,
    AuthorizeHandler,
    ExecuteHandler,
    VerifyHandler,
    RollbackHandler,
)
from .pipeline import TECPipeline, TECContext
from .schemas import TECEnvelope, TECResult

__all__ = [
    "TECPipeline",
    "TECContext",
    "TECEnvelope",
    "TECResult",
    "PlanHandler",
    "ValidateHandler",
    "AuthorizeHandler",
    "ExecuteHandler",
    "VerifyHandler",
    "RollbackHandler",
]
