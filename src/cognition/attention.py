import logging
from typing import Optional

from src.cognition.models import Experience, ExperienceType

logger = logging.getLogger(__name__)


class AttentionFilter:
    """
    Filters experiences that are worth further cognitive processing.
    """

    @staticmethod
    def should_process(experience: Experience) -> bool:
        """
        Determine if an experience should enter the cognitive pipeline.
        """
        # Always process if user explicitly says "remember"
        if isinstance(experience.content, str) and "remember" in experience.content.lower():
            return True

        # Always process capability failures
        if experience.type == ExperienceType.CAPABILITY_FAILURE:
            return True

        # Always process if tied to a high-priority Goal
        if experience.goal_uuid:
            # We'll check priority later when the goal is resolved
            pass

        # Process if there is strong sentiment (we'll check later via LLM)
        # For now, we process most experiences to be safe, but log it.
        # In a more advanced implementation, we'd use an LLM to decide.
        logger.debug(f"[Attention] Processing experience: {experience.type} from {experience.source}")
        return True
