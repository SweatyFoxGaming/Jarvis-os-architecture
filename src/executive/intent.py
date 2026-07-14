"""
Intent Interpretation – determine what the user is actually trying to achieve.
"""

import logging
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from src.llm_engine import LLMEngine

logger = logging.getLogger(__name__)


class StructuredIntent(BaseModel):
    """
    The output of Intent Interpretation.
    """
    outcome: str = Field(..., description="The desired outcome")
    entities: Dict[str, str] = Field(default_factory=dict, description="Relevant entities")
    urgency: str = Field(default="medium", description="low, medium, high, critical")
    importance: str = Field(default="medium", description="low, medium, high, critical")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="User constraints")
    implied_requirements: List[str] = Field(default_factory=list, description="Implied needs")
    assumptions: List[str] = Field(default_factory=list, description="Assumptions made")
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence in interpretation")


class IntentInterpreter:
    """
    Interprets user input to produce a Structured Intent.
    """

    def __init__(self, engine: Optional[LLMEngine] = None):
        self.engine = engine
        logger.info("[IntentInterpreter] Initialized.")

    def set_engine(self, engine: LLMEngine) -> None:
        self.engine = engine
        logger.info("[IntentInterpreter] LLMEngine attached.")

    def interpret(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> StructuredIntent:
        """
        Interpret the user input and return a Structured Intent.
        """
        if self.engine is None:
            logger.warning("[IntentInterpreter] No LLM engine available. Using fallback.")
            return self._fallback_interpret(user_input, context)

        prompt = self._build_prompt(user_input, context)
        try:
            response = self.engine.generate(prompt, max_tokens=512, temperature=0.3)
            return self._parse_response(response, user_input)
        except Exception as e:
            logger.error(f"[IntentInterpreter] Interpretation failed: {e}")
            return self._fallback_interpret(user_input, context)

    def _build_prompt(self, user_input: str, context: Optional[Dict[str, Any]]) -> str:
        context_text = ""
        if context:
            context_text = f"Context: {context}\n"
        return f"""
You are Jarvis, interpreting user intent.

{context_text}
User input: "{user_input}"

Extract the following:
- Desired outcome: What does the user want to achieve?
- Entities: Who, what, where?
- Urgency: low, medium, high, critical
- Importance: low, medium, high, critical
- Constraints: Any restrictions or requirements?
- Implied requirements: What is implied but not stated?
- Assumptions: What are you assuming?

Return as JSON with keys: outcome, entities, urgency, importance, constraints, implied_requirements, assumptions, confidence.
"""

    def _parse_response(self, response: str, user_input: str) -> StructuredIntent:
        import json
        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)
                return StructuredIntent(
                    outcome=data.get("outcome", user_input),
                    entities=data.get("entities", {}),
                    urgency=data.get("urgency", "medium"),
                    importance=data.get("importance", "medium"),
                    constraints=data.get("constraints", {}),
                    implied_requirements=data.get("implied_requirements", []),
                    assumptions=data.get("assumptions", []),
                    confidence=data.get("confidence", 0.7),
                )
        except Exception as e:
            logger.warning(f"[IntentInterpreter] Failed to parse response: {e}")
        return self._fallback_interpret(user_input, {})

    def _fallback_interpret(self, user_input: str, context: Optional[Dict[str, Any]]) -> StructuredIntent:
        return StructuredIntent(
            outcome=user_input,
            entities={},
            urgency="medium",
            importance="medium",
            constraints={},
            implied_requirements=[],
            assumptions=[],
            confidence=0.5,
        )
