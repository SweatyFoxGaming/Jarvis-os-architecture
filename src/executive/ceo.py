from typing import Optional, List
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import Task, Event, Priority, Goal, TaskStatus
from src.core.digital_twin import DigitalTwin

class CEO(ICEO):
    """
    JARVIS is the CEO.
    Answers: What are we trying to accomplish? Why? Who? Is it acceptable?
    """
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus, digital_twin: DigitalTwin):
        self.cos = chief_of_staff
        self.event_bus = event_bus
        self.twin = digital_twin
        self.goals: List[Goal] = []

    def process_request(self, user_input: str) -> str:
        print(f"[CEO] Strategy session for: {user_input}")

        # 1. Constitution Check / Fast-Path
        greetings = ["hi", "hello", "hey", "jarvis", "who are you"]
        low_input = user_input.lower().strip()
        if any(g in low_input for g in greetings) and len(low_input.split()) < 4:
            return "I am JARVIS. I lead the Phoenix Intelligence Swarm. What is our objective?"

        # 2. Intent & Goal Management
        # Define a high-level goal
        new_goal = Goal(
            title=f"Fulfill request: {user_input[:30]}...",
            description=user_input,
            priority=Priority.MEDIUM
        )
        self.goals.append(new_goal)

        # 3. Capability-based Orchestration (CEO thinks in capabilities, not departments)
        # Simplified reasoning for V2 Constitution alignment
        capability = "research_specialist"
        if any(k in low_input for k in ["code", "write", "fix", "rust", "python"]):
            capability = "coding_specialist"

        # 4. Delegate to Chief of Staff via Event Bus
        task = Task(
            creator_id="CEO",
            target_capability=capability,
            priority=Priority.MEDIUM,
            input_data={"objective": user_input, "context": self.twin.get_summary()}
        )

        self.event_bus.publish(Event(
            event_type="GoalEstablished",
            source="CEO",
            payload={"goal_id": str(new_goal.uuid), "task_id": str(task.uuid)}
        ))

        self.cos.schedule_task(task)

        return f"Strategic Goal established. Requirement: {capability}. (Task: {task.uuid})"
