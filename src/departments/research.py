from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

class ResearchWorker(BaseWorker):
    def execute(self, task: Task) -> Task:
        query = task.input_data.get("request", task.input_data.get("objective", ""))
        print(f"[ResearchWorker] Processing query: {query[:80]}...")
        
        if not self.engine:
            response = "I am operating in simulation mode. The full cognitive system is active."
        else:
            prompt = f"""You are JARVIS, a calm, professional, and highly capable AI assistant.
You are the Executive Mind of the Phoenix Intelligence Platform.

User Query: {query}

Respond naturally and helpfully:"""
            response = self.engine.generate(prompt)
        
        task.output_data = {"report": response}
        task.status = TaskStatus.COMPLETED
        task.progress = 1.0
        return task

class ResearchDepartment(BaseDepartment):
    def __init__(self, engine=None):
        super().__init__("Research")
        self.engine = engine

    def initialize(self, event_bus):
        super().initialize(event_bus)
        self.manager.register_worker(ResearchWorker("research-worker-01", self.engine))
