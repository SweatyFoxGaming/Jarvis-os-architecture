from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class Domain(str, Enum):
    FILESYSTEM = "filesystem"
    WORKSPACE = "workspace"
    PROJECTS = "projects"
    BROWSER = "browser"
    CALENDAR = "calendar"
    EMAIL = "email"
    COMMUNICATION = "communication"
    NETWORK = "network"
    HARDWARE = "hardware"
    SERVICES = "services"
    TERMINAL = "terminal"
    NOTIFICATIONS = "notifications"
    IDENTITY = "identity"


class ProviderHealth(str, Enum):
    LOADING = "loading"
    AVAILABLE = "available"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class EnvironmentProviderCapability(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)


class ProviderMetadata(BaseModel):
    name: str
    domain: Domain
    version: str = "1.0.0"
    author: str = "Jarvis Core Team"
    description: str = ""
    capabilities: List[EnvironmentProviderCapability] = Field(default_factory=list)
