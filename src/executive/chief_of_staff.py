import logging
import traceback
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
    Transforms executive vision into coordinated action.
    No cognitive reasoning, purely operational.
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
            logger.info("[CoS] Subscribed to TaskCompleted and TaskFailed events.")
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

    # ---------- Core Scheduling ----------
    def schedule_task(self, task: Task) -> None:
        """
        Schedule a task by resolving its capability to a department.
        Enforces that every Task belongs to a Goal.
        """
        logger.info(f"[CoS] Scheduling task {task.uuid}: capability='{task.target_capability}'")

        # ---- Enforce Goal ownership ----
        if not task.goal_uuid:
            error_msg = f"Task {task.uuid} rejected: missing goal_uuid. Every Task must belong to a Goal."
            logger.error(f"[CoS] {error_msg}")
            task.transition_to(ExecutionState.FAILED)
            task.error_message = error_msg
            self.event_bus.publish(Event(
                event_type="TaskRejected",
                source="ChiefOfStaff",
                payload={
                    "task_id": str(task.uuid),
                    "reason": error_msg,
                    "goal_uuid": str(task.goal_uuid) if task.goal_uuid else None,
                }
            ))
            return

        logger.info(f"[CoS] Task {task.uuid} belongs to Goal: {task.goal_uuid}")

        try:
            # Try to find department from the old registry first
            dept_name = self.cap_registry.find_department(task.target_capability)

            # If not found, try the tool registry (new capabilities)
            if not dept_name and self.tool_registry:
                cap_def = self.tool_registry.get(task.target_capability)
                if cap_def and cap_def.department:
                    dept_name = cap_def.department
                    logger.info(f"[CoS] Found capability in tool registry with department: {dept_name}")

            if not dept_name:
                msg = f"Capability '{task.target_capability}' not found in any registry."
                logger.error(f"[CoS] {msg}")
                self._escalate_failure(task, msg)
                return

            logger.info(f"[CoS] Resolved '{task.target_capability}' → department '{dept_name}'")
            task.assigned_department_id = dept_name
            task.transition_to(ExecutionState.ACCEPTED)

            key = str(task.uuid)
            self.active_tasks[key] = task
            if key not in self.retries:
                self.retries[key] = 0

            self.event_bus.publish(Event(
                event_type="DepartmentAssigned",
                source="ChiefOfStaff",
                payload={"task_id": key, "department": dept_name, "goal_uuid": str(task.goal_uuid)}
            ))
            logger.debug(f"[CoS] Task {key} assigned to {dept_name}.")

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[CoS] Unexpected error scheduling task {task.uuid}: {e}\n{error_trace}")
            self._escalate_failure(task, f"Scheduling error: {str(e)}")

    def _escalate_failure(self, task: Task, reason: str):
        logger.warning(f"[CoS] Escalating failure for task {task.uuid}: {reason}")
        task.transition_to(ExecutionState.FAILED)
        task.error_message = reason
        self.event_bus.publish(Event(
            event_type="OperationalEscalation",
            source="ChiefOfStaff",
            payload={"task_id": str(task.uuid), "reason": reason}
        ))
        key = str(task.uuid)
        if key in self.active_tasks:
            del self.active_tasks[key]

    # ---------- Monitoring ----------
    def monitor_progress(self) -> Dict[str, Any]:
        return {
            "active_count": len(self.active_tasks),
            "tasks": [
                {
                    "uuid": str(t.uuid),
                    "goal_uuid": str(t.goal_uuid) if t.goal_uuid else None,
                    "capability": t.target_capability,
                    "state": t.state.value,
                    "progress": t.progress,
                }
                for t in self.active_tasks.values()
            ]
        }

    # ---------- Event Handlers ----------
    def _on_task_completed(self, event: Event):
        task_id = event.payload.get("task_id")
        if not task_id:
            logger.warning("[CoS] TaskCompleted event missing 'task_id' payload.")
            return

        if task_id in self.active_tasks:
            logger.info(f"[CoS] Task {task_id} marked as COMPLETED.")
            self.active_tasks[task_id].transition_to(ExecutionState.COMPLETED)
            del self.active_tasks[task_id]
            if task_id in self.retries:
                del self.retries[task_id]

    def _on_task_failed(self, event: Event):
        task_id = event.payload.get("task_id")
        if not task_id:
            logger.warning("[CoS] TaskFailed event missing 'task_id' payload.")
            return

        if task_id not in self.active_tasks:
            logger.debug(f"[CoS] Task {task_id} not in active list.")
            return

        current_retries = self.retries.get(task_id, 0) + 1
        self.retries[task_id] = current_retries
        task = self.active_tasks[task_id]

        if current_retries <= self.MAX_RETRIES:
            logger.info(f"[CoS] Task {task_id} failed (attempt {current_retries}/{self.MAX_RETRIES}). Retrying...")
            task.transition_to(ExecutionState.READY)
            dept_name = task.assigned_department_id
            if dept_name:
                self.event_bus.publish(Event(
                    event_type="DepartmentAssigned",
                    source="ChiefOfStaff",
                    payload={
                        "task_id": task_id,
                        "department": dept_name,
                        "retry": current_retries,
                        "goal_uuid": str(task.goal_uuid) if task.goal_uuid else None,
                    }
                ))
            else:
                dept_name = self.cap_registry.find_department(task.target_capability)
                if dept_name:
                    task.assigned_department_id = dept_name
                    self.event_bus.publish(Event(
                        event_type="DepartmentAssigned",
                        source="ChiefOfStaff",
                        payload={
                            "task_id": task_id,
                            "department": dept_name,
                            "retry": current_retries,
                            "goal_uuid": str(task.goal_uuid) if task.goal_uuid else None,
                        }
                    ))
                else:
                    self._escalate_failure(task, f"Retry failed: capability '{task.target_capability}' still unresolved.")
        else:
            logger.error(f"[CoS] Task {task_id} failed after {self.MAX_RETRIES} retries. Escalating.")
            self._escalate_failure(task, f"Max retries ({self.MAX_RETRIES}) exceeded.")

    # ---------- Shutdown ----------
    def shutdown(self):
        logger.info("[CoS] Shutting down.")
        try:
            self.event_bus.unsubscribe("TaskCompleted", self._on_task_completed)
            self.event_bus.unsubscribe("TaskFailed", self._on_task_failed)
        except Exception as e:
            logger.warning(f"[CoS] Error unsubscribing: {e}")
        self.active_tasks.clear()
        self.retries.clear()
