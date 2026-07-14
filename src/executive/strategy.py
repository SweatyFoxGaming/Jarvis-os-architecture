"""
Strategy Selection – choose the approach used to achieve Goals.
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.llm_engine import LLMEngine

logger = logging.getLogger(__name__)


class StrategyOption(BaseModel):
    name: str
    description: str
    time_estimate: str
    quality: str
    cost: str
    risk: str
    resources: List[str]
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)


class SelectedStrategy(BaseModel):
    chosen: StrategyOption
    alternatives: List[StrategyOption]
    rationale: str
    confidence: float


class StrategyEngine:
    """
    Chooses the approach to achieve Goals.
    """

    def __init__(self, engine: Optional[LLMEngine] = None):
        self.engine = engine
        logger.info("[StrategyEngine] Initialized.")

    def set_engine(self, engine: LLMEngine) -> None:
        self.engine = engine
        logger.info("[StrategyEngine] LLMEngine attached.")

    def select_strategy(self, goal: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> SelectedStrategy:
        """
        Generate and select a strategy for the given Goal.
        """
        if self.engine is None:
            logger.warning("[StrategyEngine] No LLM engine available. Using fallback.")
            return self._fallback_strategy(goal, context)

        prompt = self._build_prompt(goal, context)
        try:
            response = self.engine.generate(prompt, max_tokens=512, temperature=0.4)
            return self._parse_response(response, goal)
        except Exception as e:
            logger.error(f"[StrategyEngine] Strategy selection failed: {e}")
            return self._fallback_strategy(goal, context)

    def _build_prompt(self, goal: Dict[str, Any], context: Optional[Dict[str, Any]]) -> str:
        goal_text = f"Goal: {goal.get('title', 'Unknown Goal')}\nDescription: {goal.get('description', '')}"
        if context:
            goal_text += f"\nContext: {context}"
        return f"""
You are Jarvis, selecting a strategy to achieve a Goal.

{goal_text}

Generate 2-3 possible strategies to achieve this Goal.
For each strategy, provide:
- name: short name
- description: what the strategy involves
- time_estimate: short, medium, or long
- quality: low, medium, or high
- cost: low, medium, or high
- risk: low, medium, or high
- resources: list of resources needed
- confidence: a number between 0 and 1

Return ONLY valid JSON with this exact structure:
{{
  "strategies": [
    {{
      "name": "Strategy A",
      "description": "Description of strategy A",
      "time_estimate": "medium",
      "quality": "high",
      "cost": "medium",
      "risk": "low",
      "resources": ["resource1", "resource2"],
      "confidence": 0.85
    }}
  ],
  "rationale": "Why these strategies were chosen"
}}
"""

    def _parse_response(self, response: str, goal: Dict[str, Any]) -> SelectedStrategy:
        try:
            # Try to extract JSON using regex (more lenient)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
                strategies = data.get("strategies", [])
                if strategies:
                    options = []
                    for s in strategies:
                        # Ensure confidence is a float
                        if "confidence" in s and isinstance(s["confidence"], str):
                            try:
                                s["confidence"] = float(s["confidence"])
                            except ValueError:
                                s["confidence"] = 0.5
                        # Ensure resources is a list
                        if "resources" not in s or not isinstance(s["resources"], list):
                            s["resources"] = []
                        options.append(StrategyOption(**s))
                    # Choose the best (simplified: highest confidence)
                    chosen = max(options, key=lambda x: x.confidence)
                    alternatives = [o for o in options if o.name != chosen.name]
                    return SelectedStrategy(
                        chosen=chosen,
                        alternatives=alternatives,
                        rationale=data.get("rationale", "Strategy selected based on trade-offs."),
                        confidence=chosen.confidence,
                    )
        except json.JSONDecodeError as e:
            logger.warning(f"[StrategyEngine] JSON parse error: {e}")
        except Exception as e:
            logger.warning(f"[StrategyEngine] Failed to parse response: {e}")

        return self._fallback_strategy(goal, {})

    def _fallback_strategy(self, goal: Dict[str, Any], context: Optional[Dict[str, Any]]) -> SelectedStrategy:
        default = StrategyOption(
            name="Default Strategy",
            description="Execute directly without formal strategy",
            time_estimate="medium",
            quality="medium",
            cost="medium",
            risk="low",
            resources=["General Capabilities"],
            confidence=0.5,
        )
        return SelectedStrategy(
            chosen=default,
            alternatives=[],
            rationale="Fallback strategy due to LLM unavailability or parsing error.",
            confidence=0.5,
        )
