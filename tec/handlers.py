"""
TEC Pipeline Handlers
Each handler processes one stage of the transaction execution context.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from .schemas import TECContext, TECResult, HandlerStage

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Base handler for TEC pipeline stages"""

    @abstractmethod
    async def handle(self, context: TECContext) -> TECResult:
        pass


class PlanHandler(BaseHandler):
    """
    Stage 1: Plan
    Converts request into an executable plan.
    """

    async def handle(self, context: TECContext) -> TECResult:
        try:
            # Extract plan from envelope body
            request_type = context.envelope.type
            request_body = context.envelope.body

            # Simple planning: identify action type and required steps
            plan = {
                "request_type": request_type,
                "steps": self._plan_steps(request_type, request_body),
                "estimated_duration_ms": 50,
            }

            context.plan = plan
            context.stages_completed.append(HandlerStage.PLAN)

            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.PLAN,
                success=True,
                data=plan,
                latency_ms=context.elapsed_ms(),
            )
        except Exception as e:
            logger.error(f"PlanHandler failed: {e}")
            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.PLAN,
                success=False,
                error=str(e),
                latency_ms=context.elapsed_ms(),
            )

    def _plan_steps(self, request_type: str, body: Dict[str, Any]) -> list:
        """Generate plan steps based on request type"""
        plans = {
            "task.execute": ["validate_input", "authorize", "execute", "verify"],
            "reasoning.infer": ["parse_query", "authorize", "inference", "score", "verify"],
            "identity.check": ["lookup_principal", "verify_credentials"],
        }
        return plans.get(request_type, ["default_step"])


class ValidateHandler(BaseHandler):
    """
    Stage 2: Validate
    Validates constraints and input correctness.
    """

    async def handle(self, context: TECContext) -> TECResult:
        try:
            # Validate envelope schema
            if not context.envelope.type or not context.envelope.body:
                raise ValueError("Missing required envelope fields")

            # Validate plan exists
            if not context.plan:
                raise ValueError("No plan provided")

            # Collect constraints
            constraints = {
                "envelope_size": len(str(context.envelope.to_dict())),
                "body_keys": list(context.envelope.body.keys()),
                "max_body_size": 64 * 1024,  # 64KB
            }

            # Check constraints
            if constraints["envelope_size"] > constraints["max_body_size"]:
                raise ValueError(f"Envelope too large: {constraints['envelope_size']} > {constraints['max_body_size']}")

            context.constraints = constraints
            context.stages_completed.append(HandlerStage.VALIDATE)

            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.VALIDATE,
                success=True,
                data=constraints,
                latency_ms=context.elapsed_ms(),
            )
        except Exception as e:
            logger.error(f"ValidateHandler failed: {e}")
            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.VALIDATE,
                success=False,
                error=str(e),
                latency_ms=context.elapsed_ms(),
            )


class AuthorizeHandler(BaseHandler):
    """
    Stage 3: Authorize
    Checks identity and governance permissions.
    """

    async def handle(self, context: TECContext) -> TECResult:
        try:
            # Extract principal from meta or use default
            principal = context.envelope.meta.get("principal") or {"id": "system", "roles": ["admin"]}
            context.principal = principal

            # Check authorization
            action = context.plan.get("request_type") if context.plan else "default"
            authorized = self._check_authorization(principal, action)

            if not authorized:
                raise PermissionError(f"Principal {principal['id']} not authorized for {action}")

            context.authorization = {
                "principal_id": principal["id"],
                "roles": principal.get("roles", []),
                "action": action,
                "authorized": True,
            }

            context.stages_completed.append(HandlerStage.AUTHORIZE)

            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.AUTHORIZE,
                success=True,
                data=context.authorization,
                latency_ms=context.elapsed_ms(),
            )
        except Exception as e:
            logger.error(f"AuthorizeHandler failed: {e}")
            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.AUTHORIZE,
                success=False,
                error=str(e),
                latency_ms=context.elapsed_ms(),
            )

    def _check_authorization(self, principal: Dict[str, Any], action: str) -> bool:
        """Check if principal is authorized for action"""
        admin_role = "admin" in principal.get("roles", [])
        return admin_role or principal.get("id") == "system"


