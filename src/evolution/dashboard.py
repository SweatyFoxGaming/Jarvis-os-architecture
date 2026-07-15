"""
Evolution Platform – Engineering Dashboard.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.evolution.models import DashboardReport, MetricsSnapshot
from src.evolution.repository import MetricsRepository
from src.evolution.analytics import TrendAnalyzer
from src.evolution.forecasting import ForecastEngine
from src.evolution.prioritizer import Prioritizer

logger = logging.getLogger(__name__)


class Dashboard:
    """
    Generates an engineering health dashboard.
    """

    def __init__(self, repository: MetricsRepository):
        self.repository = repository
        self.trend_analyzer = TrendAnalyzer(repository)
        self.forecast_engine = ForecastEngine(repository)
        self.prioritizer = Prioritizer()

    def generate(self, recommendations: Optional[List] = None) -> DashboardReport:
        """Generate a comprehensive health report."""
        # Get latest snapshot
        snapshots = self.repository.get_snapshots(limit=1)
        if not snapshots:
            return DashboardReport(
                overall_health=0,
                architecture_health=0,
                quality_health=0,
                security_health=0,
                performance_health=0,
                documentation_health=0,
                test_health=0,
                technical_debt_level="unknown",
                architecture_drift="unknown",
                top_recommendations=[],
                forecast_summary={},
                goals_progress=[],
            )

        latest = snapshots[0]

        # Compute individual health scores (0-100)
        architecture = latest.architecture_score * 100
        quality = latest.quality_score * 100
        security = latest.security_score * 100
        performance = latest.performance_score * 100
        documentation = latest.documentation_score * 100
        test = latest.test_coverage * 100

        overall = (architecture + quality + security + performance + documentation + test) / 6

        # Debt level
        debt = latest.technical_debt
        if debt < 10:
            debt_level = "low"
        elif debt < 25:
            debt_level = "medium"
        else:
            debt_level = "high"

        # Architecture drift (simplified: based on violation count trend)
        trend = self.trend_analyzer.analyze_trend("violation_count", window_days=14)
        if trend.get("direction") == "declining":
            drift = "critical"
        elif trend.get("direction") == "improving":
            drift = "stable"
        else:
            drift = "stable"

        # Forecast summary
        forecasts = self.repository.get_forecasts(limit=1)
        forecast_summary = {}
        if forecasts:
            f = forecasts[0]
            forecast_summary = {
                "quality": f.predicted_quality,
                "debt": f.predicted_debt,
                "complexity": f.predicted_complexity,
                "horizon_days": f.horizon_days,
            }

        # Top recommendations (if provided)
        if recommendations:
            prioritized = self.prioritizer.prioritize(recommendations)
            top_recs = []
            for rec in prioritized[:5]:
                top_recs.append({
                    "id": str(rec.id),
                    "title": rec.title,
                    "priority_score": rec.priority_score or 0,
                    "effort": rec.estimated_effort,
                })
        else:
            top_recs = []

        # Goals progress (if any)
        goals = self.repository.get_goals(status="active")
        goals_progress = []
        for g in goals:
            progress = 0.0
            if g.current_value is not None and g.target_value > 0:
                progress = min(1.0, g.current_value / g.target_value)
            goals_progress.append({
                "id": str(g.id),
                "title": g.title,
                "target": g.target_value,
                "current": g.current_value,
                "progress": progress,
            })

        return DashboardReport(
            timestamp=datetime.now(),
            overall_health=overall,
            architecture_health=architecture,
            quality_health=quality,
            security_health=security,
            performance_health=performance,
            documentation_health=documentation,
            test_health=test,
            technical_debt_level=debt_level,
            architecture_drift=drift,
            top_recommendations=top_recs,
            forecast_summary=forecast_summary,
            goals_progress=goals_progress,
        )
