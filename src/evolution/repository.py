"""
Evolution Platform – Metrics Repository.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID

from src.evolution.models import MetricsSnapshot, Forecast, EngineeringGoal, GoalStatus

logger = logging.getLogger(__name__)


class MetricsRepository:
    """
    Stores and retrieves engineering metrics, forecasts, and goals.
    Uses SQLite for persistence (in-memory fallback).
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(os.getcwd(), "data", "evolution.db")
        self._init_db()
        self._snapshots: List[MetricsSnapshot] = []
        self._forecasts: List[Forecast] = []
        self._goals: List[EngineeringGoal] = []

    def _init_db(self):
        """Initialize SQLite database if it exists."""
        # For simplicity, we store in memory for now; we'll add SQLite later.
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    # ---------- Snapshots ----------
    def save_snapshot(self, snapshot: MetricsSnapshot) -> None:
        """Save a metrics snapshot."""
        self._snapshots.append(snapshot)
        logger.debug(f"[MetricsRepository] Saved snapshot {snapshot.id}")

    def get_snapshots(self, limit: int = 100) -> List[MetricsSnapshot]:
        """Return recent snapshots."""
        return sorted(self._snapshots, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_snapshot_before(self, before: datetime, limit: int = 1) -> List[MetricsSnapshot]:
        """Return snapshots before a given timestamp."""
        filtered = [s for s in self._snapshots if s.timestamp < before]
        return sorted(filtered, key=lambda x: x.timestamp, reverse=True)[:limit]

    # ---------- Forecasts ----------
    def save_forecast(self, forecast: Forecast) -> None:
        self._forecasts.append(forecast)

    def get_forecasts(self, limit: int = 10) -> List[Forecast]:
        return sorted(self._forecasts, key=lambda x: x.timestamp, reverse=True)[:limit]

    def get_latest_forecast(self) -> Optional[Forecast]:
        if not self._forecasts:
            return None
        return max(self._forecasts, key=lambda x: x.timestamp)

    # ---------- Goals ----------
    def save_goal(self, goal: EngineeringGoal) -> None:
        # Update if exists
        for i, g in enumerate(self._goals):
            if g.id == goal.id:
                self._goals[i] = goal
                return
        self._goals.append(goal)

    def get_goals(self, status: Optional[GoalStatus] = None) -> List[EngineeringGoal]:
        if status:
            return [g for g in self._goals if g.status == status]
        return self._goals

    def get_goal(self, goal_id: UUID) -> Optional[EngineeringGoal]:
        for g in self._goals:
            if g.id == goal_id:
                return g
        return None

    def delete_goal(self, goal_id: UUID) -> bool:
        for i, g in enumerate(self._goals):
            if g.id == goal_id:
                del self._goals[i]
                return True
        return False
