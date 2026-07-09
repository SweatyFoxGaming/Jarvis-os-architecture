from typing import List, Dict, Any
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard
from src.templates import PromptTemplate
from datetime import datetime

class ExecutiveMind(ICEO):
    """
    Upgraded JARVIS Executive Mind with comprehensive speaking template.
    """
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus, digital_twin: DigitalTwin):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()
        self.active_goals: List[Goal] = []

    def process_request(self, user_input: str) -> str:
        print(f"[Mind] Processing Executive Request: {user_input}")
        
        lower = user_input.lower().strip()
        
        # Direct handling for very simple queries
        if any(g in lower for g in ["hello", "hi", "hey"]):
            return "Hello! JARVIS at your service. What can I do for you today?"
        
        if "how are you" in lower or "status" in lower or "who are you" in lower:
            return "I am operating at full capacity. Executive Mind, departments, and memory systems are all active and ready."

        if "time" in lower:
            current_time = datetime.now().strftime("%I:%M %p")
            return f"The current time is {current_time}."

        # Use template for most responses
        template_context = "You are having a natural conversation with the user."
        
        formatted_prompt = PromptTemplate.format(user_input, template_context)
        
        # For now, use simulation since real model may not be loaded
        if hasattr(self, 'engine') and self.engine and self.engine.llm:
            response = self.engine.generate(formatted_prompt)
        else:
            # Enhanced simulation using template logic
            response = self._simulate_response(user_input)
        
        # If it's a complex task, still delegate
        if any(k in lower for k in ["code", "write", "function", "debug", "python", "rust", "build", "create"]):
            self._delegate_to_department(user_input)
            return response + "\n\nI'll also route this to the appropriate specialist department for deeper execution."
        
        return response

    def _simulate_response(self, user_input: str) -> str:
        """Fallback high-quality simulation"""
        lower = user_input.lower()
        
        if "joke" in lower:
            return "Why do programmers prefer dark mode? Because light attracts bugs. 😊"
        elif "weather" in lower:
            return "I don't have real-time weather access in this simulation, but I can help you plan around it if you tell me your location."
        elif "thank" in lower:
            return "You're very welcome. I'm here whenever you need me."
        else:
            return f"I understand you're asking about '{user_input}'. How would you like me to help with this?"

    def _delegate_to_department(self, user_input: str):
        """Helper to delegate complex tasks"""
        capability = "coding_specialist" if any(k in user_input.lower() for k in ["code", "write", "function"]) else "research_specialist"
        
        task = Task(
            creator_id="ExecutiveMind",
            target_capability=capability,
            input_data={"request": user_input}
        )
        self.cos.schedule_task(task)

    def assess_vision(self):
        pass
