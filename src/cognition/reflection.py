import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.cognition.models import Experience, Belief, WorkspaceContents
from src.llm_engine import LLMEngine

logger = logging.getLogger(__name__)


class ReflectionEngine:
    """
    Generates insights and beliefs from experiences and workspace.
    """

    def __init__(self, engine: Optional[LLMEngine] = None):
        self.engine = engine
        logger.info("[ReflectionEngine] Initialized.")

    def set_engine(self, engine: LLMEngine) -> None:
        self.engine = engine
        logger.info("[ReflectionEngine] LLMEngine attached.")

    def reflect_immediate(self, experience: Experience, workspace: WorkspaceContents) -> List[Belief]:
        """
        Immediate reflection after an experience.
        Returns a list of new Beliefs.
        """
        logger.info(f"[ReflectionEngine] Immediate reflection for experience {experience.uuid}")

        if self.engine is None:
            logger.warning("[ReflectionEngine] No LLM engine available. Falling back to no-op.")
            return []

        prompt = f"""
You are Jarvis, reflecting on the following experience.

Experience: {experience.content}
Workspace Context: {workspace.model_dump_json(indent=2)}

Ask yourself:
1. What happened?
2. Why did it happen?
3. What should I remember?
4. What should I do differently next time?

Return your reflection as a list of beliefs. Each belief should be a statement, with a confidence score (0-1) and a brief reason.

Format:
Belief 1: [statement] | Confidence: [0-1] | Reason: [brief explanation]
Belief 2: [statement] | Confidence: [0-1] | Reason: [brief explanation]
...
"""

        try:
            response = self.engine.generate(prompt, max_tokens=512, temperature=0.3)
            beliefs = self._parse_beliefs(response, experience)
            logger.info(f"[ReflectionEngine] Generated {len(beliefs)} beliefs.")
            return beliefs
        except Exception as e:
            logger.error(f"[ReflectionEngine] Reflection failed: {e}")
            return []

    def _parse_beliefs(self, response: str, experience: Experience) -> List[Belief]:
        """
        Parse the LLM response into Belief objects.
        """
        beliefs = []
        lines = response.strip().split('\n')
        for line in lines:
            if 'Belief' in line:
                try:
                    # Parse: "Belief 1: statement | Confidence: 0.8 | Reason: ..."
                    parts = line.split('|')
                    if len(parts) >= 2:
                        claim_part = parts[0].split(':', 1)[1].strip() if ':' in parts[0] else parts[0].strip()
                        confidence_part = [p for p in parts if 'Confidence' in p]
                        confidence = 0.5
                        if confidence_part:
                            try:
                                confidence_str = confidence_part[0].split(':', 1)[1].strip()
                                confidence = float(confidence_str)
                            except:
                                pass
                        belief = Belief(
                            claim=claim_part,
                            confidence=confidence,
                            source=experience.source,
                            source_uuid=experience.uuid,
                        )
                        beliefs.append(belief)
                except Exception as e:
                    logger.warning(f"[ReflectionEngine] Failed to parse belief: {line} - {e}")
        return beliefs
