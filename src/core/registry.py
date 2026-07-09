from typing import Dict, Any, List, Optional
from src.core.interfaces import IDepartment

class DepartmentRegistry:
    def __init__(self):
        self._departments: Dict[str, IDepartment] = {}

    def register(self, department: IDepartment) -> None:
        self._departments[department.name] = department
        print(f"[Registry] Registered department: {department.name}")

    def get_department(self, name: str) -> Optional[IDepartment]:
        return self._departments.get(name)

    def list_departments(self) -> List[str]:
        return list(self._departments.keys())

from src.core.models import Capability

class CapabilityRegistry:
    def __init__(self):
        # Maps capability names to (Capability, department_name)
        self._capabilities: Dict[str, tuple[Capability, str]] = {}

    def register(self, capability: Capability, department_name: str) -> None:
        self._capabilities[capability.name] = (capability, department_name)
        print(f"[Registry] Registered capability '{capability.name}' to '{department_name}'")

    def get_metadata(self, capability_name: str) -> Optional[Capability]:
        entry = self._capabilities.get(capability_name)
        return entry[0] if entry else None

    def find_department(self, capability_name: str) -> Optional[str]:
        entry = self._capabilities.get(capability_name)
        return entry[1] if entry else None

    def list_capabilities(self) -> List[str]:
        return list(self._capabilities.keys())
