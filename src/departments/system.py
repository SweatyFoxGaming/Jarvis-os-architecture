import datetime
import psutil
from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

class TimeWorker(BaseWorker):
    def execute(self, task: Task) -> Task:
        now = datetime.datetime.now()
        task.output_data = {
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "full_timestamp": now.isoformat()
        }
        task.status = TaskStatus.COMPLETED
        return task

class SystemInfoWorker(BaseWorker):
    def execute(self, task: Task) -> Task:
        task.output_data = {
            "cpu_percent": psutil.cpu_percent(),
            "ram_available_mb": psutil.virtual_memory().available // (1024*1024),
            "os": "Phoenix OS (AIOS)"
        }
        task.status = TaskStatus.COMPLETED
        return task

class SystemDepartment(BaseDepartment):
    def __init__(self):
        super().__init__("System")

    def initialize(self, event_bus):
        super().initialize(event_bus)
        self.manager.register_worker(TimeWorker("time-worker-01"))
        self.manager.register_worker(SystemInfoWorker("sysinfo-worker-01"))

    def process_task(self, task: Task):
        # Specific capability routing for System department
        if task.target_capability == "time_service":
            worker = self.manager.workers.get("time-worker-01")
        else:
            worker = self.manager.workers.get("sysinfo-worker-01")

        if worker:
            result = worker.execute(task)
            self.manager._notify_completion(result)
