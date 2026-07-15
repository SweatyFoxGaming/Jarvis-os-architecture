"""
Evolution Platform – Approval Engine.
"""

import logging
from typing import List, Optional
from datetime import datetime

from src.evolution.models import Recommendation, ApprovalState

logger = logging.getLogger(__name__)


class ApprovalEngine:
    """
    Manages the approval workflow for recommendations.
    """

    def __init__(self):
        self.history: List[dict] = []

    def propose(self, recommendation: Recommendation) -> Recommendation:
        """Move a recommendation from DRAFT to PROPOSED."""
        if recommendation.state != ApprovalState.DRAFT:
            raise ValueError(f"Cannot propose a recommendation in state: {recommendation.state}")
        recommendation.transition_to(ApprovalState.PROPOSED)
        self._log_action(recommendation, "proposed")
        return recommendation

    def review(self, recommendation: Recommendation) -> Recommendation:
        """Move a recommendation from PROPOSED to UNDER_REVIEW."""
        if recommendation.state != ApprovalState.PROPOSED:
            raise ValueError(f"Cannot review a recommendation in state: {recommendation.state}")
        recommendation.transition_to(ApprovalState.UNDER_REVIEW)
        self._log_action(recommendation, "under_review")
        return recommendation

    def approve(self, recommendation: Recommendation, approver: str = "human") -> Recommendation:
        """Approve a recommendation."""
        if recommendation.state not in [ApprovalState.PROPOSED, ApprovalState.UNDER_REVIEW]:
            raise ValueError(f"Cannot approve a recommendation in state: {recommendation.state}")
        recommendation.transition_to(ApprovalState.APPROVED)
        recommendation.approved_by = approver
        self._log_action(recommendation, f"approved by {approver}")
        return recommendation

    def reject(self, recommendation: Recommendation, reason: Optional[str] = None) -> Recommendation:
        """Reject a recommendation."""
        if recommendation.state not in [ApprovalState.PROPOSED, ApprovalState.UNDER_REVIEW]:
            raise ValueError(f"Cannot reject a recommendation in state: {recommendation.state}")
        recommendation.transition_to(ApprovalState.REJECTED)
        if reason:
            recommendation.metadata["rejection_reason"] = reason
        self._log_action(recommendation, f"rejected: {reason}" if reason else "rejected")
        return recommendation

    def mark_implemented(self, recommendation: Recommendation) -> Recommendation:
        """Mark a recommendation as implemented."""
        if recommendation.state != ApprovalState.APPROVED:
            raise ValueError(f"Cannot mark a recommendation as implemented in state: {recommendation.state}")
        recommendation.transition_to(ApprovalState.IMPLEMENTED)
        self._log_action(recommendation, "implemented")
        return recommendation

    def mark_verified(self, recommendation: Recommendation) -> Recommendation:
        """Mark a recommendation as verified."""
        if recommendation.state != ApprovalState.IMPLEMENTED:
            raise ValueError(f"Cannot verify a recommendation in state: {recommendation.state}")
        recommendation.transition_to(ApprovalState.VERIFIED)
        self._log_action(recommendation, "verified")
        return recommendation

    def archive(self, recommendation: Recommendation) -> Recommendation:
        """Archive a recommendation."""
        if recommendation.state not in [ApprovalState.VERIFIED, ApprovalState.REJECTED]:
            raise ValueError(f"Cannot archive a recommendation in state: {recommendation.state}")
        recommendation.transition_to(ApprovalState.ARCHIVED)
        self._log_action(recommendation, "archived")
        return recommendation

    def _log_action(self, recommendation: Recommendation, action: str) -> None:
        """Log an approval action."""
        self.history.append({
            "recommendation_id": str(recommendation.id),
            "action": action,
            "state": recommendation.state,
            "timestamp": datetime.now().isoformat(),
        })
        logger.info(f"[ApprovalEngine] {action} recommendation {recommendation.id}")
