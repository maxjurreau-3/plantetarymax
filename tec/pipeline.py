"""
TEC Pipeline Orchestration
Orchestrates the full TEC pipeline: Plan → Validate → Authorize → Execute → Verify → Rollback
"""

from typing import List
import logging
from .schemas import TECContext, TECEnvelope, TECResult, HandlerStage
from .handlers import (
    PlanHandler,
    ValidateHandler,
    AuthorizeHandler,
    ExecuteHandler,
    VerifyHandler,
    RollbackHandler,
)

logger = logging.getLogger(__name__)


class TECPipeline:
    """
    Transaction Execution Context Pipeline
    Processes envelopes through a 6-stage pipeline.
    """

    def __init__(self):
        self.handlers = {
            HandlerStage.PLAN: PlanHandler(),
            HandlerStage.VALIDATE: ValidateHandler(),
            HandlerStage.AUTHORIZE: AuthorizeHandler(),
            HandlerStage.EXECUTE: ExecuteHandler(),
            HandlerStage.VERIFY: VerifyHandler(),
            HandlerStage.ROLLBACK: RollbackHandler(),
        }

    async def process(self, envelope: TECEnvelope) -> TECResult:
        """
        Process an envelope through the TEC pipeline.
        Returns the final result (success or failure with rollback).
        """
        context = TECContext(envelope=envelope)
        results: List[TECResult] = []

        # Execute pipeline stages in order
        stages = [
            HandlerStage.PLAN,
            HandlerStage.VALIDATE,
            HandlerStage.AUTHORIZE,
            HandlerStage.EXECUTE,
            HandlerStage.VERIFY,
        ]

        for stage in stages:
            handler = self.handlers[stage]
            result = await handler.handle(context)
            results.append(result)

            logger.info(f"Stage {stage.value}: {'✓' if result.success else '✗'} ({result.latency_ms:.2f}ms)")

            # On failure, initiate rollback
            if not result.success:
                logger.warning(f"Pipeline failed at {stage.value}: {result.error}")
                rollback_result = await self.handlers[HandlerStage.ROLLBACK].handle(context)
                results.append(rollback_result)
                return self._aggregate_results(results, context)

        # All stages succeeded
        logger.info(f"Pipeline completed successfully for {envelope.id}")
        return self._aggregate_results(results, context)

    def _aggregate_results(self, results: List[TECResult], context: TECContext) -> TECResult:
        """
        Aggregate all stage results into a final result.
        """
        all_success = all(r.success for r in results)
        total_latency = sum(r.latency_ms for r in results)

        return TECResult(
            envelope_id=context.envelope.id,
            stage=HandlerStage.VERIFY if all_success else HandlerStage.ROLLBACK,
            success=all_success,
            data={
                "stages_completed": [s.value for s in context.stages_completed],
                "execution_result": context.execution_result,
                "verification_result": context.verification_result,
            },
            trace=[r.to_dict() for r in results],
            latency_ms=total_latency,
        )

    async def process_stream(self, envelopes: List[TECEnvelope]) -> List[TECResult]:
        """
        Process a stream of envelopes.
        """
        results = []
        for envelope in envelopes:
            result = await self.process(envelope)
            results.append(result)
        return results
