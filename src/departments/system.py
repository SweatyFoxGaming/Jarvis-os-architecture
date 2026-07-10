import datetime
import logging
import traceback
from typing import Optional, Dict, Any

try:
    import psutil
except ImportError:
    psutil = None
    logging.warning("psutil not installed. System metrics will be simulated.")

# Secure components (injected for consistency, even if not heavily used)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.departments.base import BaseDepartment, BaseWorker
from src.core.models import Task, TaskStatus

# Logger for this module
logger = logging.getLogger(__name__)


class TimeWorker(BaseWorker):
    """
    Worker that returns the current system time and date.
    """

    def __init__(
        self,
        worker_id: str,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        super().__init__(worker_id)
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner
        logger.info(f"[{worker_id}] Initialized.")

    def _save_to_memory(self, metadata: Dict[str, Any]) -> None:
        """Store a timestamp snapshot in the secure database (if available)."""
        if self.secure_memory is None:
            return
        try:
            now = datetime.datetime.now()
            self.secure_memory.insert(
                text=f"SYSTEM_TIME: {now.isoformat()}",
                metadata={
                    "type": "system_snapshot",
                    "category": "time",
                    **metadata,
                },
            )
            logger.debug(f"[{self.worker_id}] Stored time snapshot in memory.")
        except Exception as e:
            logger.warning(f"[{self.worker_id}] Failed to store in memory: {e}")

    def execute(self, task: Task) -> Task:
        logger.info(f"[{self.worker_id}] Executing time query.")

        try:
            now = datetime.datetime.now()
            output = {
                "time": now.strftime("%H:%M:%S"),
                "date": now.strftime("%Y-%m-%d"),
                "full_timestamp": now.isoformat(),
                "timezone": str(datetime.datetime.now().astimezone().tzinfo),
            }

            # Store the snapshot in secure memory (for audit/history)
            self._save_to_memory(
                metadata={
                    "task_id": task.id,
                    "time": output["time"],
                    "date": output["date"],
                }
            )

            task.output_data = output
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[{self.worker_id}] Time retrieval failed: {e}\n{error_trace}")
            task.status = TaskStatus.FAILED
            task.output_data = {"error": str(e), "trace": error_trace}

        return task


class SystemInfoWorker(BaseWorker):
    """
    Worker that returns system resource metrics (CPU, RAM, etc.).
    Gracefully handles missing psutil or permission errors.
    """

    def __init__(
        self,
        worker_id: str,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        super().__init__(worker_id)
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner
        logger.info(f"[{worker_id}] Initialized. psutil available: {psutil is not None}")

    def _save_to_memory(self, metadata: Dict[str, Any]) -> None:
        """Store system metrics in the secure database (if available)."""
        if self.secure_memory is None:
            return
        try:
            self.secure_memory.insert(
                text=f"SYSTEM_METRICS: {metadata.get('cpu_percent', 0)}% CPU",
                metadata={
                    "type": "system_snapshot",
                    "category": "metrics",
                    **metadata,
                },
            )
            logger.debug(f"[{self.worker_id}] Stored system metrics in memory.")
        except Exception as e:
            logger.warning(f"[{self.worker_id}] Failed to store in memory: {e}")

    def _get_safe_metrics(self) -> Dict[str, Any]:
        """Safely retrieve system metrics. Returns defaults if psutil fails."""
        if psutil is None:
            return {
                "cpu_percent": 0.0,
                "ram_available_mb": 0,
                "ram_total_mb": 0,
                "ram_percent": 0.0,
                "error": "psutil not installed",
                "os": "Phoenix OS (AIOS)",
            }

        try:
            # Try to get CPU percentage with a timeout (1 second interval)
            cpu = psutil.cpu_percent(interval=1)
        except (psutil.AccessDenied, psutil.NoSuchProcess, AttributeError) as e:
            logger.warning(f"CPU metric failed: {e}")
            cpu = 0.0

        try:
            mem = psutil.virtual_memory()
            ram_available_mb = mem.available // (1024 * 1024)
            ram_total_mb = mem.total // (1024 * 1024)
            ram_percent = mem.percent
        except (psutil.AccessDenied, AttributeError) as e:
            logger.warning(f"RAM metric failed: {e}")
            ram_available_mb = 0
            ram_total_mb = 0
            ram_percent = 0.0

        return {
            "cpu_percent": cpu,
            "ram_available_mb": ram_available_mb,
            "ram_total_mb": ram_total_mb,
            "ram_percent": ram_percent,
            "os": "Phoenix OS (AIOS)",
        }

    def execute(self, task: Task) -> Task:
        logger.info(f"[{self.worker_id}] Executing system info query.")

        try:
            metrics = self._get_safe_metrics()

            # Store metrics in secure memory
            self._save_to_memory(
                metadata={
                    "task_id": task.id,
                    "cpu_percent": metrics.get("cpu_percent"),
                    "ram_available_mb": metrics.get("ram_available_mb"),
                    "ram_percent": metrics.get("ram_percent"),
                }
            )

            task.output_data = metrics
            task.status = TaskStatus.COMPLETED
            task.progress = 1.0

        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[{self.worker_id}] System info failed: {e}\n{error_trace}")
            task.status = TaskStatus.FAILED
            task.output_data = {"error": str(e), "trace": error_trace}

        return task


class SystemDepartment(BaseDepartment):
    """
    Department responsible for system-level tasks: time, resource monitoring, etc.
    Accepts secure components via setters for dependency injection.
    """

    def __init__(self, engine=None):  # engine parameter for API consistency, even if unused
        super().__init__("System")
        self.engine = engine
        self._secure_memory: Optional[SecureMemoryStore] = None
        self._secure_runner: Optional[SecureCommandRunner] = None
        self._workers = {}  # local cache for faster routing

    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        """Dependency injection for secure memory (called by main.py)."""
        self._secure_memory = secure_memory
        # Update existing workers if they are already registered
        for worker in self._workers.values():
            worker.secure_memory = secure_memory
        logger.info(f"[{self.name}] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        """Dependency injection for secure command runner (called by main.py)."""
        self._secure_runner = secure_runner
        for worker in self._workers.values():
            worker.secure_runner = secure_runner
        logger.info(f"[{self.name}] SecureCommandRunner attached.")

    def initialize(self, event_bus):
        super().initialize(event_bus)

        # Create workers with injected secure components
        time_worker = TimeWorker(
            worker_id="time-worker-01",
            secure_memory=self._secure_memory,
            secure_runner=self._secure_runner,
        )
        sysinfo_worker = SystemInfoWorker(
            worker_id="sysinfo-worker-01",
            secure_memory=self._secure_memory,
            secure_runner=self._secure_runner,
        )

        # Register workers with the manager
        self.manager.register_worker(time_worker)
        self.manager.register_worker(sysinfo_worker)

        # Keep local references for fast capability routing
        self._workers = {
            "time-worker-01": time_worker,
            "sysinfo-worker-01": sysinfo_worker,
        }

        logger.info(f"[{self.name}] Department initialized with {len(self._workers)} workers.")

    def process_task(self, task: Task) -> Task:
        """
        Override BaseDepartment.process_task to route based on target_capability.
        This is the secure, robust version with proper error handling.
        """
        logger.debug(f"[{self.name}] Processing task {task.id} with capability: {task.target_capability}")

        # Determine which worker to use
        worker_id = None
        if task.target_capability == "time_service":
            worker_id = "time-worker-01"
        elif task.target_capability == "system_info":
            worker_id = "sysinfo-worker-01"
        else:
            # Fallback: if no specific capability, use the sysinfo worker
            logger.warning(f"[{self.name}] Unknown capability '{task.target_capability}'. Falling back to sysinfo-worker-01.")
            worker_id = "sysinfo-worker-01"

        worker = self._workers.get(worker_id)

        if worker is None:
            logger.error(f"[{self.name}] No worker found for capability: {task.target_capability}")
            task.status = TaskStatus.FAILED
            task.output_data = {
                "error": f"No worker available for capability: {task.target_capability}"
            }
            # Notify manager (if it has a method) - but we won't call private methods.
            # The caller (v2_main) will check task.status directly.
            return task

        # Execute the worker inside a try/except for extra safety
        try:
            result = worker.execute(task)
            # Log completion
            if result.status == TaskStatus.COMPLETED:
                logger.info(f"[{self.name}] Task {task.id} completed by {worker_id}.")
            else:
                logger.error(f"[{self.name}] Task {task.id} failed in {worker_id}.")
            return result
        except Exception as e:
            # If worker.execute itself throws an unhandled exception (shouldn't happen now)
            error_trace = traceback.format_exc()
            logger.critical(f"[{self.name}] Unhandled exception in worker {worker_id}: {e}\n{error_trace}")
            task.status = TaskStatus.FAILED
            task.output_data = {
                "error": f"Unhandled exception: {str(e)}",
                "trace": error_trace,
            }
            return task

    def shutdown(self):
        """Clean up resources if needed."""
        logger.info(f"[{self.name}] Shutting down.")
        self._workers.clear()
