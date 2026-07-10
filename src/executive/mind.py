from typing import List, Dict, Any
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard
from src.templates import PromptTemplate
from src.memory.tiered_memory import HierarchicalMemory
from datetime import datetime

class ExecutiveMind(ICEO):
    """
    JARVIS Executive Mind - Natural conversation + Memory
    """
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus, digital_twin: DigitalTwin):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()
        self.memory = HierarchicalMemory()
        self.active_goals: List[Goal] = []

    def process_request(self, user_input: str) -> str:
        print(f"[Mind] Processing: {user_input}")
        
        # Get context from memory
        context = self.memory.get_recent_context()
        
        lower = user_input.lower().strip()
        
        # Direct responses
        if any(g in lower for g in ["hello", "hi", "hey"]):
            response = "Hello! Good to see you again. What can I do for you?"
        elif "how are you" in lower or "status" in lower:
            response = "I'm doing well, thanks for asking. Ready to help."
        elif "time" in lower:
            response = f"The current time is {datetime.now().strftime('%I:%M %p')}."
        else:
            # Use template with memory context
            full_context = context + "\nCurrent request context."
            formatted_prompt = PromptTemplate.format(user_input, full_context)
            
            if hasattr(self, 'engine') and getattr(self.engine, 'llm', None):
                response = self.engine.generate(formatted_prompt)
            else:
                response = f"I understand you're asking about {user_input}. How can I best assist?"

        # Store conversation in memory
        self.memory.store_conversation(user_input, response)
        
        return response

    def assess_vision(self):
        pass
