import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.core.models import Capability

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """
    Registry for all platform capabilities.
    Capabilities are discoverable, inspectable, and replaceable.
    """

    def __init__(self):
        self._capabilities: Dict[str, Capability] = {}
        self._capability_handlers: Dict[str, Any] = {}
        logger.info("[CapabilityRegistry] Initialized.")

    def register(self, capability: Capability, handler: Any = None) -> None:
        """
        Register a capability with an optional handler.
        """
        if capability.name in self._capabilities:
            logger.warning(f"Overwriting capability: {capability.name}")
        self._capabilities[capability.name] = capability
        if handler:
            self._capability_handlers[capability.name] = handler
        logger.info(f"[CapabilityRegistry] Registered: {capability.name} v{capability.version}")

    def get(self, name: str) -> Optional[Capability]:
        return self._capabilities.get(name)

    def get_handler(self, name: str) -> Optional[Any]:
        return self._capability_handlers.get(name)

    def list(self) -> List[str]:
        return list(self._capabilities.keys())

    def list_with_metadata(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": cap.name,
                "version": cap.version,
                "purpose": cap.purpose,
                "inputs": cap.inputs,
                "outputs": cap.outputs,
                "dependencies": cap.dependencies,
                "estimated_cost": cap.estimated_cost,
                "estimated_time_sec": cap.estimated_time_sec,
                "health_status": cap.health_status,
            }
            for cap in self._capabilities.values()
        ]

    def get_health(self, name: str) -> Optional[str]:
        cap = self._capabilities.get(name)
        return cap.health_status if cap else None

    def update_health(self, name: str, status: str) -> bool:
        cap = self._capabilities.get(name)
        if cap:
            cap.health_status = status
            cap.updated_at = datetime.now()
            return True
        return False

    def shutdown(self):
        logger.info("[CapabilityRegistry] Shutting down.")
        self._capabilities.clear()
        self._capability_handlers.clear()
