"""
Evolution Platform – Entry point.
"""

from src.evolution.manager import EvolutionManager
from src.evolution.models import (
    AnalysisType,
    RecommendationType,
    ApprovalState,
    AnalysisResult,
    Recommendation,
    MetricsSnapshot,
    Forecast,
    EngineeringGoal,
    GoalStatus,
    DashboardReport,
)

__all__ = [
    "EvolutionManager",
    "AnalysisType",
    "RecommendationType",
    "ApprovalState",
    "AnalysisResult",
    "Recommendation",
    "MetricsSnapshot",
    "Forecast",
    "EngineeringGoal",
    "GoalStatus",
    "DashboardReport",
]
