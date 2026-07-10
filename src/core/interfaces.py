"""
Interfaces (Protocols) for the Phoenix Intelligence Platform.

This module defines the core interfaces that various components must implement,
ensuring loose coupling and testability. All protocols are runtime-checkable
using typing.Protocol and @runtime_checkable.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from .models import Task, Event, Capability, Goal, ResourceBudget


# ---------- Event Bus ----------
@runtime_checkable
class IEventBus(Protocol):
    """
    Interface for the internal event bus.
    Used for decoupled communication between components.
    """

    def publish(self, event: Event) -> None:
        """
        Publish an event to the bus. All subscribers of that event_type will be notified.

        Args:
            event: The Event instance to publish.
        """
        ...

    def subscribe(self, event_type: str, callback: Any) -> None:
        """
        Register a callback for a given event type.

        Args:
            event_type: The event type string to listen for.
            callback: A callable that accepts an Event parameter.
        """
        ...

    def unsubscribe(self, event_type: str, callback: Any) -> None:
        """
        Remove a previously registered callback for an event type.

        Args:
            event_type: The event type string.
            callback: The callback that was previously registered.
        """
        ...


# ---------- Workers ----------
@runtime_checkable
class IWorker(Protocol):
    """
    Interface for a worker that processes a Task.
    Workers are typically owned by departments.
    """

    def execute(self, task: Task) -> Task:
        """
        Execute the given task and return the updated task with results.

        Args:
            task: The Task to execute.

        Returns:
            The updated Task with status, output_data, etc.
        """
        ...

    def get_profile(self) -> Dict[str, Any]:
        """
        Return a dictionary describing the worker's capabilities and metadata.

        Returns:
            Dict with keys like 'worker_id', 'supported_capabilities', etc.
        """
        ...


# ---------- Department Manager ----------
@runtime_checkable
class IDepartmentManager(Protocol):
    """
    Interface for a department's internal manager that handles workers.
    """

    def handle_task(self, task: Task) -> None:
        """
        Receive a task and assign it to an appropriate worker.

        Args:
            task: The Task to be handled.
        """
        ...

    def register_worker(self, worker: IWorker) -> None:
        """
        Register a worker with this manager.

        Args:
            worker: The IWorker instance to register.
        """
        ...


# ---------- Department ----------
@runtime_checkable
class IDepartment(Protocol):
    """
    Interface for a department that provides a set of capabilities.
    """

    @property
    def name(self) -> str:
        """The unique name of the department."""
        ...

    def initialize(self, event_bus: IEventBus) -> None:
        """
        Initialize the department, subscribe to events, and register workers.

        Args:
            event_bus: The IEventBus instance to subscribe to.
        """
        ...

    def process_task(self, task: Task) -> Task:
        """
        Process a task by routing it to the appropriate worker.
        Returns the updated task.

        Args:
            task: The Task to process.

        Returns:
            The Task after processing (status updated).
        """
        ...

    def set_secure_memory(self, secure_memory: Any) -> None:
        """
        Inject a secure memory store (optional).
        """
        ...

    def set_secure_runner(self, secure_runner: Any) -> None:
        """
        Inject a secure command runner (optional).
        """
        ...

    def shutdown(self) -> None:
        """
        Clean up resources, unsubscribe from events, etc.
        """
        ...


# ---------- Chief of Staff ----------
@runtime_checkable
class IChiefOfStaff(Protocol):
    """
    Interface for the Chief of Staff – responsible for task scheduling
    and monitoring operational execution.
    """

    def schedule_task(self, task: Task) -> None:
        """
        Schedule a task for execution by resolving its capability to a department.

        Args:
            task: The Task to schedule.
        """
        ...

    def monitor_progress(self) -> Dict[str, Any]:
        """
        Return a snapshot of current task progress.

        Returns:
            Dict with 'active_count' and list of active tasks.
        """
        ...


# ---------- CEO / Executive Mind ----------
@runtime_checkable
class ICEO(Protocol):
    """
    Interface for the CEO / Executive Mind.
    Responsible for strategic reasoning, intent analysis, and high-level decisions.
    """

    def process_request(self, user_input: str) -> str:
        """
        Process a user request and return a strategic response.

        Args:
            user_input: The raw user input string.

        Returns:
            The strategic response string.
        """
        ...

    def assess_vision(self) -> str:
        """
        Assess current goals and strategic direction.

        Returns:
            A summary of the current vision and status.
        """
        ...


# ---------- Model Manager ----------
@runtime_checkable
class IModelManager(Protocol):
    """
    Interface for managing LLM models – loading, selection, and retrieval.
    """

    def load_model(self, model_type: str, model_path: str, backend: str = "llama_cpp", **kwargs) -> Optional[Any]:
        """
        Load a model from disk or API.

        Args:
            model_type: Identifier for the model.
            model_path: Path to model file or API endpoint.
            backend: Backend to use ('llama_cpp', 'openai', 'mock').
            **kwargs: Additional backend-specific arguments.

        Returns:
            The loaded model instance, or None if failed.
        """
        ...

    def select_model_for_task(self, task: Task) -> Optional[str]:
        """
        Select the most appropriate model name for a given task.

        Args:
            task: The Task requiring a model.

        Returns:
            The model name to use, or None if none available.
        """
        ...

    def get_engine(self, model_name: Optional[str] = None) -> Optional[Any]:
        """
        Retrieve a model instance by name, or the default if not specified.

        Args:
            model_name: Optional name of the model.

        Returns:
            The model instance, or None if not found.
        """
        ...


# ---------- Hardware Manager ----------
@runtime_checkable
class IHardwareManager(Protocol):
    """
    Interface for hardware detection and optimization.
    """

    @staticmethod
    def detect_hardware() -> Dict[str, Any]:
        """
        Detect hardware capabilities (CPU cores, RAM, etc.).

        Returns:
            Dict with keys like 'cpu_count', 'total_ram_gb', etc.
        """
        ...

    @staticmethod
    def get_optimized_settings(hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Given hardware info, return optimized settings for the LLM.

        Returns:
            Dict with settings (threads, context_window, etc.).
        """
        ...


