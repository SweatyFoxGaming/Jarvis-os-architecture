import logging
import traceback
from typing import Any, Dict, Optional
from abc import ABC, abstractmethod

# Import models (ensure RiskLevel exists; if not, define a fallback)
from src.core.models import ExecutiveDecision, Goal, RiskLevel

# Secure components (optional, injected for future use)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

# Logger
logger = logging.getLogger(__name__)


# ---------- 1. Base Abstract Engine ----------
class BaseReasoningEngine(ABC):
    """Base class for all reasoning engines in the Executive Board."""

    @abstractmethod
    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform reasoning based on the given input state.
        Should return a dictionary with reasoning results.
        """
        pass


# ---------- 2. Individual Engines (with safe fallbacks) ----------
class StrategyEngine(BaseReasoningEngine):
    """Long-term planning & objective alignment."""

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[StrategyEngine] Reasoning...")
        # In a real implementation, this would analyze input_data.
        # For now, return a default struct.
        return {
            "alignment": "Strategic",
            "opportunity": "High",
            "long_term_impact": "High",
            "analysis": input_data.get("user_input", "")[:50],
        }


class PlanningEngine(BaseReasoningEngine):
    """Phase decomposition & dependency analysis."""

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[PlanningEngine] Reasoning...")
        return {
            "phases": ["Research", "Design", "Implementation"],
            "dependencies": [],
            "critical_path": ["Design"],
        }


class RiskEngine(BaseReasoningEngine):
    """Threat detection & uncertainty assessment."""

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[RiskEngine] Reasoning...")
        return {
            "risk_level": RiskLevel.LOW,
            "threats": [],
            "confidence_score": 0.95,
            "mitigations": ["Standard monitoring"],
        }


class ResourceEngine(BaseReasoningEngine):
    """Hardware utilization & budgets."""

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[ResourceEngine] Reasoning...")
        return {
            "cpu_allocation": 0.2,
            "ram_mb": 512,
            "token_budget": 2000,
            "available_resources": {"cpu": 4, "ram": 8192},
        }


class ContextEngine(BaseReasoningEngine):
    """User & environment context."""

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[ContextEngine] Reasoning...")
        return {
            "project": "Phoenix Intelligence",
            "user_intent": "Exploration",
            "environment": "Development",
        }


class MemoryEngine(BaseReasoningEngine):
    """Executive memory & historical outcomes."""

    def __init__(self, secure_memory: Optional[SecureMemoryStore] = None):
        self.secure_memory = secure_memory

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[MemoryEngine] Reasoning...")
        # If secure memory is available, we could retrieve past decisions.
        # For now, return static data.
        return {
            "relevant_past_decisions": 0,
            "previous_success_rate": 1.0,
            "memory_available": self.secure_memory is not None,
        }


class EthicsSafetyEngine(BaseReasoningEngine):
    """Constitutional compliance & safe behavior."""

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[EthicsSafetyEngine] Reasoning...")
        return {
            "constitutional_status": "Compliant",
            "risk_mitigation": "Standard",
            "review_required": False,
        }


class WorldModelEngine(BaseReasoningEngine):
    """Digital Twin integration & environment state."""

    def reason(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        logger.debug("[WorldModelEngine] Reasoning...")
        return {
            "environment_stability": "High",
            "hardware_load": "Low",
            "digital_twin_status": "Synchronized",
        }


# ---------- 3. Executive Board ----------
class ExecutiveBoard:
    """
    Internal reasoning council representing different styles of executive reasoning.
    Consulted by the Executive Mind.
    Now with logging, error isolation, and optional secure memory injection.
    """

    def __init__(self, secure_memory: Optional[SecureMemoryStore] = None):
        self.secure_memory = secure_memory

        # Instantiate all engines, passing secure memory to those that need it.
        self.engines = {
            "strategy": StrategyEngine(),
            "planning": PlanningEngine(),
            "risk": RiskEngine(),
            "resource": ResourceEngine(),
            "context": ContextEngine(),
            "memory": MemoryEngine(secure_memory=secure_memory),
            "ethics": EthicsSafetyEngine(),
            "world": WorldModelEngine(),
        }
        logger.info(
            f"[ExecutiveBoard] Initialized with {len(self.engines)} engines. "
            f"Secure memory: {secure_memory is not None}"
        )

    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        """Inject secure memory after construction (for dependency injection)."""
        self.secure_memory = secure_memory
        # Update the memory engine if it exists
        if "memory" in self.engines and isinstance(self.engines["memory"], MemoryEngine):
            self.engines["memory"].secure_memory = secure_memory
        logger.info("[ExecutiveBoard] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        """Inject secure command runner (for future use)."""
        # We don't currently use the runner in engines, but keep for consistency.
        logger.info("[ExecutiveBoard] SecureCommandRunner attached (not used yet).")

    def consult(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consult all engines and return a dictionary of their reasoning results.
        If any engine fails, its error is logged and an error entry is returned
        so the board can still function.
        """
        results = {}
        for name, engine in self.engines.items():
            try:
                logger.debug(f"[Board] Consulting {name.capitalize()} Engine...")
                results[name] = engine.reason(state)
            except Exception as e:
                error_trace = traceback.format_exc()
                logger.error(f"[Board] Engine '{name}' failed: {e}\n{error_trace}")
                results[name] = {
                    "error": str(e),
                    "status": "failed",
                    "trace": error_trace,
                }
        return results

    def consult_one(self, engine_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Consult a single engine by name. Useful if the Mind only needs one aspect.
        """
        engine = self.engines.get(engine_name)
        if engine is None:
            logger.warning(f"[Board] Engine '{engine_name}' not found.")
            return {"error": f"Engine '{engine_name}' not found", "status": "error"}
        try:
            logger.debug(f"[Board] Consulting single engine: {engine_name}")
            return engine.reason(state)
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[Board] Engine '{engine_name}' failed: {e}\n{error_trace}")
            return {"error": str(e), "status": "failed", "trace": error_trace}

    # Optional: add a method to list available engines
    def list_engines(self) -> List[str]:
        return list(self.engines.keys())
