"""
Core data models for the Cognitive Platform.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from src.core.models import Goal, Task, ExecutionState


class ExperienceSource(str, Enum):
    CONVERSATION = "conversation"
    CAPABILITY_RESULT = "capability_result"
    SYSTEM_EVENT = "system_event"
    SENSOR = "sensor"
    CALENDAR = "calendar"
    FILE = "file"
    API = "api"
    INTERNAL = "internal"


class ExperienceType(str, Enum):
    USER_INPUT = "user_input"
    JARVIS_RESPONSE = "jarvis_response"
    CAPABILITY_SUCCESS = "capability_success"
    CAPABILITY_FAILURE = "capability_failure"
    GOAL_CREATED = "goal_created"
    GOAL_COMPLETED = "goal_completed"
    TASK_SCHEDULED = "task_scheduled"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    FILE_CHANGED = "file_changed"
    CALENDAR_EVENT = "calendar_event"
    OTHER = "other"


class Experience(BaseModel):
    """
    Raw input to the cognitive system.
    """
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    source: ExperienceSource
    type: ExperienceType
    content: Any  # The raw data (string, dict, etc.)
    user_id: str = Field(default="default")
    goal_uuid: Optional[UUID] = None
    task_uuid: Optional[UUID] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"


class Belief(BaseModel):
    """
    A hypothesis about the world, with confidence and evidence.
    """
    uuid: UUID = Field(default_factory=uuid4)
    claim: str = Field(..., min_length=1, max_length=2000)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    evidence: List[UUID] = Field(default_factory=list)  # References to Experiences or Knowledge
    reinforcement_count: int = Field(default=0, ge=0)
    last_reinforced: datetime = Field(default_factory=datetime.now)
    source: Optional[ExperienceSource] = None
    source_uuid: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def reinforce(self) -> None:
        """Increase reinforcement count and update timestamp."""
        self.reinforcement_count += 1
        self.last_reinforced = datetime.now()
        self.updated_at = datetime.now()

    def update_confidence(self, new_confidence: float) -> None:
        """Update confidence and timestamp."""
        self.confidence = max(0.0, min(1.0, new_confidence))
        self.updated_at = datetime.now()

    class Config:
        extra = "forbid"


class KnowledgeType(str, Enum):
    FACT = "fact"
    PROCEDURE = "procedure"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"
    SKILL = "skill"
    PROJECT = "project"
    DECISION = "decision"
    PRINCIPLE = "principle"


class KnowledgeVerificationStatus(str, Enum):
    UNVERIFIED = "unverified"
    VERIFIED_BY_LLM = "verified_by_llm"
    VERIFIED_BY_HUMAN = "verified_by_human"
    REJECTED = "rejected"


class KnowledgeItem(BaseModel):
    """
    Verified, structured, and explainable intelligence.
    """
    uuid: UUID = Field(default_factory=uuid4)
    type: KnowledgeType
    content: Any  # The knowledge itself (string, dict, etc.)
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    evidence: List[UUID] = Field(default_factory=list)  # References to Experiences or Beliefs
    verification_status: KnowledgeVerificationStatus = KnowledgeVerificationStatus.UNVERIFIED
    source: Optional[ExperienceSource] = None
    source_uuid: Optional[UUID] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    usage_count: int = Field(default=0, ge=0)
    reinforcement_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def use(self) -> None:
        """Mark as used and increment usage count."""
        self.last_used = datetime.now()
        self.usage_count += 1

    def reinforce(self) -> None:
        """Increase reinforcement and update timestamp."""
        self.reinforcement_count += 1
        self.updated_at = datetime.now()

    def update_confidence(self, new_confidence: float) -> None:
        self.confidence = max(0.0, min(1.0, new_confidence))
        self.updated_at = datetime.now()

    class Config:
        extra = "forbid"


class WorkspaceContents(BaseModel):
    """
    The structured content of the Cognitive Workspace.
    """
    goal: Optional[Goal] = None
    task: Optional[Task] = None
    conversation: List[Dict[str, str]] = Field(default_factory=list)
    memories: List[KnowledgeItem] = Field(default_factory=list)
    capability_results: Dict[str, Any] = Field(default_factory=dict)
    planner_notes: List[str] = Field(default_factory=list)
    reasoning_notes: List[str] = Field(default_factory=list)
    budget: Optional[Dict[str, Any]] = None
    execution_context: Optional[Dict[str, Any]] = None
    insights: List[str] = Field(default_factory=list)
    hypotheses: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "forbid"


class CognitionTrace(BaseModel):
    """
    Explains why Jarvis made a decision.
    """
    uuid: UUID = Field(default_factory=uuid4)
    decision: str = Field(..., min_length=1, max_length=500)
    experience: Optional[Experience] = None
    attention_summary: str = ""
    understanding_summary: str = ""
    reflection_summary: str = ""
    beliefs: List[Belief] = Field(default_factory=list)
    knowledge: List[KnowledgeItem] = Field(default_factory=list)
    assistant_suggestions: List[str] = Field(default_factory=list)
    chosen_capability: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    class Config:
        extra = "forbid"

