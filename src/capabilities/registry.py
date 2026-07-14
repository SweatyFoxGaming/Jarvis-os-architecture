import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.capabilities.manifest import CapabilityManifest, CapabilityState, CapabilityHealth
from src.capabilities.contract import Capability

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """
    Stores all capability metadata, implementations, health, and confidence.
    """

    def __init__(self):
        self._manifests: Dict[str, CapabilityManifest] = {}
        self._implementations: Dict[str, Capability] = {}
        self._health: Dict[str, CapabilityHealth] = {}
        self._confidence: Dict[str, float] = {}
        self._last_updated: Dict[str, datetime] = {}
        logger.info("[CapabilityRegistry] Initialized.")

    def register(self, manifest: CapabilityManifest, implementation: Capability) -> None:
        manifest_id = manifest.identity.id
        self._manifests[manifest_id] = manifest
        self._implementations[manifest_id] = implementation
        self._health[manifest_id] = CapabilityHealth.AVAILABLE
        self._confidence[manifest_id] = 0.5  # start neutral
        self._last_updated[manifest_id] = datetime.now()
        logger.info(f"[CapabilityRegistry] Registered capability: {manifest_id} v{manifest.lifecycle.version}")

    def get_manifest(self, capability_id: str) -> Optional[CapabilityManifest]:
        return self._manifests.get(capability_id)

    def get_implementation(self, capability_id: str) -> Optional[Capability]:
        return self._implementations.get(capability_id)

    def get_health(self, capability_id: str) -> Optional[CapabilityHealth]:
        return self._health.get(capability_id)

    def set_health(self, capability_id: str, health: CapabilityHealth) -> None:
        self._health[capability_id] = health
        self._last_updated[capability_id] = datetime.now()
        # Also update the manifest lifecycle status if needed
        if health == CapabilityHealth.OFFLINE:
            self._manifests[capability_id].lifecycle.status = CapabilityState.OFFLINE
        elif health == CapabilityHealth.DEGRADED:
            self._manifests[capability_id].lifecycle.status = CapabilityState.DEGRADED

    def get_confidence(self, capability_id: str) -> float:
        return self._confidence.get(capability_id, 0.0)

    def update_confidence(self, capability_id: str, success: bool) -> None:
        current = self._confidence.get(capability_id, 0.5)
        # Simple moving average: success increases, failure decreases
        delta = 0.05 if success else -0.05
        new = max(0.0, min(1.0, current + delta))
        self._confidence[capability_id] = new

    def list_capabilities(self) -> List[str]:
        return list(self._manifests.keys())

    def get_all_manifests(self) -> List[CapabilityManifest]:
        return list(self._manifests.values())

    def get_all_implementations(self) -> Dict[str, Capability]:
        return self._implementations
