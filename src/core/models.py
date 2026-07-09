from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Priority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    URGENT = 3

class ResourceBudget(BaseModel):
    cpu_limit: float = 1.0  # Percentage or units
    ram_limit_mb: int = 256
    token_limit: int = 2048
    time_limit_sec: int = 60

class RiskLevel(Enum):
    NEGLIGIBLE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Goal(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    parent_goal: Optional[UUID] = None
    priority: Priority = Priority.MEDIUM
    deadline: Optional[datetime] = None
    alignment: str = "Strategic" # Vision alignment

class ExecutiveDecision(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    intent: str
    context: str
    goals: List[UUID] = []
    selected_capabilities: List[str] = []
    reasoning_summary: str
    confidence: float
    expected_outcome: str
    estimated_cost: float
    estimated_time_sec: int
    risks: List[Dict[str, Any]] = []
    alternatives: List[str] = []
    approved: bool = False

class Capability(BaseModel):
    name: str
    purpose: str
    inputs: Dict[str, str] = {}
    outputs: Dict[str, str] = {}
    dependencies: List[str] = []
    required_permissions: List[str] = []
    estimated_cost: float = 0.0
    estimated_time_sec: int = 0
    confidence: float = 1.0
    required_resources: Dict[str, Any] = {}

class Task(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    creator_id: str
    target_capability: str
    assigned_department_id: Optional[str] = None
    assigned_worker_id: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    dependencies: List[UUID] = []
    deadline: Optional[datetime] = None
    history: List[Dict[str, Any]] = []
    confidence: float = 0.0
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    input_data: Dict[str, Any] = {}
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class Event(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    event_type: str
    source: str
    payload: Dict[str, Any] = {}
    importance: float = 0.5

class MemoryRecord(BaseModel):
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str
    content: Any
    confidence: float = 1.0
    importance: float = 0.5
    verification_status: str = "unverified"
    embedding: Optional[List[float]] = None
    tags: List[str] = []
    usage_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.now)
