"""
End-to-End Message Flow
Rebuild 3: Complete System Integration

Implements the complete message flow from Worker to Substrate.
Worker HTTP → Kernel → SIM → TEC → Substrate → HTTP Response
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
import time


@dataclass
class EndToEndFlow:
    """End-to-end flow metrics"""
    request_id: str
    start_time: float
    end_time: Optional[float] = None
    stages: Dict[str, float] = None
    
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return 0.0


class EndToEndMessageFlow:
    """
    Orchestrates complete message flow through system.
    
    Flow:
    1. Worker HTTP POST /message
    2. HTTP Handler parses request
    3. Message queued to Kernel
    4. Kernel scheduler routes to COGNITIVE lane
    5. SIM Core performs inference
    6. Inference result cached
    7. Message routed to TEC lane
    8. TEC Pipeline executes (6 stages)
    9. Execution results routed to SUBSTRATE lane
    10. Substrate persists state (DO + KV)
    11. Response built and returned to Worker
    12. HTTP 200 with result
    """
    
    def __init__(self):
        self.flows: Dict[str, EndToEndFlow] = {}
    
    def process_request(
        self,
        request_id: str,
        request_data: Dict[str, Any],
        kernel,
        sim,
        tec,
        substrate,
    ) -> Dict[str, Any]:
        """
        Process a complete request through all layers.
        
        Args:
            request_id: Unique request identifier
            request_data: Parsed HTTP request data
            kernel: Kernel scheduler instance
            sim: SIM cognitive instance
            tec: TEC execution instance
            substrate: Substrate state instance
        
        Returns:
            Response data for HTTP
        """
        flow = EndToEndFlow(request_id=request_id, start_time=time.time())
        flow.stages = {}
        
        try:
            # Stage 1: Cognitive Processing
            stage_start = time.time()
            reasoning_result = self._cognitive_stage(request_data, sim)
            flow.stages["cognitive"] = time.time() - stage_start
            
            if not reasoning_result.get("success"):
                return self._error_response(request_id, reasoning_result.get("error"))
            
            # Stage 2: TEC Execution
            stage_start = time.time()
            execution_result = self._execution_stage(
                request_data,
                reasoning_result,
                tec,
            )
            flow.stages["execution"] = time.time() - stage_start
            
            if not execution_result.get("success"):
                return self._error_response(request_id, execution_result.get("error"))
            
            # Stage 3: Persistence
            stage_start = time.time()
            persist_result = self._persistence_stage(
                execution_result,
                substrate,
            )
            flow.stages["persistence"] = time.time() - stage_start
            
            if not persist_result.get("success"):
                return self._error_response(request_id, persist_result.get("error"))
            
            # Build response
            flow.end_time = time.time()
            self.flows[request_id] = flow
            
            return self._success_response(
                request_id,
                reasoning_result,
                execution_result,
                flow,
            )
        
        except Exception as e:
            return self._error_response(request_id, str(e))
    
    def _cognitive_stage(
        self,
        request: Dict[str, Any],
        sim,
    ) -> Dict[str, Any]:
        """
        Cognitive processing stage: SIM inference
        """
        try:
            goal = request.get("goal")
            if not goal:
                return {"success": False, "error": "No goal in request"}
            
            # Run inference
            result = sim.reason({"query": goal})
            
            return {
                "success": True,
                "reasoning": result,
                "confidence": result.get("confidence", 0.5),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _execution_stage(
        self,
        request: Dict[str, Any],
        cognitive_result: Dict[str, Any],
        tec,
    ) -> Dict[str, Any]:
        """
        Execution stage: TEC pipeline
        """
        try:
            actions = request.get("actions", [])
            
            # Submit to TEC
            action_id = tec.submit_action(
                goal=request.get("goal"),
                actions=actions,
            )
            
            # Execute
            success = tec.execute_action(action_id)
            
            return {
                "success": success,
                "action_id": action_id,
                "status": "executed" if success else "failed",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _persistence_stage(
        self,
        execution_result: Dict[str, Any],
        substrate,
    ) -> Dict[str, Any]:
        """
        Persistence stage: Write to substrate
        """
        try:
            # Write execution result
            key = f"execution_{execution_result.get('action_id')}"
            substrate.write_persistent(key, execution_result)
            
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _success_response(
        self,
        request_id: str,
        reasoning: Dict[str, Any],
        execution: Dict[str, Any],
        flow: EndToEndFlow,
    ) -> Dict[str, Any]:
        """
        Build success response
        """
        return {
            "status": 200,
            "request_id": request_id,
            "result": {
                "reasoning": reasoning,
                "execution": execution,
                "duration_ms": flow.duration_ms(),
                "stages": {
                    k: int(v * 1000) for k, v in flow.stages.items()
                },
            },
        }
    
    def _error_response(self, request_id: str, error: str) -> Dict[str, Any]:
        """
        Build error response
        """
        return {
            "status": 400,
            "request_id": request_id,
            "error": error,
        }
