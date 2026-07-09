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

class CapabilityRegistry:
    def __init__(self):
        # Maps capability names to department names
        self._capabilities: Dict[str, str] = {}

    def register_capability(self, capability: str, department_name: str) -> None:
        self._capabilities[capability] = department_name
        print(f"[Registry] Registered capability '{capability}' to '{department_name}'")

    def find_department(self, capability: str) -> Optional[str]:
        return self._capabilities.get(capability)
