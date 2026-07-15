"""
Ecosystem Platform – Core models.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4


class PluginState(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    INSTALLED = "installed"
    LOADED = "loaded"
    ACTIVE = "active"
    UPDATING = "updating"
    INACTIVE = "inactive"
    REMOVED = "removed"
    FAILED = "failed"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class PluginCapability(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    returns: Dict[str, Any] = Field(default_factory=dict)


class PluginPermission(str, Enum):
    FILESYSTEM = "filesystem"
    NETWORK = "network"
    TERMINAL = "terminal"
    CLIPBOARD = "clipboard"
    ENVIRONMENT = "environment"
    CALENDAR = "calendar"
    EMAIL = "email"
    BROWSER = "browser"
    NOTIFICATIONS = "notifications"
    DEVICES = "devices"


class PluginManifest(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    version: str
    description: str
    author: str
    homepage: Optional[str] = None
    license: Optional[str] = None
    jarvis_version: str = "1.0.0"
    dependencies: List[str] = Field(default_factory=list)
    permissions: List[PluginPermission] = Field(default_factory=list)
    capabilities: List[PluginCapability] = Field(default_factory=list)
    providers: List[str] = Field(default_factory=list)
    state: PluginState = PluginState.DISCOVERED
    health: HealthStatus = HealthStatus.UNKNOWN
    installed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    source: str = "local"
    digital_signature: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PluginPackage(BaseModel):
    """Remote plugin package from marketplace."""
    id: str
    name: str
    version: str
    description: str
    author: str
    repository: str
    download_url: str
    dependencies: List[str] = Field(default_factory=list)
    capabilities: List[Dict[str, Any]] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    rating: float = 0.0
    downloads: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
