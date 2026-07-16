"""
Core Interfaces – contracts for core components.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from uuid import UUID


# ---------- Event Bus ----------
class IEventBus(ABC):
    @abstractmethod
    def publish(self, event: Any) -> None:
        pass

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable) -> None:
        pass

    @abstractmethod
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        pass


# ---------- Chief of Staff ----------
class IChiefOfStaff(ABC):
    @abstractmethod
    def schedule_task(self, task: Any) -> Any:
        pass

    @abstractmethod
    def monitor_progress(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass


# ---------- Executive CEO ----------
class ICEO(ABC):
    @abstractmethod
    def process_request(self, user_input: str, user_id: str, collect_trace: bool, force_agent: bool, system_prompt: Optional[str]) -> tuple:
        pass

    @abstractmethod
    def assess_vision(self) -> str:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass


# ---------- Department ----------
class IDepartment(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def initialize(self, event_bus: IEventBus) -> None:
        pass

    @abstractmethod
    def process_task(self, task: Any) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass


# ---------- Worker ----------
class IWorker(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def initialize(self) -> None:
        pass

    @abstractmethod
    def process(self, task: Any) -> Dict[str, Any]:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass


# ---------- Department Manager ----------
class IDepartmentManager(ABC):
    @abstractmethod
    def register_department(self, department: IDepartment) -> None:
        pass

    @abstractmethod
    def get_department(self, name: str) -> Optional[IDepartment]:
        pass

    @abstractmethod
    def list_departments(self) -> List[str]:
        pass


# ---------- Capability Registry ----------
class ICapabilityRegistry(ABC):
    @abstractmethod
    def register(self, capability: Any, department: str) -> None:
        pass

    @abstractmethod
    def list_capabilities(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_capability(self, name: str) -> Optional[Any]:
        pass

    @abstractmethod
    def find_department(self, capability_name: str) -> Optional[str]:
        pass
