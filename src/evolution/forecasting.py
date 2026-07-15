"""
Evolution Platform – Forecast Engine.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from statistics import mean

from src.evolution.models import Forecast, MetricsSnapshot
from src.evolution.repository import MetricsRepository

logger = logging.getLogger(__name__)


class ForecastEngine:
    """
    Predicts future engineering metrics using linear regression.
    """

    def __init__(self, repository: MetricsRepository):
        self.repository = repository

    def forecast_metric(self, metric_key: str, horizon_days: int = 30) -> Optional[Forecast]:
        """Forecast a single metric."""
        snapshots = self.repository.get_snapshots(limit=100)
        if len(snapshots) < 3:
            logger.warning(f"Not enough snapshots to forecast {metric_key}")
            return None

        # Extract values
        values = []
        for s in snapshots:
            val = self._get_metric_value(s, metric_key)
            if val is not None:
                values.append(val)

        if len(values) < 3:
            return None

        # Simple linear regression
        n = len(values)
        x = list(range(n))
        sum_x = sum(x)
        sum_y = sum(values)
        sum_xy = sum(x[i] * values[i] for i in range(n))
        sum_x2 = sum(x[i]**2 for i in range(n))

        if (n * sum_x2 - sum_x**2) == 0:
            return None

        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x**2)
        intercept = (sum_y - slope * sum_x) / n

        # Predict future values
        future_x = n + horizon_days / 30  # assume 30-day intervals
        predicted_y = slope * future_x + intercept

        # Compute confidence based on R² (simplified)
        mean_y = sum_y / n
        ss_tot = sum((y - mean_y)**2 for y in values)
        ss_reg = sum((slope * x[i] + intercept - mean_y)**2 for i in range(n))
        r2 = ss_reg / ss_tot if ss_tot != 0 else 0
        confidence = max(0, min(1, r2))

        # Create forecast object
        forecast = Forecast(
            horizon_days=horizon_days,
            predicted_quality=predicted_y if metric_key == "quality_score" else 0.0,
            predicted_debt=predicted_y if metric_key == "technical_debt" else 0.0,
            predicted_complexity=predicted_y if metric_key == "complexity_avg" else 0.0,
            confidence=confidence,
            model="linear_regression",
            metadata={
                "metric": metric_key,
                "slope": slope,
                "intercept": intercept,
                "r2": r2,
                "data_points": n,
            }
        )
        self.repository.save_forecast(forecast)
        return forecast

    def forecast_all(self, horizon_days: int = 30) -> Dict[str, Any]:
        """Forecast all key metrics."""
        metrics = [
            "architecture_score",
            "quality_score",
            "security_score",
            "performance_score",
            "documentation_score",
            "test_coverage",
            "technical_debt",
            "complexity_avg",
            "duplication_estimate",
        ]
        results = {}
        for metric in metrics:
            f = self.forecast_metric(metric, horizon_days)
            if f:
                results[metric] = {
                    "predicted": getattr(f, "predicted_quality", None) or getattr(f, "predicted_debt", None) or getattr(f, "predicted_complexity", None),
                    "confidence": f.confidence,
                    "horizon_days": horizon_days,
                }
        return results

    def _get_metric_value(self, snapshot: MetricsSnapshot, key: str) -> Optional[float]:
        mapping = {
            "architecture_score": snapshot.architecture_score,
            "quality_score": snapshot.quality_score,
            "security_score": snapshot.security_score,
            "performance_score": snapshot.performance_score,
            "documentation_score": snapshot.documentation_score,
            "test_coverage": snapshot.test_coverage,
            "technical_debt": snapshot.technical_debt,
            "complexity_avg": snapshot.complexity_avg,
            "duplication_estimate": snapshot.duplication_estimate,
            "maintainability_index": snapshot.maintainability_index,
        }
        return mapping.get(key)
