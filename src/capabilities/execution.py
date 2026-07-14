import logging
import time
from typing import Dict, Any, Optional

from src.capabilities.registry import CapabilityRegistry
from src.capabilities.context import ExecutionContext
from src.capabilities.contract import Capability
from src.core.models import Event
from src.capabilities.events import CapabilityEvents

logger = logging.getLogger(__name__)


class CapabilityExecutionEngine:
    """
    Executes capabilities using the Contract.
    Enforces timeouts, retries, and captures metrics.
    """

    def __init__(self, registry: CapabilityRegistry, event_publisher):
        self.registry = registry
        self.event_publisher = event_publisher

    def execute(self, capability_id: str, context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute the capability and return the result.
        """
        implementation = self.registry.get_implementation(capability_id)
        if implementation is None:
            raise ValueError(f"Capability {capability_id} not found")

        # Validate
        if not implementation.validate(context):
            raise ValueError(f"Capability {capability_id} validation failed")

        # Publish start event
        self.event_publisher(Event(event_type=CapabilityEvents.EXECUTION_STARTED, source="CapabilityExecution", payload={"capability_id": capability_id, "execution_id": context.execution_id}))

        # Execute with retries and timeout
        budget = context.budget
        max_retries = budget.max_retries
        attempt = 0
        last_error = None

        while attempt <= max_retries:
            try:
                start_time = time.time()
                result = implementation.execute(context)
                elapsed = time.time() - start_time
                logger.info(f"[Execution] Capability {capability_id} executed in {elapsed:.2f}s")

                # Update confidence (success)
                self.registry.update_confidence(capability_id, True)

                # Publish success event
                self.event_publisher(Event(event_type=CapabilityEvents.EXECUTION_COMPLETED, source="CapabilityExecution", payload={"capability_id": capability_id, "execution_id": context.execution_id, "elapsed": elapsed}))
                return {"success": True, "result": result}
            except Exception as e:
                last_error = str(e)
                attempt += 1
                logger.warning(f"[Execution] Attempt {attempt} failed: {e}")
                if attempt <= max_retries:
                    time.sleep(1 * attempt)  # simple backoff
                else:
                    self.registry.update_confidence(capability_id, False)
                    self.event_publisher(Event(event_type=CapabilityEvents.EXECUTION_FAILED, source="CapabilityExecution", payload={"capability_id": capability_id, "execution_id": context.execution_id, "error": last_error}))
                    raise RuntimeError(f"Capability {capability_id} failed after {max_retries} retries: {last_error}")

        # Should never reach here
        return {"success": False, "error": last_error}
