"""
Evolution Platform – Manager.
"""

import logging
from typing import List, Optional
from uuid import UUID

from src.evolution.models import AnalysisResult, Recommendation, MetricsSnapshot
from src.evolution.analyzer import ArchitectureAnalyzer
from src.evolution.quality import CodeQualityAnalyzer
from src.evolution.performance import PerformanceAnalyzer
from src.evolution.security import SecurityAnalyzer
from src.evolution.recommendations import RecommendationEngine
from src.evolution.approval import ApprovalEngine
from src.evolution.repository import MetricsRepository
from src.evolution.analytics import TrendAnalyzer
from src.evolution.forecasting import ForecastEngine
from src.evolution.prioritizer import Prioritizer
from src.evolution.dashboard import Dashboard
from src.evolution.goals import GoalManager

logger = logging.getLogger(__name__)


class EvolutionManager:
    """
    Coordinates analysis, recommendations, approval, and continuous evolution.
    """

    def __init__(self, root_path: str, event_bus=None):
        self.root_path = root_path
        self.event_bus = event_bus
        self.arch_analyzer = ArchitectureAnalyzer(root_path)
        self.quality_analyzer = CodeQualityAnalyzer(root_path)
        self.performance_analyzer = PerformanceAnalyzer(root_path)
        self.security_analyzer = SecurityAnalyzer(root_path)
        self.recommendation_engine = RecommendationEngine()
        self.approval_engine = ApprovalEngine()
        self.repository = MetricsRepository()
        self.trend_analyzer = TrendAnalyzer(self.repository)
        self.forecast_engine = ForecastEngine(self.repository)
        self.prioritizer = Prioritizer()
        self.dashboard = Dashboard(self.repository)
        self.goal_manager = GoalManager(self.repository)
        self.analyses: List[AnalysisResult] = []
        self.recommendations: List[Recommendation] = []

    def analyze_architecture(self) -> AnalysisResult:
        result = self.arch_analyzer.analyze()
        self.analyses.append(result)
        self._update_snapshot()
        if self.event_bus:
            self._publish_event("AnalysisCompleted", {
                "id": str(result.id),
                "type": result.type,
                "summary": result.summary,
            })
        logger.info(f"[Evolution] Architecture analysis complete: {result.summary}")
        return result

    def analyze_quality(self) -> AnalysisResult:
        result = self.quality_analyzer.analyze()
        self.analyses.append(result)
        self._update_snapshot()
        if self.event_bus:
            self._publish_event("AnalysisCompleted", {
                "id": str(result.id),
                "type": result.type,
                "summary": result.summary,
            })
        logger.info(f"[Evolution] Code quality analysis complete: {result.summary}")
        return result

    def analyze_performance(self) -> AnalysisResult:
        result = self.performance_analyzer.analyze()
        self.analyses.append(result)
        self._update_snapshot()
        if self.event_bus:
            self._publish_event("AnalysisCompleted", {
                "id": str(result.id),
                "type": result.type,
                "summary": result.summary,
            })
        logger.info(f"[Evolution] Performance analysis complete: {result.summary}")
        return result

    def analyze_security(self) -> AnalysisResult:
        result = self.security_analyzer.analyze()
        self.analyses.append(result)
        self._update_snapshot()
        if self.event_bus:
            self._publish_event("AnalysisCompleted", {
                "id": str(result.id),
                "type": result.type,
                "summary": result.summary,
            })
        logger.info(f"[Evolution] Security analysis complete: {result.summary}")
        return result

    def _update_snapshot(self):
        """Create a metrics snapshot from the latest analyses."""
        # Aggregate scores from the last analysis of each type
        scores = {
            "architecture": 0.8,  # Placeholder
            "quality": 0.7,
            "security": 0.9,
            "performance": 0.85,
            "documentation": 0.6,
            "test": 0.5,
        }
        # Use the latest quality analysis for detailed metrics
        quality_analysis = None
        for a in reversed(self.analyses):
            if a.type == "code_quality":
                quality_analysis = a
                break

        if quality_analysis:
            metrics = quality_analysis.metrics
            scores["quality"] = max(0, min(1, 1 - (metrics.get("avg_complexity", 0) / 20)))
            scores["documentation"] = metrics.get("doc_ratio", 0.5)
            scores["test"] = metrics.get("doc_ratio", 0.5)  # placeholder
            scores["performance"] = max(0, min(1, 1 - (metrics.get("avg_complexity", 0) / 30)))
            scores["security"] = 0.9  # placeholder

        # Build snapshot
        snapshot = MetricsSnapshot(
            architecture_score=scores["architecture"],
            quality_score=scores["quality"],
            security_score=scores["security"],
            performance_score=scores["performance"],
            documentation_score=scores["documentation"],
            test_coverage=scores["test"],
            technical_debt=20.0,  # placeholder
            recommendation_count=len(self.recommendations),
            violation_count=sum(len(a.violations) for a in self.analyses),
            complexity_avg=quality_analysis.metrics.get("avg_complexity", 0) if quality_analysis else 0,
            duplication_estimate=quality_analysis.metrics.get("duplication_estimate", 0) if quality_analysis else 0,
            maintainability_index=quality_analysis.metrics.get("maintainability_index", 50) if quality_analysis else 50,
        )
        self.repository.save_snapshot(snapshot)

    def generate_recommendations(self, analysis_id: Optional[str] = None) -> List[Recommendation]:
        recs = []
        if analysis_id:
            analysis = next((a for a in self.analyses if str(a.id) == analysis_id), None)
            if analysis:
                recs = self.recommendation_engine.generate(analysis)
        else:
            for analysis in self.analyses:
                recs.extend(self.recommendation_engine.generate(analysis))

        for rec in recs:
            self.recommendations.append(rec)
            if self.event_bus:
                self._publish_event("RecommendationCreated", {
                    "id": str(rec.id),
                    "title": rec.title,
                    "state": rec.state,
                })

        logger.info(f"[Evolution] Generated {len(recs)} recommendations")
        return recs

    def get_analyses(self) -> List[AnalysisResult]:
        return self.analyses

    def get_recommendations(self, state: Optional[str] = None) -> List[Recommendation]:
        if state:
            return [r for r in self.recommendations if r.state == state]
        return self.recommendations

    def get_recommendation(self, rec_id: str) -> Optional[Recommendation]:
        for r in self.recommendations:
            if str(r.id) == rec_id:
                return r
        return None

    def propose(self, rec_id: str) -> Optional[Recommendation]:
        rec = self.get_recommendation(rec_id)
        if not rec:
            return None
        return self.approval_engine.propose(rec)

    def approve(self, rec_id: str) -> Optional[Recommendation]:
        rec = self.get_recommendation(rec_id)
        if not rec:
            return None
        return self.approval_engine.approve(rec)

    def reject(self, rec_id: str, reason: Optional[str] = None) -> Optional[Recommendation]:
        rec = self.get_recommendation(rec_id)
        if not rec:
            return None
        return self.approval_engine.reject(rec, reason)

    def get_dependency_graph(self) -> Optional[dict]:
        for analysis in reversed(self.analyses):
            if analysis.type == "architecture" and analysis.dependency_graph:
                return analysis.dependency_graph
        return None

    def get_dashboard(self, recommendations: Optional[List] = None) -> dict:
        if recommendations is None:
            recommendations = self.recommendations
        report = self.dashboard.generate(recommendations)
        return report.model_dump(mode='json')

    def get_trend_report(self) -> dict:
        return self.trend_analyzer.generate_trend_report()

    def get_forecast(self, horizon_days: int = 30) -> dict:
        return self.forecast_engine.forecast_all(horizon_days)

    def prioritize_recommendations(self) -> List[Recommendation]:
        return self.prioritizer.prioritize(self.recommendations)

    def get_goals(self, status: Optional[str] = None) -> List[dict]:
        from src.evolution.models import GoalStatus
        status_enum = GoalStatus(status) if status else None
        goals = self.goal_manager.list_goals(status_enum)
        return [g.model_dump(mode='json') for g in goals]

    def create_goal(self, title: str, description: str, target_metric: str, target_value: float) -> dict:
        goal = self.goal_manager.create_goal(title, description, target_metric, target_value)
        return goal.model_dump(mode='json')

    def update_goal_progress(self, goal_id: str, current_value: float) -> Optional[dict]:
        goal = self.goal_manager.update_progress(UUID(goal_id), current_value)
        if goal:
            return goal.model_dump(mode='json')
        return None

    def _publish_event(self, event_type: str, payload: dict) -> None:
        if self.event_bus:
            try:
                from src.core.models import Event
                event = Event(event_type=event_type, source="EvolutionManager", payload=payload)
                self.event_bus.publish(event)
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type}: {e}")
