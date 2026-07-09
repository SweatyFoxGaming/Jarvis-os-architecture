from src.core.models import Capability
from src.departments.research import ResearchDepartment
from src.departments.coding import CodingDepartment
from src.core.registry import CapabilityRegistry

def register_initial_capabilities(cap_registry: CapabilityRegistry):
    # Research Capabilities
    research_cap = Capability(
        name="research_specialist",
        purpose="Perform deep factual research and evidence collection.",
        inputs={"objective": "The topic to research"},
        outputs={"report": "Factual summary with evidence"},
        estimated_time_sec=30
    )
    cap_registry.register(research_cap, "Research")

    # Coding Capabilities
    coding_cap = Capability(
        name="coding_specialist",
        purpose="Generate, analyze, and optimize source code.",
        inputs={"objective": "Coding task description"},
        outputs={"code": "Source code", "language": "Programming language"},
        estimated_time_sec=45
    )
    cap_registry.register(coding_cap, "Coding")
