from typing import List, Dict, Any
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import ExecutiveDecision, Goal, Task, Priority, Event, TaskStatus
from src.core.digital_twin import DigitalTwin
from src.executive.board import ExecutiveBoard

class ExecutiveMind(ICEO):
    """
    The cognitive core of JARVIS. Responsible for thought, not execution.
    Thinks in goals and capabilities.
    """
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus, digital_twin: DigitalTwin):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.board = ExecutiveBoard()
        self.active_goals: List[Goal] = []

    def process_request(self, user_input: str) -> str:
        print(f"[Mind] Processing Executive Request: {user_input}")

        # 1. Intent & Context Analysis (Internal thought)
        context_summary = self.twin.get_summary()

        # 2. Board Consultation
        board_results = self.board.consult({
            "intent": user_input,
            "context": context_summary
        })

        # 3. Decision Formulation
        decision = ExecutiveDecision(
            intent=user_input,
            context=context_summary,
            reasoning_summary="Integrated board feedback for mission alignment.",
            confidence=board_results['risk']['confidence_score'],
            expected_outcome="Strategic objective achieved.",
            estimated_cost=0.01,
            estimated_time_sec=60,
            selected_capabilities=["research_specialist"] # Logic based on Board feedback
        )

        # 4. Capability Selection logic (Simplified for V3 MVP)
        capability = "research_specialist"
        if "code" in user_input.lower():
            capability = "coding_specialist"

        # 5. Goal Alignment
        new_goal = Goal(
            title=f"Objective: {user_input[:20]}",
            description=user_input,
            alignment="Board Validated"
        )
        self.active_goals.append(new_goal)

        # 6. Final Executive Decision -> Chief of Staff
        print(f"[Mind] Finalizing Decision: {decision.uuid}")

        task = Task(
            creator_id="ExecutiveMind",
            target_capability=capability,
            input_data={"objective": user_input, "executive_context": decision.dict()}
        )

        # Publish Executive Decision Event
        self.event_bus.publish(Event(
            event_type="ExecutiveDecisionFinalized",
            source="ExecutiveMind",
            payload=decision.dict()
        ))

        self.cos.schedule_task(task)

        return f"Executive Mind Decision: {decision.expected_outcome}. Orchestrating {capability}..."

    def assess_vision(self):
        # Long-term strategic awareness
        pass
