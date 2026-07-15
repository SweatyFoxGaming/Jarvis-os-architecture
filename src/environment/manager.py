"""
Environment Platform – Manager.
"""

import logging
from typing import Dict, Any, Optional, List
from src.environment.models import Domain, ProviderHealth
from src.environment.providers.base import EnvironmentProvider
from src.core.interfaces import IEventBus
from src.core.models import Event

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """
    Entry point for the Environment Platform.
    Routes requests to the appropriate provider.
    """

    def __init__(self, event_bus: Optional[IEventBus] = None):
        self.event_bus = event_bus
        self.providers: Dict[str, EnvironmentProvider] = {}
        self.domain_map: Dict[Domain, str] = {}
        logger.info("[EnvironmentManager] Initialized.")

    def register_provider(self, provider_id: str, provider: EnvironmentProvider) -> None:
        """Register a provider."""
        self.providers[provider_id] = provider
        try:
            meta = provider.metadata()
            domain = meta.domain
            if domain not in self.domain_map:
                self.domain_map[domain] = provider_id
                logger.info(f"[EnvironmentManager] Registering provider '{provider_id}' for domain '{domain}'")
            else:
                logger.warning(f"[EnvironmentManager] Domain '{domain}' already has provider '{self.domain_map[domain]}'. Skipping '{provider_id}'.")
        except Exception as e:
            logger.error(f"[EnvironmentManager] Failed to get metadata for provider '{provider_id}': {e}")
        try:
            provider.initialize()
        except Exception as e:
            logger.error(f"[EnvironmentManager] Failed to initialize provider '{provider_id}': {e}")

    def get_provider(self, provider_id: str) -> Optional[EnvironmentProvider]:
        """Get a provider by its ID."""
        return self.providers.get(provider_id)

    def get_domain_provider(self, domain: Domain) -> Optional[EnvironmentProvider]:
        """Get the provider for a given domain."""
        provider_id = self.domain_map.get(domain)
        if provider_id:
            return self.providers.get(provider_id)
        return None

    def execute(self, domain: Domain, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a capability in the given domain."""
        provider = self.get_domain_provider(domain)
        if not provider:
            return {"error": f"No provider found for domain '{domain}'"}
        if provider.health() not in (ProviderHealth.AVAILABLE, ProviderHealth.BUSY, ProviderHealth.DEGRADED):
            return {"error": f"Provider for domain '{domain}' is not available (health: {provider.health()})"}
        return provider.execute(capability, params)

    def health_check(self) -> Dict[str, ProviderHealth]:
        """Return health status of all providers."""
        return {pid: p.health() for pid, p in self.providers.items()}

    def shutdown(self) -> None:
        """Shut down all providers."""
        for pid, p in self.providers.items():
            try:
                p.shutdown()
                logger.info(f"[EnvironmentManager] Shut down provider '{pid}'")
            except Exception as e:
                logger.error(f"[EnvironmentManager] Error shutting down provider '{pid}': {e}")
