from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

class ResearchWorker(BaseWorker):
    def execute(self, task: Task) -> Task:
        # V3 compatibility: look for 'objective' from Executive Mind
        query = task.input_data.get("objective") or task.input_data.get("request", "")
        print(f"[ResearchWorker] Performing deep research on: {query}")

        if not self.engine:
            task.output_data = {"report": f"Research simulation for: {query}"}
        else:
            prompt = f"System: Research specialist. Report on: {query}"
            task.output_data = {"report": self.engine.generate(prompt)}

        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        return task

class ResearchDepartment(BaseDepartment):
    def __init__(self, engine=None):
        super().__init__("Research")
        self.engine = engine

    def initialize(self, event_bus):
        super().initialize(event_bus)
        # Add workers
        self.manager.register_worker(ResearchWorker("research-worker-01", self.engine))
