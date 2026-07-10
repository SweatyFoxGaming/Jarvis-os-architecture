import logging
import traceback
from typing import Dict, Any, List, Optional

# Secure components (injected for consistency)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.core.interfaces import IChiefOfStaff, IEventBus
from src.core.models import Task, TaskStatus, Event, Priority
from src.core.registry import CapabilityRegistry, DepartmentRegistry

# Logger
logger = logging.getLogger(__name__)


class ChiefOfStaff(IChiefOfStaff):
    """
    Chief of Staff focuses on execution.
    Transforms executive vision into coordinated action.
    No cognitive reasoning, purely operational.

    Now reinforced with logging, exception handling, and secure component injection.
    """

    def __init__(
        self,
        event_bus: IEventBus,
        cap_registry: CapabilityRegistry,
        dept_registry: DepartmentRegistry,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        self.event_bus = event_bus
        self.cap_registry = cap_registry
        self.dept_registry = dept_registry

        # Secure components (injected)
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        self.active_tasks: Dict[str, Task] = {}
        self.retries: Dict[str, int] = {}
        self.MAX_RETRIES = 3

        # Subscribe to event bus (with error handling)
        try:
            self.event_bus.subscribe("TaskCompleted", self._on_task_completed)
            self.event_bus.subscribe("TaskFailed", self._on_task_failed)
            logger.info("[CoS] Subscribed to TaskCompleted and TaskFailed events.")
        except Exception as e:
            logger.error(f"[CoS] Failed to subscribe to events: {e}", exc_info=True)
            raise

        logger.info(
            f"[CoS] Initialized. SecureMemory: {secure_memory is not None}, "
            f"SecureRunner: {secure_runner is not None}"
        )

    # ---------- Dependency Injection Setters ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        """Inject secure memory after construction."""
        self._secure_memory = secure_memory
        logger.info("[CoS] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        """Inject secure command runner after construction."""
        self._secure_runner = secure_runner
        logger.info("[CoS] SecureCommandRunner attached.")

    # ---------- Core Scheduling ----------
    def schedule_task(self, task: Task) -> None:
        """
        Schedule a task by resolving its capability to a department.
        If resolution fails, escalate the failure.
        """
        logger.info(f"[CoS] Scheduling task {task.uuid}: capability='{task.target_capability}'")

        try:
            # Resolve capability to department
            dept_name = self.cap_registry.find_department(task.target_capability)
            if not dept_name:
                msg = f"Capability '{task.target_capability}' not found in registry."
                logger.error(f"[CoS] {msg}")
                self._escalate_failure(task, msg)
                return

            logger.info(f"[CoS] Resolved '{task.target_capability}' → department '{dept_name}'")
            task.assigned_department_id = dept_name
            task.status = TaskStatus.ASSIGNED

            # Store task with string UUID as key
            key = str(task.uuid)
            self.active_tasks[key] = task
            # Initialize retry counter if not already present
            if key not in self.retries:
                self.retries[key] = 0

            # Publish assignment event
            self.event_bus.publish(Event(
                event_type="DepartmentAssigned",
                source="ChiefOfStaff",
                payload={"task_id": key, "department": dept_name}
            ))
            logger.debug(f"[CoS] Task {key} assigned to {dept_name}.")

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[CoS] Unexpected error scheduling task {task.uuid}: {e}\n{error_trace}")
            self._escalate_failure(task, f"Scheduling error: {str(e)}")

    def _escalate_failure(self, task: Task, reason: str):
        """Mark task as failed and publish an escalation event."""
        logger.warning(f"[CoS] Escalating failure for task {task.uuid}: {reason}")
        task.status = TaskStatus.FAILED
        task.error_message = reason
        self.event_bus.publish(Event(
            event_type="OperationalEscalation",
            source="ChiefOfStaff",
            payload={"task_id": str(task.uuid), "reason": reason}
        ))
        # Remove from active tasks if present
        key = str(task.uuid)
        if key in self.active_tasks:
            del self.active_tasks[key]

    # ---------- Monitoring ----------
    def monitor_progress(self) -> Dict[str, Any]:
        """Return a snapshot of current task progress."""
        return {
            "active_count": len(self.active_tasks),
            "tasks": [t.__dict__ for t in self.active_tasks.values()]  # or t.dict() if you have that
        }

    # ---------- Event Handlers ----------
    def _on_task_completed(self, event: Event):
        """Handle TaskCompleted events from the event bus."""
        task_id = event.payload.get("task_id")
        if not task_id:
            logger.warning("[CoS] TaskCompleted event missing 'task_id' payload.")
            return

        if task_id in self.active_tasks:
            logger.info(f"[CoS] Task {task_id} marked as COMPLETED.")
            self.active_tasks[task_id].status = TaskStatus.COMPLETED
            # Move to history (optional) — for now, just remove from active list
            del self.active_tasks[task_id]
            if task_id in self.retries:
                del self.retries[task_id]
        else:
            logger.debug(f"[CoS] Task {task_id} already removed from active list.")

    def _on_task_failed(self, event: Event):
        """
        Handle TaskFailed events. Implements a simple retry mechanism
        before escalating to permanent failure.
        """
        task_id = event.payload.get("task_id")
        if not task_id:
            logger.warning("[CoS] TaskFailed event missing 'task_id' payload.")
            return

        if task_id not in self.active_tasks:
            logger.debug(f"[CoS] Task {task_id} not in active list (already cleaned up).")
            return

        # Increment retry counter
        current_retries = self.retries.get(task_id, 0) + 1
        self.retries[task_id] = current_retries

        task = self.active_tasks[task_id]

        if current_retries <= self.MAX_RETRIES:
            logger.info(f"[CoS] Task {task_id} failed (attempt {current_retries}/{self.MAX_RETRIES}). Retrying...")
            # Reset status to PENDING so it can be rescheduled
            task.status = TaskStatus.PENDING
            # Optionally, we could call schedule_task again, but that would re-resolve capability.
            # For simplicity, we just re-assign to the same department and re-publish.
            dept_name = task.assigned_department_id
            if dept_name:
                self.event_bus.publish(Event(
                    event_type="DepartmentAssigned",
                    source="ChiefOfStaff",
                    payload={"task_id": task_id, "department": dept_name, "retry": current_retries}
                ))
                logger.debug(f"[CoS] Re-published DepartmentAssigned for {task_id}")
            else:
                # If department is missing, try to resolve again
                dept_name = self.cap_registry.find_department(task.target_capability)
                if dept_name:
                    task.assigned_department_id = dept_name
                    self.event_bus.publish(Event(
                        event_type="DepartmentAssigned",
                        source="ChiefOfStaff",
                        payload={"task_id": task_id, "department": dept_name, "retry": current_retries}
                    ))
                else:
                    self._escalate_failure(task, f"Retry failed: capability '{task.target_capability}' still unresolved.")
        else:
            # Exceeded retries – permanent failure
            logger.error(f"[CoS] Task {task_id} failed after {self.MAX_RETRIES} retries. Escalating.")
            self._escalate_failure(task, f"Max retries ({self.MAX_RETRIES}) exceeded.")

    # ---------- Shutdown ----------
    def shutdown(self):
        """Clean up resources and unsubscribe from events."""
        logger.info("[CoS] Shutting down.")
        try:
            self.event_bus.unsubscribe("TaskCompleted", self._on_task_completed)
            self.event_bus.unsubscribe("TaskFailed", self._on_task_failed)
        except Exception as e:
            logger.warning(f"[CoS] Error unsubscribing: {e}")
        self.active_tasks.clear()
        self.retries.clear()
