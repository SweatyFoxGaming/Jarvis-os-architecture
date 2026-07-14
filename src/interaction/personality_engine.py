
"""
Personality Engine – Builds prompts based on tone.
Governed by INTERACTION_MODEL.md
"""

import logging
from typing import Dict, Any
from src.interaction.models import Tone

logger = logging.getLogger(__name__)


class PersonalityEngine:
    """
    Constructs the system prompt and tone instructions.
    This replaces the static PromptTemplate.
    """

    # Base executive personality
    EXECUTIVE_BASE = """
You are Jarvis, an executive AI assistant.
You are calm, professional, confident, and transparent.
You never reveal internal architecture unless explicitly asked.
You communicate with clarity and purpose.
"""

    TONE_MAPPINGS = {
        Tone.PROFESSIONAL: """
Communicate in a formal, professional tone.
Use precise language.
Be concise but comprehensive.
""",
        Tone.CASUAL: """
Communicate in a warm, casual tone.
Use friendly language.
Be approachable and relaxed.
""",
        Tone.BRIEF: """
Communicate very briefly.
Provide only essential information.
No fluff.
""",
        Tone.TECHNICAL: """
Communicate in a technical tone.
Use precise technical terminology.
Provide detailed reasoning.
""",
        Tone.ENCOURAGING: """
Communicate in an encouraging, supportive tone.
Acknowledge effort.
Be positive and motivating.
""",
        Tone.DIRECT: """
Communicate directly and assertively.
State facts plainly.
No hedging.
""",
        Tone.EMPATHETIC: """
Communicate with empathy and understanding.
Acknowledge the user's perspective.
Be warm and supportive.
""",
    }

    def __init__(self):
        logger.info("[PersonalityEngine] Initialized.")

    def build_system_prompt(self, tone: Tone, custom_context: str = "") -> str:
        """Build the full system prompt based on tone and optional context."""
        prompt = self.EXECUTIVE_BASE + "\n"
        prompt += self.TONE_MAPPINGS.get(tone, self.TONE_MAPPINGS[Tone.PROFESSIONAL])
        if custom_context:
            prompt += f"\nAdditional Context: {custom_context}\n"
        return prompt

    def get_response_instruction(self, tone: Tone) -> str:
        """Get instruction for the LLM on how to format responses."""
        if tone in [Tone.BRIEF, Tone.DIRECT]:
            return "Respond with minimal elaboration. Do not add extra commentary."
        elif tone == Tone.TECHNICAL:
            return "Provide detailed, technical explanations. Use structured reasoning."
        elif tone == Tone.EMPATHETIC:
            return "Show empathy and emotional intelligence in your responses."
        else:
            return "Respond naturally, maintaining the Jarvis executive persona."

    def adapt_tone(self, user_input: str, current_tone: Tone) -> Tone:
        """Optionally adjust tone based on user input (stub for future)."""
        # For now, just return the current tone.
        return current_tone
