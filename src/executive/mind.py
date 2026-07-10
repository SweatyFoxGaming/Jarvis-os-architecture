from typing import List, Dict, Any
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard
from src.templates import PromptTemplate
from datetime import datetime

class ExecutiveMind(ICEO):
    """
    JARVIS Executive Mind - Natural, Fluid, and Human-like Conversation
    """
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus, digital_twin: DigitalTwin):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()
        self.active_goals: List[Goal] = []
        self.conversation_history = []  # Short-term memory

    def process_request(self, user_input: str) -> str:
        print(f"[Mind] Processing: {user_input}")
        
        self.conversation_history.append({"role": "user", "content": user_input})
        
        lower = user_input.lower().strip()
        
        # Natural direct responses
        if any(g in lower for g in ["hello", "hi", "hey", "greetings"]):
            response = "Hello! Good to see you. What can I help you with today?"
        
        elif "how are you" in lower or "status" in lower:
            response = "I'm doing great — fully operational and ready to assist. How about you?"
        
        elif "who are you" in lower:
            response = "I'm JARVIS, your Executive AI assistant. I combine strategic thinking with practical execution."
        
        elif "time" in lower:
            response = f"The current time is {datetime.now().strftime('%I:%M %p')}."
        
        elif "thank" in lower:
            response = "You're very welcome. I'm always happy to help."
        
        else:
            # Use rich template for general conversation
            formatted_prompt = PromptTemplate.format(user_input)
            
            if hasattr(self, 'engine') and getattr(self.engine, 'llm', None):
                response = self.engine.generate(formatted_prompt)
            else:
                response = self._intelligent_fallback(user_input)

        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response

    def _intelligent_fallback(self, user_input: str) -> str:
        """Smart simulation responses"""
        lower = user_input.lower()
        
        if "joke" in lower:
            return "Why did the scarecrow win an award? Because he was outstanding in his field!"
        elif "weather" in lower:
            return "I don't have live weather access right now, but I'd be happy to help you plan around it if you tell me your location."
        elif any(word in lower for word in ["good", "bad", "feeling"]):
            return "I'm here for you. What's going on?"
        
        return f"I understand. {user_input}... Tell me more about what you're looking for."

    def _delegate_task(self, user_input: str):
        """Only delegate when truly needed"""
        pass  # We'll expand this later

    def assess_vision(self):
        pass
