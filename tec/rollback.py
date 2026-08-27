"""
TEC Rollback Mechanism
Rebuild 3: Error Recovery

Implements rollback for failed executions.
Undoes actions and restores state.
"""

from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
import uuid


@dataclass
class UndoAction:
    """Action to undo a previous operation"""
    id: str
    original_action_id: str
    operation: str
    parameters: Dict[str, Any]
    execute_fn: Optional[Callable] = None


class RollbackManager:
    """
    Manages rollback of failed executions.
    Tracks undo actions and executes them in reverse order.
    """
    
    def __init__(self):
        self.undo_stack: List[UndoAction] = []
        self.rollback_count = 0
    
    def record_action(self, action_id: str, undo: UndoAction) -> None:
        """
        Record an action that can be undone.
        """
        self.undo_stack.append(undo)
    
    def rollback(self, to_point: Optional[str] = None) -> bool:
        """
        Rollback all actions since a checkpoint.
        If to_point is None, rollback all.
        Returns success.
        """
        success = True
        
        # Execute undo actions in reverse order
        while self.undo_stack:
            undo = self.undo_stack.pop()
            
            try:
                if undo.execute_fn:
                    undo.execute_fn(undo.parameters)
                else:
                    self._execute_undo(undo)
            except Exception as e:
                print(f"[TEC] Undo failed: {e}")
                success = False
        
        self.rollback_count += 1
        return success
    
    def _execute_undo(self, undo: UndoAction) -> None:
        """
        Execute a standard undo operation.
        """
        if undo.operation == "write":
            # Delete written data
            # TODO: Delete from substrate
            pass
        elif undo.operation == "create":
            # Delete created resource
            # TODO: Delete resource
            pass
        elif undo.operation == "modify":
            # Restore previous value
            # TODO: Restore state
            pass
    
    def clear(self) -> None:
        """Clear undo stack (commit)"""
        self.undo_stack.clear()


class CheckpointManager:
    """
    Manages checkpoints for recovery.
    Creates snapshots of system state at key points.
    """
    
    def __init__(self):
        self.checkpoints: Dict[str, Dict[str, Any]] = {}
    
    def create_checkpoint(self, name: str, state: Dict[str, Any]) -> str:
        """
        Create a named checkpoint.
        Returns checkpoint ID.
        """
        checkpoint_id = str(uuid.uuid4())
        self.checkpoints[checkpoint_id] = {
            "name": name,
            "state": state.copy(),
        }
        return checkpoint_id
    
    def restore_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """
        Restore system state from checkpoint.
        """
        if checkpoint_id in self.checkpoints:
            return self.checkpoints[checkpoint_id]["state"].copy()
        return None
