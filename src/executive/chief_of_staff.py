import logging
import traceback
import time
from typing import Dict, Any, List, Optional

from src.core.interfaces import IChiefOfStaff, IEventBus
from src.core.models import Task, Event, Priority, ExecutionState
from src.core.registry import CapabilityRegistry, DepartmentRegistry
from src.core.tools import ToolRegistry

try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

logger = logging.getLogger(__name__)


class ChiefOfStaff(IChiefOfStaff):
    """
    Chief of Staff focuses on execution.
    Now synchronous: executes capabilities and returns results.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        cap_registry: CapabilityRegistry,
        dept_registry: DepartmentRegistry,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.event_bus = event_bus
        self.cap_registry = cap_registry
        self.dept_registry = dept_registry
        self.tool_registry = tool_registry

        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        self.active_tasks: Dict[str, Task] = {}
        self.retries: Dict[str, int] = {}
        self.MAX_RETRIES = 3

        try:
            self.event_bus.subscribe("TaskCompleted", self._on_task_completed)
            self.event_bus.subscribe("TaskFailed", self._on_task_failed)
            logger.info("[CoS] Subscribed to TaskCompleted and TaskFailed events (observability).")
        except Exception as e:
            logger.error(f"[CoS] Failed to subscribe to events: {e}", exc_info=True)
            raise

        logger.info(
            f"[CoS] Initialized. SecureMemory: {secure_memory is not None}, "
            f"SecureRunner: {secure_runner is not None}, "
            f"ToolRegistry: {tool_registry is not None}"
        )

    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        self._secure_memory = secure_memory
        logger.info("[CoS] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        self._secure_runner = secure_runner
        logger.info("[CoS] SecureCommandRunner attached.")

    def set_tool_registry(self, tool_registry: ToolRegistry):
        """Inject tool registry after construction."""
        self.tool_registry = tool_registry
        logger.info("[CoS] ToolRegistry attached.")

    # ---------- Core Synchronous Execution ----------
    def schedule_task(self, task: Task) -> Any:
        """Execute task synchronously and return result."""
        logger.info(f"[CoS] Executing task {task.uuid}: capability='{task.target_capability}'")

        if not task.goal_uuid:
            error_msg = f"Task {task.uuid} rejected: missing goal_uuid."
            logger.error(f"[CoS] {error_msg}")
            task.transition_to(ExecutionState.FAILED)
            task.error_message = error_msg
            self._publish_event("TaskRejected", {"task_id": str(task.uuid), "reason": error_msg})
            raise ValueError(error_msg)

        # Extract parameters from input_data
        params = getattr(task, 'input_data', {})
        if not params:
            # Fallback for backward compatibility
            params = getattr(task, 'parameters', {}) or getattr(task, 'params', {})
        if not isinstance(params, dict):
            params = {"objective": str(params)} if params else {}

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                # Resolve capability
                if self.tool_registry:
                    cap_def = self.tool_registry.get(task.target_capability)
                    if cap_def:
                        # If the capability has a direct handler, call it directly
                        if hasattr(cap_def, 'handler') and cap_def.handler is not None:
                            logger.info(f"[CoS] Using direct handler for {task.target_capability}")
                            result = cap_def.handler(**params)
                            # Ensure result is serializable
                            task.transition_to(ExecutionState.COMPLETED)
                            self._publish_event("TaskCompleted", {"task_id": str(task.uuid), "result": result})
                            self._cleanup_task(task)
                            return result
                        else:
                            # Fallback to the tool registry execution (which may create internal Tasks)
                            result = self.tool_registry.execute_tool(task.target_capability, params)
                            task.transition_to(ExecutionState.COMPLETED)
                            self._publish_event("TaskCompleted", {"task_id": str(task.uuid), "result": result})
                            self._cleanup_task(task)
                            return result

                if self.cap_registry and hasattr(self.cap_registry, 'get_capability'):
                    capability = self.cap_registry.get_capability(task.target_capability)
                    if capability and hasattr(capability, 'execute'):
                        logger.info(f"[CoS] Found in cap_registry: {task.target_capability}")
                        from src.capabilities.context import ExecutionContext
                        context = ExecutionContext(extra={"params": params})
                        result = capability.execute(context)
                        if isinstance(result, dict) and "result" in result:
                            result = result["result"]
                        task.transition_to(ExecutionState.COMPLETED)
                        self._publish_event("TaskCompleted", {"task_id": str(task.uuid), "result": result})
                        self._cleanup_task(task)
                        return result

                msg = f"Capability '{task.target_capability}' not found."
                logger.error(f"[CoS] {msg}")
                task.transition_to(ExecutionState.FAILED)
                task.error_message = msg
                self._publish_event("OperationalEscalation", {"task_id": str(task.uuid), "reason": msg})
                raise RuntimeError(msg)

            except Exception as e:
                last_error = e
                logger.error(f"[CoS] Task {task.uuid} attempt {attempt} failed: {e}")
                self._publish_event("TaskFailed", {"task_id": str(task.uuid), "attempt": attempt, "error": str(e)})

                if attempt < self.MAX_RETRIES:
                    logger.info(f"[CoS] Retrying task {task.uuid} in 1 second...")
                    time.sleep(1)
                    task.transition_to(ExecutionState.READY)
                else:
                    task.transition_to(ExecutionState.FAILED)
                    task.error_message = str(e)
                    self._publish_event("OperationalEscalation", {
                        "task_id": str(task.uuid),
                        "reason": f"Max retries exceeded: {str(e)}"
                    })
                    self._cleanup_task(task)
                    raise RuntimeError(f"Task {task.uuid} failed after {self.MAX_RETRIES} retries") from e

        raise RuntimeError(f"Task {task.uuid} failed for unknown reasons.")

    def _cleanup_task(self, task: Task):
        key = str(task.uuid)
        self.active_tasks.pop(key, None)
        self.retries.pop(key, None)

    def _publish_event(self, event_type: str, payload: Dict[str, Any]):
        try:
            self.event_bus.publish(Event(event_type=event_type, source="ChiefOfStaff", payload=payload))
        except Exception as e:
            logger.warning(f"[CoS] Failed to publish {event_type}: {e}")

    # ---------- Monitoring ----------
    def monitor_progress(self) -> Dict[str, Any]:
        return {
            "active_count": len(self.active_tasks),
            "tasks": [{"uuid": str(t.uuid), "state": t.state.value} for t in self.active_tasks.values()]
        }

    # ---------- Event Handlers (observability) ----------
    def _on_task_completed(self, event: Event):
        pass  # already handled synchronously

    def _on_task_failed(self, event: Event):
        pass

    def shutdown(self):
        logger.info("[CoS] Shutting down.")
        self.active_tasks.clear()
        self.retries.clear()
