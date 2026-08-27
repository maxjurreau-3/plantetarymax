"""
SIM Trajectory Layer
Rebuild 2: Reasoning Path Tracking

Tracks the execution path through reasoning steps.
Enables explanation, backtracking, and validation.
"""

from typing import Dict, Any, List, Optional, Deque
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import time


class StepType(Enum):
    """Type of reasoning step"""
    OBSERVATION = "observation"
    INFERENCE = "inference"
    DECISION = "decision"
    ACTION = "action"
    REFLECTION = "reflection"


class StepStatus(Enum):
    """Status of a reasoning step"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    BACKTRACKED = "backtracked"


@dataclass
class ReasoningStep:
    """A single step in reasoning"""
    id: str
    type: StepType
    status: StepStatus
    input: Dict[str, Any]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: float = 0.0
    duration_ms: float = 0.0
    children: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None


class ExecutionTree:
    """Tree of reasoning steps"""
    
    def __init__(self):
        self.steps: Dict[str, ReasoningStep] = {}
        self.root_ids: List[str] = []
    
    def add_step(self, step: ReasoningStep) -> None:
        """Add a step to tree"""
        self.steps[step.id] = step
        
        if step.parent_id is None:
            self.root_ids.append(step.id)
        else:
            parent = self.steps.get(step.parent_id)
            if parent:
                parent.children.append(step.id)
    
    def get_path_to_step(self, step_id: str) -> List[ReasoningStep]:
        """Get path from root to step"""
        step = self.steps.get(step_id)
        if not step:
            return []
        
        path = [step]
        current = step
        
        while current.parent_id:
            parent = self.steps.get(current.parent_id)
            if parent:
                path.insert(0, parent)
                current = parent
            else:
                break
        
        return path
    
    def get_subtree(self, step_id: str) -> List[ReasoningStep]:
        """Get all descendants of step"""
        step = self.steps.get(step_id)
        if not step:
            return []
        
        result = [step]
        queue: Deque[str] = deque(step.children)
        
        while queue:
            child_id = queue.popleft()
            child = self.steps.get(child_id)
            if child:
                result.append(child)
                queue.extend(child.children)
        
        return result


class ReasoningTrajectory:
    """
    The path through reasoning space.
    Enables backtracking and explanation.
    """
    
    def __init__(self):
        self.tree = ExecutionTree()
        self.current_step_id: Optional[str] = None
        self.step_sequence: List[str] = []
    
    def begin_step(
        self,
        step_id: str,
        step_type: StepType,
        input_data: Dict[str, Any],
        parent_id: Optional[str] = None,
    ) -> ReasoningStep:
        """Start a new reasoning step"""
        step = ReasoningStep(
            id=step_id,
            type=step_type,
            status=StepStatus.EXECUTING,
            input=input_data,
            timestamp=time.time(),
            parent_id=parent_id,
        )
        
        self.tree.add_step(step)
        self.step_sequence.append(step_id)
        self.current_step_id = step_id
        
        return step
    
    def complete_step(
        self,
        step_id: str,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Complete a reasoning step"""
        step = self.tree.steps.get(step_id)
        if not step:
            return
        
        step.status = StepStatus.FAILED if error else StepStatus.SUCCESS
        step.output = output
        step.error = error
        step.duration_ms = (time.time() - step.timestamp) * 1000
    
    def backtrack(self, steps: int = 1) -> bool:
        """
        Backtrack from current step.
        Mark backtracked steps.
        """
        if steps > len(self.step_sequence):
            return False
        
        for i in range(steps):
            step_id = self.step_sequence[-1]
            step = self.tree.steps.get(step_id)
            if step:
                step.status = StepStatus.BACKTRACKED
            self.step_sequence.pop()
        
        self.current_step_id = self.step_sequence[-1] if self.step_sequence else None
        return True
    
    def explain(self, step_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Explain reasoning leading to step.
        Returns path and justifications.
        """
        target_id = step_id or self.current_step_id
        if not target_id:
            return {"explanation": "No steps executed"}
        
        path = self.tree.get_path_to_step(target_id)
        
        return {
            "target_step_id": target_id,
            "path_length": len(path),
            "steps": [
                {
                    "id": s.id,
                    "type": s.type.value,
                    "status": s.status.value,
                    "duration_ms": s.duration_ms,
                }
                for s in path
            ],
        }


class SIMTrajectory:
    """
    SIM reasoning trajectory layer.
    Tracks execution path and enables reasoning about reasoning.
    """
    
    def __init__(self):
        self.trajectory = ReasoningTrajectory()
        self.max_depth = 100
        self.depth_exceeded = False
    
    def record_step(
        self,
        step_type: StepType,
        input_data: Dict[str, Any],
    ) -> str:
        """Record a reasoning step"""
        step_id = f"{step_type.value}_{len(self.trajectory.step_sequence)}"
        self.trajectory.begin_step(step_id, step_type, input_data)
        
        if len(self.trajectory.step_sequence) > self.max_depth:
            self.depth_exceeded = True
        
        return step_id
    
    def complete_step(
        self,
        step_id: str,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> None:
        """Mark step as complete"""
        self.trajectory.complete_step(step_id, output, error)
    
    def get_reasoning_path(self) -> List[Dict[str, Any]]:
        """Get current reasoning path"""
        return [
            {
                "step_id": step_id,
                "step_type": self.trajectory.tree.steps[step_id].type.value,
            }
            for step_id in self.trajectory.step_sequence
        ]
    
    def is_valid_trajectory(self) -> bool:
        """Verify trajectory coherence"""
        # TODO: Check for discontinuities, loops, invalid transitions
        return not self.depth_exceeded
