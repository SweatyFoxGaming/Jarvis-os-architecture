from abc import ABC, abstractmethod
from typing import Dict, Any, List
from src.core.interfaces import IDepartment, IEventBus, IWorker, IDepartmentManager
from src.core.models import Task, Event, TaskStatus

class BaseWorker(IWorker, ABC):
    def __init__(self, worker_id: str, engine=None):
        self.worker_id = worker_id
        self.engine = engine

    @abstractmethod
    def execute(self, task: Task) -> Task:
        pass

    def get_profile(self) -> Dict[str, Any]:
        return {"id": self.worker_id, "type": self.__class__.__name__}

class BaseDepartmentManager(IDepartmentManager):
    def __init__(self, department_name: str, event_bus: IEventBus):
        self.department_name = department_name
        self.event_bus = event_bus
        self.workers: Dict[str, IWorker] = {}
        self.active_tasks: Dict[str, Task] = {}

    def register_worker(self, worker: IWorker) -> None:
        profile = worker.get_profile()
        self.workers[profile["id"]] = worker
        print(f"[{self.department_name}] Registered worker: {profile['id']}")

    def handle_task(self, task: Task) -> None:
        print(f"[{self.department_name}] Manager handling task {task.uuid} (Requirement: {task.target_capability})")
        task.status = TaskStatus.IN_PROGRESS
        self.active_tasks[str(task.uuid)] = task

        # Simple worker selection (first available)
        if not self.workers:
            task.status = TaskStatus.FAILED
            task.error_message = "No workers available"
            self._notify_failure(task)
            return

        worker = list(self.workers.values())[0]
        task.assigned_worker_id = worker.get_profile()["id"]

        # Execute (In V2 this might be async/threaded)
        try:
            result_task = worker.execute(task)
            if result_task.status == TaskStatus.COMPLETED:
                self._notify_completion(result_task)
            else:
                self._notify_failure(result_task)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            self._notify_failure(task)

    def _notify_completion(self, task: Task):
        self.event_bus.publish(Event(
            event_type="TaskCompleted",
            source=self.department_name,
            payload={"task_id": str(task.uuid), "output": task.output_data}
        ))

    def _notify_failure(self, task: Task):
        self.event_bus.publish(Event(
            event_type="TaskFailed",
            source=self.department_name,
            payload={"task_id": str(task.uuid), "error": task.error_message}
        ))

class BaseDepartment(IDepartment):
    def __init__(self, name: str):
        self._name = name
        self.manager: Optional[IDepartmentManager] = None

    @property
    def name(self) -> str:
        return self._name

    def initialize(self, event_bus: IEventBus) -> None:
        self.manager = BaseDepartmentManager(self._name, event_bus)
        # Subscribe to department assignment events
        event_bus.subscribe("DepartmentAssigned", self._on_department_assigned)

    def _on_department_assigned(self, event: Event):
        if event.payload.get("department") == self._name:
            # Reconstruct task (in real system, fetch from a TaskRepository)
            # For MVP, we simulate having the task object or passing it in payload
            pass

    def process_task(self, task: Task):
        if self.manager:
            self.manager.handle_task(task)
