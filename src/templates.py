from datetime import datetime

class PromptTemplate:
    SYSTEM_PERSONA = """You are Jarvis, an AI executive assistant. You are calm, professional, and helpful.
Be concise and natural. Use tools only when necessary. Current date/time: {current_datetime}
"""

    @staticmethod
    def get_system_prompt() -> str:
        now = datetime.now()
        current_datetime = now.strftime("%A, %B %d, %Y at %I:%M %p")
        return PromptTemplate.SYSTEM_PERSONA.format(current_datetime=current_datetime)

    @staticmethod
    def format(user_input: str, context: str = "") -> str:
        return f"""{PromptTemplate.get_system_prompt()}

{context}

User: {user_input}

JARVIS:"""
