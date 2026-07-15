"""
Evolution Platform – Recommendation Prioritizer.
"""

import logging
from typing import List, Optional
from src.evolution.models import Recommendation

logger = logging.getLogger(__name__)


class Prioritizer:
    """
    Scores and ranks recommendations based on multiple dimensions.
    """

    def __init__(self):
        pass

    def compute_priority(self, rec: Recommendation) -> float:
        """
        Compute priority score.
        Formula: (Impact × Architecture × Confidence × Urgency) / Effort
        All factors normalized to 0-1.
        """
        # Normalize impact (0-1)
        impact = rec.impact if hasattr(rec, 'impact') else 0.5

        # Architecture importance (0-1)
        arch = rec.architectural_importance if hasattr(rec, 'architectural_importance') else 0.5

        # Confidence (0-1)
        confidence = rec.confidence if hasattr(rec, 'confidence') else 0.5

        # Urgency (0-1)
        urgency = rec.urgency if hasattr(rec, 'urgency') else 0.5

        # Effort: low=0.2, medium=0.5, high=0.8
        effort_map = {"low": 0.2, "medium": 0.5, "high": 0.8}
        effort = effort_map.get(rec.estimated_effort, 0.5)

        # Compute score; if effort is zero, set to high
        if effort == 0:
            effort = 0.1

        score = (impact * arch * confidence * urgency) / effort
        return min(1.0, score)

    def prioritize(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """
        Compute priority score for each and sort descending.
        """
        for rec in recommendations:
            rec.priority_score = self.compute_priority(rec)
        return sorted(recommendations, key=lambda r: r.priority_score or 0, reverse=True)
