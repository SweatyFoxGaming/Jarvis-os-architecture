import datetime
import logging
import traceback
from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)


class TimeWorker(BaseWorker):
    def __init__(self, worker_id: str, secure_memory=None, secure_runner=None):
        super().__init__(worker_id)
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner
        logger.info(f"[{worker_id}] Initialized.")

    def execute(self, task: Task) -> Task:
        try:
            now = datetime.datetime.now()
            task.output_data = {
                "time": now.strftime("%H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "full_timestamp": now.isoformat()
            }
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            logger.error(f"[TimeWorker] Error: {e}")
            task.status = TaskStatus.FAILED
            task.output_data = {"error": str(e)}
        return task


class SystemInfoWorker(BaseWorker):
    def __init__(self, worker_id: str, secure_memory=None, secure_runner=None):
        super().__init__(worker_id)
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner
        logger.info(f"[{worker_id}] Initialized. psutil available: {psutil is not None}")

    def execute(self, task: Task) -> Task:
        try:
            if psutil is None:
                task.output_data = {
                    "cpu_percent": 0,
                    "ram_available_mb": 0,
                    "os": "Unknown"
                }
            else:
                task.output_data = {
                    "cpu_percent": psutil.cpu_percent(),
                    "ram_available_mb": psutil.virtual_memory().available // (1024*1024),
                    "os": "Phoenix OS (AIOS)"
                }
            task.status = TaskStatus.COMPLETED
        except Exception as e:
            logger.error(f"[SystemInfoWorker] Error: {e}")
            task.status = TaskStatus.FAILED
            task.output_data = {"error": str(e)}
        return task


class SystemDepartment(BaseDepartment):
    def __init__(self, secure_memory=None, secure_runner=None):
        super().__init__("System")
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner

    def initialize(self, event_bus):
        super().initialize(event_bus)
        time_worker = TimeWorker(
            "time-worker-01",
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )
        sysinfo_worker = SystemInfoWorker(
            "sysinfo-worker-01",
            secure_memory=self.secure_memory,
            secure_runner=self.secure_runner,
        )
        self.manager.register_worker(time_worker)
        self.manager.register_worker(sysinfo_worker)
        logger.info("[System] Department initialized with 2 workers.")

    def process_task(self, task: Task):
        if task.target_capability == "time_service":
            worker = self.manager.workers.get("time-worker-01")
        else:
            worker = self.manager.workers.get("sysinfo-worker-01")
        if worker:
            result = worker.execute(task)
            self.manager._notify_completion(result)

