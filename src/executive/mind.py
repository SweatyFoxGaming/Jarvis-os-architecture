from typing import List, Dict, Any
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard
from src.templates import PromptTemplate
from datetime import datetime

class ExecutiveMind(ICEO):
    """
    Final upgraded JARVIS Executive Mind with strong natural conversation.
    """
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus, digital_twin: DigitalTwin):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()
        self.active_goals: List[Goal] = []

    def process_request(self, user_input: str) -> str:
        print(f"[Mind] Processing: {user_input}")
        
        lower = user_input.lower().strip()
        
        # Quick direct responses for best natural flow
        if any(word in lower for word in ["hello", "hi", "hey", "greetings"]):
            return "Hello! JARVIS at your service. What’s on your mind today?"

        if "how are you" in lower or "status" in lower:
            return "I'm running perfectly — all cognitive systems and departments are online and ready."

        if "who are you" in lower:
            return "I am JARVIS, the Executive Mind of the Phoenix Intelligence Platform. Think of me as your strategic partner."

        if "time" in lower:
            current_time = datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}."

        if "thank" in lower:
            return "You're very welcome. I'm glad I could help."

        if "joke" in lower:
            return "Why do programmers prefer dark mode? Because light attracts bugs."

        # Use rich template for most other queries
        formatted_prompt = PromptTemplate.format(user_input)
        
        # Generate response (simulation or real)
        if hasattr(self, 'engine') and getattr(self.engine, 'llm', None):
            response = self.engine.generate(formatted_prompt)
        else:
            response = self._natural_response(user_input)
        
        # Delegate only when clearly needed
        if any(k in lower for k in ["code", "write", "function", "debug", "python", "rust", "build", "create", "algorithm"]):
            self._delegate_task(user_input)
            response += "\n\nI'll also have the Coding Department review this for you."
        
        return response

    def _natural_response(self, user_input: str) -> str:
        """High-quality fallback responses"""
        lower = user_input.lower()
        
        if "weather" in lower:
            return "I don't have live weather data in this mode, but I can help you plan around it or suggest what to wear based on your location."
        
        if "how old" in lower or "age" in lower:
            return "I'm as old as the last time you improved me. Which is continuously."
        
        # Default thoughtful response
        return f"I understand what you're asking. {user_input}...\n\nHow would you like me to approach this?"

    def _delegate_task(self, user_input: str):
        """Route to appropriate department"""
        capability = "coding_specialist" if any(k in user_input.lower() for k in ["code", "write", "function"]) else "research_specialist"
        
        task = Task(
            creator_id="ExecutiveMind",
            target_capability=capability,
            input_data={"request": user_input}
        )
        self.cos.schedule_task(task)

    def assess_vision(self):
        pass
