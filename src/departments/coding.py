from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

class CodingWorker(BaseWorker):
    def execute(self, task: Task) -> Task:
        # V3 compatibility: look for 'objective' from Executive Mind
        request = task.input_data.get("objective") or task.input_data.get("request", "")
        print(f"[CodingWorker] Generating code for: {request}")

        if not self.engine:
            task.output_data = {"code": "print('hello')", "language": "python"}
        else:
            prompt = f"System: Coding specialist. Task: {request}"
            task.output_data = {"code": self.engine.generate(prompt)}

        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        return task

class CodingDepartment(BaseDepartment):
    def __init__(self, engine=None):
        super().__init__("Coding")
        self.engine = engine

    def initialize(self, event_bus):
        super().initialize(event_bus)
        # Add workers
        self.manager.register_worker(CodingWorker("coding-worker-01", self.engine))
