from typing import List, Dict, Any
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard

class ExecutiveMind(ICEO):
    """
    The cognitive core of JARVIS. Now handles simple conversation directly.
    """
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus, digital_twin: DigitalTwin):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()
        self.active_goals: List[Goal] = []

    def process_request(self, user_input: str) -> str:
        print(f"[Mind] Processing Executive Request: {user_input}")
        
        lower_input = user_input.lower().strip()
        
        # Direct responses for casual conversation (more human-like)
        if any(g in lower_input for g in ["hello", "hi", "hey", "how are you", "status", "who are you"]):
            direct_response = """Hello! I am JARVIS, the Executive Mind of the Phoenix Intelligence Platform.
I am fully operational with the complete cognitive architecture active.
How can I help you today?"""
            print("[Mind] Direct conversational response.")
            return direct_response

        # For more complex requests, use full delegation
        context_summary = self.twin.get_summary()
        
        board_results = self.board.consult({
            "intent": user_input,
            "context": context_summary
        })
        
        decision = ExecutiveDecision(
            intent=user_input,
            context=context_summary,
            reasoning_summary="Integrated board feedback.",
            confidence=0.85,
            expected_outcome="User request fulfilled.",
            estimated_cost=0.01,
            estimated_time_sec=30,
            selected_capabilities=["research_specialist"]
        )
        
        capability = "research_specialist"
        if any(k in lower_input for k in ["code", "write", "function", "class", "debug", "python", "rust"]):
            capability = "coding_specialist"
        
        new_goal = Goal(
            title=f"Objective: {user_input[:30]}",
            description=user_input,
            alignment="User Request"
        )
        self.active_goals.append(new_goal)
        
        print(f"[Mind] Finalizing Decision: {decision.uuid}")
        
        task = Task(
            creator_id="ExecutiveMind",
            target_capability=capability,
            input_data={"request": user_input, "executive_context": decision.dict()}
        )
        
        self.event_bus.publish(Event(
            event_type="ExecutiveDecisionFinalized",
            source="ExecutiveMind",
            payload=decision.dict()
        ))
        
        self.cos.schedule_task(task)
        
        return f"Understood. Orchestrating {capability} for your request..."

    def assess_vision(self):
        pass
