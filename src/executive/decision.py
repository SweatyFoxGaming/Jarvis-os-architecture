"""
Decision Making – commits to a course of action.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DecisionRecord(BaseModel):
    """
    Record of a decision made by the Executive.
    """
    uuid: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    goal_id: UUID
    chosen_plan: Dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0)
    risk_assessment: Dict[str, Any]
    alternatives_considered: List[Dict[str, Any]]
    rationale: str
    governance_approved: bool = True


class DecisionEngine:
    """
    Commits to a course of action after evaluating alternatives.
    """

    def __init__(self):
        self._decision_history: List[DecisionRecord] = []
        logger.info("[DecisionEngine] Initialized.")

    def make_decision(
        self,
        goal_id: UUID,
        candidates: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[DecisionRecord]:
        """
        Select the best candidate and record the decision.
        """
        if not candidates:
            logger.warning("[DecisionEngine] No candidates provided.")
            return None

        context = context or {}

        # Score candidates
        scored = []
        for candidate in candidates:
            score = self._score_candidate(candidate, context)
            scored.append((score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_candidate = scored[0]

        # If best score is too low, ask for more info or user confirmation
        if best_score < 0.5:
            logger.warning(f"[DecisionEngine] Best candidate has low confidence: {best_score}")
            # In a full implementation, we would escalate to the user.

        # Build alternatives list
        alternatives = []
        for score, alt in scored[1:3]:
            alternatives.append({
                "score": score,
                "plan": alt,
            })

        decision = DecisionRecord(
            goal_id=goal_id,
            chosen_plan=best_candidate,
            confidence=best_score,
            risk_assessment=self._assess_risk(best_candidate, context),
            alternatives_considered=alternatives,
            rationale=self._generate_rationale(best_candidate, scored),
        )

        self._decision_history.append(decision)
        logger.info(f"[DecisionEngine] Decision recorded: {decision.uuid} with confidence {best_score:.2f}")
        return decision

    def _score_candidate(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> float:
        """
        Score a candidate based on confidence, risk, cost, and alignment.
        Handles both numeric and string values.
        """
        score = 0.0

        # Confidence (if provided) - handle both float and string
        confidence = candidate.get("confidence", 0.5)
        if isinstance(confidence, str):
            try:
                confidence = float(confidence)
            except ValueError:
                confidence = 0.5
        elif not isinstance(confidence, (int, float)):
            confidence = 0.5
        score += confidence * 0.4

        # Risk (lower is better) - handle both float and string
        risk = candidate.get("risk", 0.5)
        if isinstance(risk, str):
            # Map string risk to float
            risk_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
            risk = risk_map.get(risk.lower(), 0.5)
        elif not isinstance(risk, (int, float)):
            risk = 0.5
        score += (1.0 - risk) * 0.3

        # Cost (lower is better) - handle both float and string
        cost = candidate.get("estimated_cost", 1.0)
        if isinstance(cost, str):
            try:
                cost = float(cost)
            except ValueError:
                cost = 1.0
        if not isinstance(cost, (int, float)):
            cost = 1.0
        # Normalize cost to 0-1 if it's not already
        if cost > 1.0:
            cost = min(cost, 10.0) / 10.0
        score += (1.0 - cost) * 0.2

        # Alignment with user preferences (simplified)
        score += 0.1

        return max(0.0, min(1.0, score))

    def _assess_risk(self, candidate: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the risk of a candidate.
        """
        risk = candidate.get("risk", "medium")
        if isinstance(risk, str):
            risk_level = risk
        elif isinstance(risk, (int, float)):
            risk_level = "low" if risk < 0.3 else "medium" if risk < 0.7 else "high"
        else:
            risk_level = "medium"

        return {
            "risk_level": risk_level,
            "risk_factors": candidate.get("risk_factors", []),
            "mitigations": candidate.get("mitigations", []),
        }

    def _generate_rationale(self, chosen: Dict[str, Any], scored: List[tuple]) -> str:
        """
        Generate a human-readable rationale for the decision.
        """
        rationale = f"Selected option with score {scored[0][0]:.2f} over {len(scored)-1} alternatives."
        if len(scored) > 1:
            rationale += f" Best alternative scored {scored[1][0]:.2f}."
        return rationale

    def get_decision_history(self, limit: int = 100) -> List[DecisionRecord]:
        return self._decision_history[-limit:]

    def get_decision(self, decision_id: UUID) -> Optional[DecisionRecord]:
        for decision in self._decision_history:
            if decision.uuid == decision_id:
                return decision
        return None
