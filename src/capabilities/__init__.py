"""
Capability Platform – the nervous system of Jarvis OS.
Capabilities are discoverable, versioned, health‑aware, and interchangeable.
"""

from .contract import Capability
from .context import ExecutionContext
from .manifest import CapabilityManifest, CapabilityState, CapabilityHealth
from .registry import CapabilityRegistry
from .resolver import CapabilityResolver
from .execution import CapabilityExecutionEngine
from .budgets import CapabilityBudget
from .policies import Policy, Permission
from .events import CapabilityEvents

# Providers
from .providers import CapabilityProvider, BuiltinProvider

__all__ = [
    "Capability",
    "ExecutionContext",
    "CapabilityManifest",
    "CapabilityState",
    "CapabilityHealth",
    "CapabilityRegistry",
    "CapabilityResolver",
    "CapabilityExecutionEngine",
    "CapabilityBudget",
    "Policy",
    "Permission",
    "CapabilityEvents",
    "CapabilityProvider",
    "BuiltinProvider",
]
