from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class CapabilityState(str, Enum):
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    REGISTERED = "registered"
    AVAILABLE = "available"
    EXECUTING = "executing"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class CapabilityHealth(str, Enum):
    AVAILABLE = "available"
    LOADING = "loading"
    HEALTHY = "healthy"
    BUSY = "busy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class CapabilityIdentity(BaseModel):
    id: str
    name: str
    description: str


class CapabilityClassification(BaseModel):
    category: str
    tags: List[str] = Field(default_factory=list)


class CapabilityDependency(BaseModel):
    capability: str
    version: str = ">=1.0.0"


class CapabilityRequirements(BaseModel):
    permissions: List[str] = Field(default_factory=list)
    dependencies: List[CapabilityDependency] = Field(default_factory=list)


class CapabilityExecution(BaseModel):
    entrypoint: str
    timeout: int = 30
    retry_policy: Dict[str, Any] = Field(default_factory=lambda: {"max_attempts": 3, "delay": 1})


class CapabilityResources(BaseModel):
    estimated_tokens: int = 0
    estimated_memory_mb: int = 128
    estimated_duration_sec: int = 5


class CapabilityLifecycle(BaseModel):
    version: str = "1.0.0"
    status: CapabilityState = CapabilityState.AVAILABLE


class CapabilityMetadata(BaseModel):
    author: str = "Jarvis Core Team"
    source: str = "built-in"
    documentation: str = ""


class CapabilityManifest(BaseModel):
    identity: CapabilityIdentity
    classification: CapabilityClassification
    requirements: CapabilityRequirements = Field(default_factory=CapabilityRequirements)
    execution: CapabilityExecution
    resources: CapabilityResources = Field(default_factory=CapabilityResources)
    lifecycle: CapabilityLifecycle = Field(default_factory=CapabilityLifecycle)
    metadata: CapabilityMetadata = Field(default_factory=CapabilityMetadata)