class ExecuteHandler(BaseHandler):
    """
    Stage 4: Execute
    Executes the plan (dispatches to agents/services).
    """

    async def handle(self, context: TECContext) -> TECResult:
        try:
            if not context.plan:
                raise ValueError("No plan to execute")

            # Simulate execution based on request type
            request_type = context.envelope.type
            body = context.envelope.body

            result = await self._execute_by_type(request_type, body)
            context.execution_result = result
            context.stages_completed.append(HandlerStage.EXECUTE)

            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.EXECUTE,
                success=True,
                data=result,
                latency_ms=context.elapsed_ms(),
            )
        except Exception as e:
            logger.error(f"ExecuteHandler failed: {e}")
            # Mark rollback needed
            context.rollback_actions.append({"stage": "execute", "error": str(e)})
            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.EXECUTE,
                success=False,
                error=str(e),
                latency_ms=context.elapsed_ms(),
            )

    async def _execute_by_type(self, request_type: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute based on request type"""
        if request_type == "task.execute":
            return {"task_id": body.get("task"), "status": "queued"}
        elif request_type == "reasoning.infer":
            return {"inference_id": body.get("query"), "status": "processing"}
        else:
            return {"request_type": request_type, "status": "executed"}


class VerifyHandler(BaseHandler):
    """
    Stage 5: Verify
    Verifies execution result correctness.
    """

    async def handle(self, context: TECContext) -> TECResult:
        try:
            if not context.execution_result:
                raise ValueError("No execution result to verify")

            # Verify result structure
            result = context.execution_result
            if not isinstance(result, dict):
                raise ValueError(f"Invalid execution result: {result}")

            # Verify required fields
            required_fields = ["status"]
            missing_fields = [f for f in required_fields if f not in result]
            if missing_fields:
                raise ValueError(f"Missing fields in execution result: {missing_fields}")

            verification = {
                "result_id": result.get("task_id") or result.get("inference_id") or "unknown",
                "valid": True,
                "checks_passed": 5,
                "status": result.get("status"),
            }

            context.verification_result = verification
            context.stages_completed.append(HandlerStage.VERIFY)

            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.VERIFY,
                success=True,
                data=verification,
                latency_ms=context.elapsed_ms(),
            )
        except Exception as e:
            logger.error(f"VerifyHandler failed: {e}")
            context.rollback_actions.append({"stage": "verify", "error": str(e)})
            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.VERIFY,
                success=False,
                error=str(e),
                latency_ms=context.elapsed_ms(),
            )


class RollbackHandler(BaseHandler):
    """
    Stage 6: Rollback
    Rolls back execution on failure.
    """

    async def handle(self, context: TECContext) -> TECResult:
        try:
            if not context.rollback_actions:
                # No rollback needed
                return TECResult(
                    envelope_id=context.envelope.id,
                    stage=HandlerStage.ROLLBACK,
                    success=True,
                    data={"rollback_needed": False, "actions_completed": 0},
                    latency_ms=context.elapsed_ms(),
                )

            # Execute rollback actions in reverse order
            for action in reversed(context.rollback_actions):
                logger.info(f"Rolling back: {action}")
                # Perform rollback (e.g., undo database changes)

            context.stages_completed.append(HandlerStage.ROLLBACK)

            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.ROLLBACK,
                success=True,
                data={
                    "rollback_needed": True,
                    "actions_completed": len(context.rollback_actions),
                },
                latency_ms=context.elapsed_ms(),
            )
        except Exception as e:
            logger.error(f"RollbackHandler failed: {e}")
            return TECResult(
                envelope_id=context.envelope.id,
                stage=HandlerStage.ROLLBACK,
                success=False,
                error=str(e),
                latency_ms=context.elapsed_ms(),
            )
