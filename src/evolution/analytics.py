"""
Evolution Platform – Trend Analyzer.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from statistics import mean, stdev

from src.evolution.models import MetricsSnapshot
from src.evolution.repository import MetricsRepository

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """
    Analyzes historical metrics to detect trends.
    """

    def __init__(self, repository: MetricsRepository):
        self.repository = repository

    def analyze_trend(self, metric_key: str, window_days: int = 30) -> Dict[str, Any]:
        """
        Analyze trend for a specific metric.
        Returns: direction, rate of change, current value, average.
        """
        snapshots = self.repository.get_snapshots(limit=100)
        if not snapshots:
            return {"error": "No snapshots available"}

        # Filter by time window
        cutoff = datetime.now() - timedelta(days=window_days)
        recent = [s for s in snapshots if s.timestamp >= cutoff]

        if not recent:
            recent = snapshots[:10]  # fallback

        # Extract metric values
        values = []
        timestamps = []
        for s in recent:
            val = self._get_metric_value(s, metric_key)
            if val is not None:
                values.append(val)
                timestamps.append(s.timestamp)

        if len(values) < 2:
            return {
                "metric": metric_key,
                "direction": "insufficient_data",
                "current": values[-1] if values else None,
                "average": None,
                "rate_of_change": None,
            }

        # Compute trend
        current = values[-1]
        avg = mean(values)
        # Simple linear regression slope
        n = len(values)
        if n > 1:
            x = list(range(n))
            slope = (n * sum(x[i] * values[i] for i in range(n)) - sum(x) * sum(values)) / (n * sum(x[i]**2 for i in range(n)) - sum(x)**2)
        else:
            slope = 0

        direction = "stable"
        if slope > 0.5:
            direction = "improving"
        elif slope < -0.5:
            direction = "declining"

        return {
            "metric": metric_key,
            "direction": direction,
            "current": current,
            "average": avg,
            "rate_of_change": slope,
            "sample_size": len(values),
        }

    def _get_metric_value(self, snapshot: MetricsSnapshot, key: str) -> Optional[float]:
        """Extract a metric value from a snapshot."""
        mapping = {
            "architecture_score": snapshot.architecture_score,
            "quality_score": snapshot.quality_score,
            "security_score": snapshot.security_score,
            "performance_score": snapshot.performance_score,
            "documentation_score": snapshot.documentation_score,
            "test_coverage": snapshot.test_coverage,
            "technical_debt": snapshot.technical_debt,
            "recommendation_count": float(snapshot.recommendation_count),
            "violation_count": float(snapshot.violation_count),
            "complexity_avg": snapshot.complexity_avg,
            "duplication_estimate": snapshot.duplication_estimate,
            "maintainability_index": snapshot.maintainability_index,
        }
        return mapping.get(key)

    def generate_trend_report(self) -> Dict[str, Any]:
        """Generate a comprehensive trend report."""
        keys = [
            "architecture_score",
            "quality_score",
            "security_score",
            "performance_score",
            "documentation_score",
            "test_coverage",
            "technical_debt",
            "complexity_avg",
            "duplication_estimate",
            "maintainability_index",
        ]
        report = {}
        for key in keys:
            report[key] = self.analyze_trend(key, window_days=30)
        return report
