"""
Evolution Platform – Core models.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID, uuid4


class AnalysisType(str, Enum):
    ARCHITECTURE = "architecture"
    CODE_QUALITY = "code_quality"
    DEPENDENCIES = "dependencies"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    TESTS = "tests"


class RecommendationType(str, Enum):
    REFACTOR = "refactor"
    ARCHITECTURAL_CHANGE = "architectural_change"
    DEPENDENCY_UPGRADE = "dependency_upgrade"
    DOCUMENTATION = "documentation"
    PERFORMANCE = "performance"
    SECURITY = "security"
    TEST_IMPROVEMENT = "test_improvement"
    GOVERNANCE_UPDATE = "governance_update"
    DUPLICATION = "duplication"


class ApprovalState(str, Enum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    ARCHIVED = "archived"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    ARCHIVED = "archived"


class EngineeringGoal(BaseModel):
    """Long-term engineering objective."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    target_metric: str  # e.g., "code_quality", "test_coverage"
    target_value: float
    current_value: Optional[float] = None
    status: GoalStatus = GoalStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricsSnapshot(BaseModel):
    """A point-in-time snapshot of engineering metrics."""
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    architecture_score: float = 0.0
    quality_score: float = 0.0
    security_score: float = 0.0
    performance_score: float = 0.0
    documentation_score: float = 0.0
    test_coverage: float = 0.0
    technical_debt: float = 0.0  # percentage
    recommendation_count: int = 0
    violation_count: int = 0
    complexity_avg: float = 0.0
    duplication_estimate: float = 0.0
    maintainability_index: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Forecast(BaseModel):
    """Predicted future metrics."""
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    horizon_days: int
    predicted_quality: float
    predicted_debt: float
    predicted_complexity: float
    confidence: float = 0.5
    model: str = "linear_regression"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DashboardReport(BaseModel):
    """Comprehensive engineering health report."""
    timestamp: datetime = Field(default_factory=datetime.now)
    overall_health: float = 0.0
    architecture_health: float = 0.0
    quality_health: float = 0.0
    security_health: float = 0.0
    performance_health: float = 0.0
    documentation_health: float = 0.0
    test_health: float = 0.0
    technical_debt_level: str = "low"  # low, medium, high
    architecture_drift: str = "stable"  # stable, drifting, critical
    top_recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    forecast_summary: Dict[str, Any] = Field(default_factory=dict)
    goals_progress: List[Dict[str, Any]] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    """Result of a single analysis run."""
    id: UUID = Field(default_factory=uuid4)
    type: AnalysisType
    timestamp: datetime = Field(default_factory=datetime.now)
    summary: str
    details: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations_count: int = 0
    circular_dependencies: List[List[str]] = Field(default_factory=list)
    dependency_graph: Optional[Dict[str, Any]] = None

    class Config:
        extra = "forbid"


class Recommendation(BaseModel):
    """An actionable engineering recommendation."""
    id: UUID = Field(default_factory=uuid4)
    analysis_id: UUID
    type: RecommendationType
    title: str
    description: str
    motivation: str
    evidence: str
    expected_benefit: str
    expected_risk: str
    estimated_effort: str
    affected_modules: List[str] = Field(default_factory=list)
    governance_references: List[str] = Field(default_factory=list)
    state: ApprovalState = ApprovalState.DRAFT
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    approved_by: Optional[str] = None
    implemented_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    # Priority scoring fields
    impact: float = 0.5
    architectural_importance: float = 0.5
    confidence: float = 0.5
    urgency: float = 0.5
    priority_score: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "forbid"

    def transition_to(self, new_state: ApprovalState) -> None:
        self.state = new_state
        self.updated_at = datetime.now()
        if new_state == ApprovalState.APPROVED:
            self.approved_by = "human"
        elif new_state == ApprovalState.IMPLEMENTED:
            self.implemented_at = datetime.now()
        elif new_state == ApprovalState.VERIFIED:
            self.verified_at = datetime.now()
