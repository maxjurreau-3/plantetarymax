"""
System Invariants Layer
Rebuild 2: Foundational Constraints

Defines the constraints that Portal-OS must maintain
across all layers (Kernel, SIM, TEC, Substrate).
"""

from typing import Dict, Any, Callable, List
from enum import Enum


class InvariantLevel(Enum):
    """Severity levels for invariant violations"""
    CRITICAL = "critical"      # System must halt
    HIGH = "high"              # Recovery required
    MEDIUM = "medium"          # Log and continue
    LOW = "low"                # Log only


class InvariantViolation(Exception):
    """Raised when a system invariant is violated"""
    def __init__(self, invariant_name: str, level: InvariantLevel, details: str):
        self.invariant_name = invariant_name
        self.level = level
        self.details = details
        super().__init__(f"[{level.value}] {invariant_name}: {details}")


class SystemInvariants:
    """
    Core system invariants that must hold at all times.
    
    Invariants are ordered by criticality.
    """
    
    # ============================================================================
    # TIER 1: FOUNDATIONAL (System must halt if violated)
    # ============================================================================
    
    @staticmethod
    def coherent_state() -> bool:
        """
        STATE COHERENCE
        
        The system state across all layers (Kernel, SIM, TEC, Substrate)
        must be internally consistent at all times.
        
        Violations indicate:
          - Stale cached state
          - Concurrent modification conflicts
          - Substrate sync failures
        """
        # TODO: Implement state coherence check
        return True
    
    @staticmethod
    def no_silent_failures() -> bool:
        """
        NO SILENT FAILURES
        
        Every failure must be logged, reported, and escalated.
        No error can be swallowed without explicit acknowledgment.
        
        Violations indicate:
          - Exception handling gaps
          - Missing error callbacks
          - Silent catch blocks
        """
        # TODO: Implement silence detection
        return True
    
    # ============================================================================
    # TIER 2: SECURITY & AUTHORIZATION
    # ============================================================================
    
    @staticmethod
    def authorization_enforced() -> bool:
        """
        AUTHORIZATION REQUIRED
        
        Every operation must be authorized before execution.
        Identity + Governance must sign off on all routing, orchestration,
        and substrate access.
        """
        # TODO: Verify governance hooks are wired
        return True
    
    @staticmethod
    def identity_established() -> bool:
        """
        IDENTITY REQUIRED
        
        Every message must carry a valid identity.
        Identity cannot be null or forged.
        """
        # TODO: Verify identity checks in message flow
        return True
    
    # ============================================================================
    # TIER 3: MESSAGING & ROUTING
    # ============================================================================
    
    @staticmethod
    def message_ordering_preserved() -> bool:
        """
        MESSAGE ORDERING
        
        Messages within a domain must be processed in order.
        Cross-domain messages may reorder, but intra-domain ordering is strict.
        """
        return True
    
    @staticmethod
    def no_message_loss() -> bool:
        """
        NO MESSAGE LOSS
        
        Every message must either:
          - Be processed and acknowledged
          - Be explicitly rejected with reason
          - Be queued for retry
        
        No message may disappear silently.
        """
        return True
    
    @staticmethod
    def message_timeout_bounded() -> bool:
        """
        MESSAGE TIMEOUT
        
        Messages have a maximum age (see KernelInvariants.MESSAGE_MAX_AGE_MS).
        Stale messages must be dropped with logging.
        """
        return True
    
    # ============================================================================
    # TIER 4: SCHEDULER & CONCURRENCY
    # ============================================================================
    
    @staticmethod
    def scheduler_cycles_complete() -> bool:
        """
        SCHEDULER CYCLES
        
        Every scheduler cycle must complete within a bounded time
        (see KernelInvariants.SCHEDULER_CYCLE_MS).
        
        Violations indicate:
          - Deadlock
          - Infinite loops
          - Resource exhaustion
        """
        return True
    
    @staticmethod
    def no_deadlock() -> bool:
        """
        NO DEADLOCK
        
        Scheduler lanes must never deadlock each other.
        Lanes are:
          - cognitive
          - orchestration
          - substrate
          - governance
        """
        return True
    
    # ============================================================================
    # TIER 5: SUBSTRATE CONSISTENCY
    # ============================================================================
    
    @staticmethod
    def substrate_consistent() -> bool:
        """
        SUBSTRATE CONSISTENCY
        
        Durable Objects state + KV state must be synchronized.
        Write-after-read must reflect all prior writes.
        
        Violations indicate:
          - Stale reads
          - Lost writes
          - Ordering issues
        """
        return True
    
    @staticmethod
    def kv_eventual_consistency() -> bool:
        """
        KV EVENTUAL CONSISTENCY
        
        KV updates are eventually consistent, not immediately.
        System must handle read-after-write delays gracefully.
        """
        return True
    
    # ============================================================================
    # TIER 6: COGNITIVE & EXECUTION
    # ============================================================================
    
    @staticmethod
    def sim_trajectory_valid() -> bool:
        """
        SIM TRAJECTORY VALIDITY
        
        SIM's state trajectory must be valid at all times.
        Trajectory discontinuities indicate bugs or external interference.
        """
        return True
    
    @staticmethod
    def tec_execution_bounded() -> bool:
        """
        TEC EXECUTION BOUNDS
        
        TEC agents must complete execution within bounded time.
        Infinite loops or resource exhaustion must be detected.
        """
        return True


class InvariantChecker:
    """
    Checks system invariants and handles violations.
    """
    
    def __init__(self):
        self.checks: Dict[str, Callable[[], bool]] = {
            # Tier 1
            "coherent_state": SystemInvariants.coherent_state,
            "no_silent_failures": SystemInvariants.no_silent_failures,
            
            # Tier 2
            "authorization_enforced": SystemInvariants.authorization_enforced,
            "identity_established": SystemInvariants.identity_established,
            
            # Tier 3
            "message_ordering_preserved": SystemInvariants.message_ordering_preserved,
            "no_message_loss": SystemInvariants.no_message_loss,
            "message_timeout_bounded": SystemInvariants.message_timeout_bounded,
            
            # Tier 4
            "scheduler_cycles_complete": SystemInvariants.scheduler_cycles_complete,
            "no_deadlock": SystemInvariants.no_deadlock,
            
            # Tier 5
            "substrate_consistent": SystemInvariants.substrate_consistent,
            "kv_eventual_consistency": SystemInvariants.kv_eventual_consistency,
            
            # Tier 6
            "sim_trajectory_valid": SystemInvariants.sim_trajectory_valid,
            "tec_execution_bounded": SystemInvariants.tec_execution_bounded,
        }
    
    def check_all(self) -> bool:
        """Check all invariants"""
        results = {}
        for name, check in self.checks.items():
            try:
                results[name] = check()
            except Exception as e:
                print(f"[INVARIANT] Check '{name}' failed: {e}")
                results[name] = False
        
        all_pass = all(results.values())
        if not all_pass:
            failed = [name for name, result in results.items() if not result]
            print(f"[INVARIANT] Failures: {', '.join(failed)}")
        
        return all_pass
    
    def check_critical(self) -> bool:
        """Check only critical Tier 1 invariants"""
        return all([
            SystemInvariants.coherent_state(),
            SystemInvariants.no_silent_failures(),
        ])
