from src.executive.executive_memory import ExecutiveMemory
from src.core.models import ExecutiveDecision
from src.memory.tiered_memory import HierarchicalMemory

# Setup
base = HierarchicalMemory()
mem = ExecutiveMemory(base)

# Record a decision
decision = ExecutiveDecision(
    intent="Research AI safety",
    context="Need to investigate alignment",
    reasoning_summary="AI safety is critical",
    confidence=0.85,
    expected_outcome="Comprehensive report",
    estimated_cost=0.5,
    estimated_time_sec=300,
)
mem.record_decision(decision)

# Record a lesson
mem.record_lesson("Always verify sources", outcome_success=True)

# Get history
print(mem.get_decision_history())
print(mem.get_lesson_history())
print(mem.get_stats())
mem.shutdown()
