"""
Ecosystem Platform – Manager.
"""

import logging
from typing import List, Optional
from uuid import UUID

from src.ecosystem.models import PluginManifest, PluginState, HealthStatus, PluginPackage
from src.ecosystem.registry import PluginRegistry
from src.ecosystem.discovery import DiscoveryEngine
from src.ecosystem.lifecycle import PluginLifecycle

logger = logging.getLogger(__name__)


class EcosystemManager:
    """
    Orchestrates the Ecosystem Platform.
    """

    def __init__(self, plugin_path: str = "plugins", event_bus=None):
        self.plugin_path = plugin_path
        self.event_bus = event_bus
        self.registry = PluginRegistry()
        self.discovery = DiscoveryEngine(plugin_path)
        self.lifecycle = PluginLifecycle(self.registry, self.discovery, plugin_path, event_bus)

    def discover(self) -> List[PluginManifest]:
        """Discover new plugins."""
        manifests = self.discovery.discover_all()
        for m in manifests:
            existing = self.registry.get_by_name(m.name)
            if existing:
                continue
            self.registry.register(m)
        logger.info(f"[Ecosystem] Discovered {len(manifests)} new plugins.")
        return manifests

    def install(self, name: str, version: str = "1.0.0", description: str = "", author: str = "Unknown") -> PluginManifest:
        """Install a plugin from local discovery."""
        # Check if already installed
        existing = self.registry.get_by_name(name)
        if existing:
            logger.warning(f"Plugin {name} already installed.")
            return existing
        # Try to find a discovered manifest
        discovered = None
        for m in self.registry.list(PluginState.DISCOVERED):
            if m.name == name:
                discovered = m
                break
        if discovered:
            manifest = discovered
            self.lifecycle.install(manifest)
            self.lifecycle.load(str(manifest.id))
            self.lifecycle.activate(str(manifest.id))
            return manifest
        # Create a new manifest
        manifest = PluginManifest(
            name=name,
            version=version,
            description=description,
            author=author,
        )
        self.lifecycle.install(manifest)
        self.lifecycle.load(str(manifest.id))
        self.lifecycle.activate(str(manifest.id))
        return manifest

    def activate(self, plugin_id: str) -> bool:
        return self.lifecycle.activate(plugin_id)

    def deactivate(self, plugin_id: str) -> bool:
        return self.lifecycle.deactivate(plugin_id)

    def remove(self, plugin_id: str) -> bool:
        return self.lifecycle.remove(plugin_id)

    def list_plugins(self, state: Optional[str] = None) -> List[PluginManifest]:
        state_enum = PluginState(state) if state else None
        return self.registry.list(state_enum)

    def get_plugin(self, plugin_id: str) -> Optional[PluginManifest]:
        try:
            return self.registry.get(UUID(plugin_id))
        except ValueError:
            return None

    def health_check(self, plugin_id: str) -> HealthStatus:
        return self.lifecycle.health_check(plugin_id)

    def health_check_all(self) -> dict:
        results = {}
        for p in self.registry.list():
            if p.state == PluginState.ACTIVE:
                results[str(p.id)] = self.health_check(str(p.id))
        return results

    def marketplace_search(self, query: str) -> List[PluginPackage]:
        """Search marketplace for plugins (stub)."""
        return []