# ---------- Security Module ----------
@runtime_checkable
class ISecurityModule(Protocol):
    """
    Interface for the security module – validation, auditing, sanitization.
    """

    def validate_path(self, path: str) -> bool:
        """
        Validate that a path is within allowed whitelist.

        Returns:
            True if allowed, False otherwise.
        """
        ...

    def validate_command(self, command: str) -> bool:
        """
        Validate that a command is in allowed whitelist.

        Returns:
            True if allowed, False otherwise.
        """
        ...

    def audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an audit event.
        """
        ...

    def sanitize_input(self, input_string: str, max_length: int = 2048) -> str:
        """
        Sanitize user input to prevent injection attacks.
        """
        ...


# ---------- Digital Twin ----------
@runtime_checkable
class IDigitalTwin(Protocol):
    """
    Interface for the Digital Twin – maintains a representation of the system state.
    """

    def update_hardware(self, hardware_info: Dict[str, Any]) -> None:
        """
        Update hardware information.
        """
        ...

    def update_capabilities(self, capabilities: List[str]) -> None:
        """
        Update the list of available capabilities.
        """
        ...

    def get_summary(self) -> Dict[str, Any]:
        """
        Return a summary of the current system state.
        """
        ...


# ---------- Memory Store (Secure) ----------
@runtime_checkable
class IMemoryStore(Protocol):
    """
    Interface for secure memory storage (SQLite-based).
    """

    def insert(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        """
        Insert a new memory record.

        Returns:
            The new record ID.
        """
        ...

    def search_by_text(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for memories containing the search term.

        Returns:
            List of matching records.
        """
        ...

    def delete_by_id(self, record_id: int) -> bool:
        """
        Delete a record by ID.

        Returns:
            True if deleted, False if not found.
        """
        ...

    def close(self) -> None:
        """
        Close the database connection.
        """
        ...
