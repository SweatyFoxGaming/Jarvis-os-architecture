from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

class CodingWorker(BaseWorker):
    def execute(self, task: Task) -> Task:
        query = task.input_data.get("request", task.input_data.get("objective", ""))
        print(f"[CodingWorker] Processing coding task: {query[:80]}...")
        
        if not self.engine:
            response = "Code generation is ready. Provide a specific coding request."
        else:
            prompt = f"""You are JARVIS Coding Specialist.
You are an expert programmer with deep knowledge of Python, Rust, and system architecture.

Task: {query}

Provide clean, well-commented code or analysis:"""
            response = self.engine.generate(prompt)
        
        task.output_data = {"code": response, "language": "python"}
        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        return task

class CodingDepartment(BaseDepartment):
    def __init__(self, engine=None):
        super().__init__("Coding")
        self.engine = engine

    def initialize(self, event_bus):
        super().initialize(event_bus)
        self.manager.register_worker(CodingWorker("coding-worker-01", self.engine))
