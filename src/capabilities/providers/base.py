from abc import ABC, abstractmethod
from typing import List, Optional

from src.capabilities.contract import Capability
from src.capabilities.manifest import CapabilityManifest


class CapabilityProvider(ABC):
    """
    A source of capabilities. Built-in, filesystem, Docker, MCP, etc.
    """

    @abstractmethod
    def discover(self) -> List[CapabilityManifest]:
        """Discover and return all manifests from this provider."""
        pass

    @abstractmethod
    def load(self, manifest: CapabilityManifest) -> Optional[Capability]:
        """Load the capability implementation from the manifest."""
        pass

    @abstractmethod
    def watch(self) -> None:
        """Continuously monitor for changes (optional, can be no‑op)."""
        pass
