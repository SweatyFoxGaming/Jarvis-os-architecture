from typing import Dict, Any, List
from src.core.interfaces import IChiefOfStaff, IEventBus
from src.core.models import Task, TaskStatus, Event, Priority

from src.core.registry import CapabilityRegistry, DepartmentRegistry

class ChiefOfStaff(IChiefOfStaff):
    """
    Chief of Staff focuses on execution.
    Transforms executive vision into coordinated action.
    No cognitive reasoning, purely operational.
    """
    def __init__(self, event_bus: IEventBus, cap_registry: CapabilityRegistry, dept_registry: DepartmentRegistry):
        self.event_bus = event_bus
        self.cap_registry = cap_registry
        self.dept_registry = dept_registry
        self.active_tasks: Dict[str, Task] = {}
        self.retries: Dict[str, int] = {}
        self.MAX_RETRIES = 3

        self.event_bus.subscribe("TaskCompleted", self._on_task_completed)
        self.event_bus.subscribe("TaskFailed", self._on_task_failed)

    def schedule_task(self, task: Task) -> None:
        # Resolve capability to department
        dept_name = self.cap_registry.find_department(task.target_capability)
        if not dept_name:
            print(f"[CoS] CRITICAL: Discovery failed for capability '{task.target_capability}'")
            self._escalate_failure(task, "Capability Registry Lookup Failed")
            return

        print(f"[CoS] Scheduling '{task.target_capability}' via '{dept_name}'")
        task.assigned_department_id = dept_name
        task.status = TaskStatus.ASSIGNED
        self.active_tasks[str(task.uuid)] = task

        self.event_bus.publish(Event(
            event_type="DepartmentAssigned",
            source="ChiefOfStaff",
            payload={"task_id": str(task.uuid), "department": dept_name}
        ))

    def _escalate_failure(self, task: Task, reason: str):
        print(f"[CoS] Escalating failure for task {task.uuid}: {reason}")
        task.status = TaskStatus.FAILED
        task.error_message = reason
        self.event_bus.publish(Event(
            event_type="OperationalEscalation",
            source="ChiefOfStaff",
            payload={"task_id": str(task.uuid), "reason": reason}
        ))

    def monitor_progress(self) -> Dict[str, Any]:
        return {
            "active_count": len(self.active_tasks),
            "tasks": [t.dict() for t in self.active_tasks.values()]
        }

    def _on_task_completed(self, event: Event):
        task_id = event.payload.get("task_id")
        if task_id in self.active_tasks:
            print(f"[CoS] Task {task_id} marked as COMPLETED")
            self.active_tasks[task_id].status = TaskStatus.COMPLETED
            # In a real system, we might move this to a history log
            del self.active_tasks[task_id]

    def _on_task_failed(self, event: Event):
        task_id = event.payload.get("task_id")
        if task_id in self.active_tasks:
            print(f"[CoS] Task {task_id} marked as FAILED")
            self.active_tasks[task_id].status = TaskStatus.FAILED
            # Handle recovery logic here
