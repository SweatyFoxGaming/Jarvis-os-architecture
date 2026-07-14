import logging
from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ExecutionState(str, Enum):
    CREATED = "created"
    ACCEPTED = "accepted"
    PLANNED = "planned"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    RETRYING = "retrying"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class StateTransition:
    """Defines a valid state transition."""

    def __init__(self, from_state: ExecutionState, to_state: ExecutionState, condition: Optional[callable] = None):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition


class ExecutionStateMachine:
    """
    Formal state machine governing all execution lifecycles.
    """

    def __init__(self):
        self._transitions: Dict[ExecutionState, List[StateTransition]] = {}
        self._current_state: Optional[ExecutionState] = None
        self._history: List[Dict[str, Any]] = []
        self._initialize_transitions()

    def _initialize_transitions(self):
        self._transitions = {
            ExecutionState.CREATED: [
                StateTransition(ExecutionState.CREATED, ExecutionState.ACCEPTED),
            ],
            ExecutionState.ACCEPTED: [
                StateTransition(ExecutionState.ACCEPTED, ExecutionState.PLANNED),
                StateTransition(ExecutionState.ACCEPTED, ExecutionState.REJECTED, condition=lambda x: x.get("reject", False)),
            ],
            ExecutionState.PLANNED: [
                StateTransition(ExecutionState.PLANNED, ExecutionState.READY),
            ],
            ExecutionState.READY: [
                StateTransition(ExecutionState.READY, ExecutionState.RUNNING),
            ],
            ExecutionState.RUNNING: [
                StateTransition(ExecutionState.RUNNING, ExecutionState.WAITING),
                StateTransition(ExecutionState.RUNNING, ExecutionState.COMPLETED),
                StateTransition(ExecutionState.RUNNING, ExecutionState.FAILED),
            ],
            ExecutionState.WAITING: [
                StateTransition(ExecutionState.WAITING, ExecutionState.RUNNING),
                StateTransition(ExecutionState.WAITING, ExecutionState.COMPLETED),
                StateTransition(ExecutionState.WAITING, ExecutionState.FAILED),
            ],
            ExecutionState.RETRYING: [
                StateTransition(ExecutionState.RETRYING, ExecutionState.RUNNING),
                StateTransition(ExecutionState.RETRYING, ExecutionState.COMPLETED),
                StateTransition(ExecutionState.RETRYING, ExecutionState.FAILED),
            ],
            ExecutionState.REVIEWING: [
                StateTransition(ExecutionState.REVIEWING, ExecutionState.COMPLETED),
                StateTransition(ExecutionState.REVIEWING, ExecutionState.RUNNING),
                StateTransition(ExecutionState.REVIEWING, ExecutionState.ARCHIVED),
            ],
            ExecutionState.COMPLETED: [
                StateTransition(ExecutionState.COMPLETED, ExecutionState.ARCHIVED),
            ],
            ExecutionState.FAILED: [
                StateTransition(ExecutionState.FAILED, ExecutionState.RETRYING),
                StateTransition(ExecutionState.FAILED, ExecutionState.ARCHIVED),
            ],
        }

    def can_transition(self, current: ExecutionState, target: ExecutionState, context: Dict[str, Any] = None) -> bool:
        context = context or {}
        transitions = self._transitions.get(current, [])
        for transition in transitions:
            if transition.to_state == target:
                if transition.condition is None or transition.condition(context):
                    return True
        return False

    def transition(self, current: ExecutionState, target: ExecutionState, context: Dict[str, Any] = None) -> Optional[ExecutionState]:
        if not self.can_transition(current, target, context):
            logger.warning(f"Invalid transition: {current} -> {target}")
            return None

        self._history.append({
            "from_state": current.value,
            "to_state": target.value,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        })
        self._current_state = target
        logger.debug(f"State transition: {current} -> {target}")
        return target

    def get_history(self) -> List[Dict[str, Any]]:
        return self._history.copy()

    def get_current_state(self) -> Optional[ExecutionState]:
        return self._current_state

    def reset(self):
        self._current_state = None
        self._history = []
