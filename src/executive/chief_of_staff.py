from typing import Dict, Any, List
from src.core.interfaces import IChiefOfStaff, IEventBus
from src.core.models import Task, TaskStatus, Event, Priority

class ChiefOfStaff(IChiefOfStaff):
    def __init__(self, event_bus: IEventBus):
        self.event_bus = event_bus
        self.active_tasks: Dict[str, Task] = {}
        self.event_bus.subscribe("TaskCompleted", self._on_task_completed)
        self.event_bus.subscribe("TaskFailed", self._on_task_failed)

    def schedule_task(self, task: Task) -> None:
        print(f"[CoS] Scheduling task {task.uuid} for department {task.target_department}")
        task.status = TaskStatus.ASSIGNED
        self.active_tasks[str(task.uuid)] = task

        # Publish event to notify department
        self.event_bus.publish(Event(
            event_type="DepartmentAssigned",
            source="ChiefOfStaff",
            payload={"task_id": str(task.uuid), "department": task.target_department}
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
