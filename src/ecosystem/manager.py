"""
Ecosystem Platform – Manager.
"""

import logging
from typing import List, Optional, Dict, Any, Callable
from uuid import UUID

from src.ecosystem.models import PluginManifest, PluginState, HealthStatus, PluginPackage, PluginPermission
from src.ecosystem.registry import PluginRegistry
from src.ecosystem.discovery import DiscoveryEngine
from src.ecosystem.lifecycle import PluginLifecycle
from src.ecosystem.marketplace import MarketplaceClient
from src.ecosystem.sandbox import PluginSandbox, PermissionDenied

logger = logging.getLogger(__name__)


class EcosystemManager:
    """
    Orchestrates the Ecosystem Platform.
    """

    def __init__(self, plugin_path: str = "plugins", event_bus=None, marketplace_url: Optional[str] = None):
        self.plugin_path = plugin_path
        self.event_bus = event_bus
        self.registry = PluginRegistry()
        self.discovery = DiscoveryEngine(plugin_path)
        self.lifecycle = PluginLifecycle(self.registry, self.discovery, plugin_path, event_bus)
        self.marketplace = MarketplaceClient(marketplace_url)

    def discover(self) -> List[PluginManifest]:
        manifests = self.discovery.discover_all()
        for m in manifests:
            existing = self.registry.get_by_name(m.name)
            if existing:
                continue
            self.registry.register(m)
        logger.info(f"[Ecosystem] Discovered {len(manifests)} new plugins.")
        return manifests

    def install(self, name: str, version: str = "1.0.0", description: str = "", author: str = "Unknown") -> PluginManifest:
        existing = self.registry.get_by_name(name)
        if existing:
            logger.warning(f"Plugin {name} already installed.")
            return existing
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

    # ---------- Sandbox ----------
    def get_sandbox(self, plugin_id: str) -> Optional[PluginSandbox]:
        """Get a sandbox for a plugin."""
        manifest = self.get_plugin(plugin_id)
        if not manifest:
            return None
        return PluginSandbox(manifest)

    def execute_sandboxed(self, plugin_id: str, func: Callable, *args, **kwargs) -> Any:
        """
        Execute a function in the context of a plugin's sandbox.
        The sandbox is passed as the first argument to the function.
        The function should call sandbox.require() for permission checks.
        """
        sandbox = self.get_sandbox(plugin_id)
        if not sandbox:
            raise ValueError(f"Plugin {plugin_id} not found or not active")
        return func(sandbox, *args, **kwargs)

    # ---------- Marketplace Integration ----------
    def marketplace_search(self, query: str = "") -> List[PluginPackage]:
        return self.marketplace.search(query)

    def marketplace_install(self, plugin_id: str) -> bool:
        success = self.marketplace.install_from_marketplace(plugin_id)
        if success:
            plugin = self.marketplace.get_plugin(plugin_id)
            if plugin:
                self.discover()
                manifest = self.registry.get_by_name(plugin.name)
                if manifest:
                    self.lifecycle.load(str(manifest.id))
                    self.lifecycle.activate(str(manifest.id))
                else:
                    # Convert string permissions to PluginPermission enum
                    perms = []
                    for p in plugin.permissions:
                        try:
                            perms.append(PluginPermission(p))
                        except ValueError:
                            logger.warning(f"Unknown permission '{p}' for plugin {plugin.name}")
                    manifest = PluginManifest(
                        name=plugin.name,
                        version=plugin.version,
                        description=plugin.description,
                        author=plugin.author,
                        source="marketplace",
                        permissions=perms,
                    )
                    self.lifecycle.install(manifest)
                    self.lifecycle.load(str(manifest.id))
                    self.lifecycle.activate(str(manifest.id))
            return True
        return False
