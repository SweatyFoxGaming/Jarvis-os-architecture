from typing import Optional
from src.core.interfaces import ICEO, IChiefOfStaff, IEventBus
from src.core.models import Task, Event, Priority

class CEO(ICEO):
    def __init__(self, chief_of_staff: IChiefOfStaff, event_bus: IEventBus):
        self.cos = chief_of_staff
        self.event_bus = event_bus

    def process_request(self, user_input: str) -> str:
        print(f"[CEO] Processing request: {user_input}")

        # 1. Understand Intent (In V2 this would be an LLM call)
        # For now, we simulate the intent understanding and department routing

        # 2. Publish UserIntentReceived event
        self.event_bus.publish(Event(
            event_type="UserIntentReceived",
            source="CEO",
            payload={"input": user_input}
        ))

        # 3. Determine Goal and Constraints
        # Simplified routing for MVP
        department = "Research"
        if "code" in user_input.lower() or "write" in user_input.lower():
            department = "Coding"

        # 4. Create Task
        new_task = Task(
            creator_id="CEO",
            target_department=department,
            priority=Priority.MEDIUM,
            input_data={"request": user_input}
        )

        # 5. Delegate to Chief of Staff
        self.cos.schedule_task(new_task)

        return f"Executive order issued. {department} Department is on the case. (Task ID: {new_task.uuid})"
