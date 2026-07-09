from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

class DigitalTwinState(BaseModel):
    user_identity: Dict[str, Any] = {}
    active_projects: List[str] = []
    current_goals: List[str] = []
    hardware_status: Dict[str, Any] = {}
    software_environment: Dict[str, Any] = {}
    available_capabilities: List[str] = []
    running_tasks_count: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)

class DigitalTwin:
    """
    A continuously evolving internal representation of reality.
    Allows JARVIS to reason about the world rather than repeatedly rediscover it.
    """
    def __init__(self):
        self.state = DigitalTwinState()

    def update_hardware(self, info: Dict[str, Any]):
        self.state.hardware_status = info
        self.state.last_updated = datetime.now()

    def update_capabilities(self, capabilities: List[str]):
        self.state.available_capabilities = capabilities
        self.state.last_updated = datetime.now()

    def add_project(self, project_name: str):
        if project_name not in self.state.active_projects:
            self.state.active_projects.append(project_name)
            self.state.last_updated = datetime.now()

    def set_user(self, user_info: Dict[str, Any]):
        self.state.user_identity = user_info
        self.state.last_updated = datetime.now()

    def get_summary(self) -> str:
        return (
            f"Environment: {self.state.software_environment.get('os', 'Unknown')}\n"
            f"Active Projects: {', '.join(self.state.active_projects) if self.state.active_projects else 'None'}\n"
            f"Capabilities: {len(self.state.available_capabilities)} active"
        )
