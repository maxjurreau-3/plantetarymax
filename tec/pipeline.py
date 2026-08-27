"""
TEC Execution Pipelines
Rebuild 2: Execution Layer Pipelines

Defines the execution pipelines that route SIM decisions → TEC agents → Substrate.
Pipelines are the bridge between cognition and action.
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid


class PipelineStage(Enum):
    """Stages in execution pipeline"""
    PLAN = "plan"
    VALIDATE = "validate"
    AUTHORIZE = "authorize"
    EXECUTE = "execute"
    VERIFY = "verify"
    ROLLBACK = "rollback"


class ExecutionStatus(Enum):
    """Status of execution"""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class ExecutionPlan:
    """A plan for execution"""
    id: str
    goal: Dict[str, Any]
    actions: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    priority: int = 0
    timeout_ms: int = 30000


class PipelineStageHandler:
    """Handles execution at a specific pipeline stage"""
    
    def __init__(self, stage: PipelineStage):
        self.stage = stage
        self.handlers: List[Callable] = []
    
    def register(self, handler: Callable) -> None:
        """Register a handler"""
        self.handlers.append(handler)
    
    def execute(self, context: Dict[str, Any]) -> bool:
        """Execute all handlers at this stage"""
        for handler in self.handlers:
            try:
                if not handler(context):
                    return False
            except Exception as e:
                print(f"[TEC] Handler error at {self.stage.value}: {e}")
                return False
        return True


class ExecutionPipeline:
    """
    Execution pipeline from plan → action.
    Manages stages: plan, validate, authorize, execute, verify, rollback.
    """
    
    def __init__(self):
        self.stages: Dict[PipelineStage, PipelineStageHandler] = {
            stage: PipelineStageHandler(stage) for stage in PipelineStage
        }
        self.executions: Dict[str, Dict[str, Any]] = {}
    
    def submit_plan(self, plan: ExecutionPlan) -> str:
        """Submit an execution plan"""
        self.executions[plan.id] = {
            "plan": plan,
            "status": ExecutionStatus.PENDING,
            "stage": PipelineStage.PLAN,
        }
        return plan.id
    
    def execute_plan(self, plan_id: str) -> bool:
        """
        Execute pipeline stages for a plan.
        Returns success.
        """
        execution = self.executions.get(plan_id)
        if not execution:
            return False
        
        plan = execution["plan"]
        context = {"plan": plan, "execution_id": plan_id}
        
        # Execute stages in order
        stages = [
            PipelineStage.PLAN,
            PipelineStage.VALIDATE,
            PipelineStage.AUTHORIZE,
            PipelineStage.EXECUTE,
            PipelineStage.VERIFY,
        ]
        
        for stage in stages:
            execution["stage"] = stage
            execution["status"] = ExecutionStatus.EXECUTING
            
            handler = self.stages[stage]
            if not handler.execute(context):
                print(f"[TEC] Pipeline failed at {stage.value}")
                execution["status"] = ExecutionStatus.FAILED
                self._rollback(plan_id, context)
                return False
        
        execution["status"] = ExecutionStatus.SUCCESS
        return True
    
    def _rollback(self, plan_id: str, context: Dict[str, Any]) -> None:
        """Rollback execution"""
        execution = self.executions.get(plan_id)
        if execution:
            execution["status"] = ExecutionStatus.ROLLED_BACK
            handler = self.stages[PipelineStage.ROLLBACK]
            handler.execute(context)


class TECPipeline:
    """
    TEC execution pipeline layer.
    Manages the full journey from SIM decisions → substrate actions.
    """
    
    def __init__(self):
        self.pipeline = ExecutionPipeline()
    
    def submit_action(
        self,
        goal: Dict[str, Any],
        actions: List[Dict[str, Any]],
    ) -> str:
        """Submit an action sequence for execution"""
        plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            goal=goal,
            actions=actions,
        )
        return self.pipeline.submit_plan(plan)
    
    def execute_action(self, action_id: str) -> bool:
        """Execute an action"""
        return self.pipeline.execute_plan(action_id)
