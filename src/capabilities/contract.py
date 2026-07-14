from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.capabilities.context import ExecutionContext


class Capability(ABC):
    """
    The contract that every capability must implement.
    The Execution Engine never cares how the capability is delivered.
    """

    @abstractmethod
    def initialize(self) -> None:
        """Perform any one‑time setup."""
        pass

    @abstractmethod
    def validate(self, context: ExecutionContext) -> bool:
        """Check if the capability is valid for the given context."""
        pass

    @abstractmethod
    def execute(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute the capability with the given context."""
        pass

    @abstractmethod
    def health(self) -> Dict[str, Any]:
        """Return the current health status (available, healthy, degraded, etc.)."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Clean up resources."""
        pass

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Return capability metadata (identity, version, etc.)."""
        pass
