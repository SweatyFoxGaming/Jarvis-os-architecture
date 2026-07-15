"""
Ecosystem Platform – Plugin Lifecycle Management.
"""

import os
import logging
import importlib
import sys
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from src.ecosystem.models import PluginManifest, PluginState, HealthStatus
from src.ecosystem.registry import PluginRegistry
from src.ecosystem.discovery import DiscoveryEngine

logger = logging.getLogger(__name__)


class PluginLifecycle:
    """
    Manages plugin lifecycle: install, load, activate, update, deactivate, remove.
    """

    def __init__(self, registry: PluginRegistry, discovery: DiscoveryEngine, plugin_path: str = "plugins", event_bus=None):
        self.registry = registry
        self.discovery = discovery
        self.plugin_path = plugin_path
        self.event_bus = event_bus
        self.loaded_plugins: Dict[str, Any] = {}

    def _publish_event(self, event_type: str, payload: dict) -> None:
        if self.event_bus:
            try:
                from src.core.models import Event
                event = Event(event_type=event_type, source="PluginLifecycle", payload=payload)
                self.event_bus.publish(event)
            except Exception as e:
                logger.warning(f"Failed to publish event {event_type}: {e}")

    def install(self, manifest: PluginManifest) -> bool:
        if self.registry.get_by_name(manifest.name):
            logger.warning(f"Plugin {manifest.name} already installed.")
            return False
        manifest.state = PluginState.INSTALLED
        manifest.installed_at = datetime.now()
        self.registry.register(manifest)
        self._publish_event("PluginInstalled", {"id": str(manifest.id), "name": manifest.name})
        logger.info(f"Installed plugin: {manifest.name}")
        return True

    def load(self, plugin_id: str) -> bool:
        try:
            uid = UUID(plugin_id)
        except ValueError:
            logger.error(f"Invalid plugin ID: {plugin_id}")
            return False
        manifest = self.registry.get(uid)
        if not manifest:
            logger.error(f"Plugin {plugin_id} not found.")
            return False
        if manifest.state in (PluginState.LOADED, PluginState.ACTIVE):
            logger.info(f"Plugin {manifest.name} already loaded.")
            return True

        # Check if plugin directory exists and contains a Python module
        plugin_dir = os.path.join(self.plugin_path, manifest.name)
        has_module = os.path.exists(os.path.join(plugin_dir, "__init__.py"))

        if has_module:
            try:
                module_name = f"{self.plugin_path}.{manifest.name}"
                module = importlib.import_module(module_name)
                self.loaded_plugins[manifest.name] = module
                self.registry.update_state(uid, PluginState.LOADED)
                self._publish_event("PluginLoaded", {"id": str(uid), "name": manifest.name})
                logger.info(f"Loaded plugin: {manifest.name}")
                return True
            except Exception as e:
                logger.error(f"Failed to load plugin {manifest.name}: {e}")
                self.registry.update_state(uid, PluginState.FAILED)
                return False
        else:
            # No module, treat as loaded (metadata-only plugin)
            self.loaded_plugins[manifest.name] = None
            self.registry.update_state(uid, PluginState.LOADED)
            logger.info(f"Loaded plugin (no module): {manifest.name}")
            return True

    def activate(self, plugin_id: str) -> bool:
        try:
            uid = UUID(plugin_id)
        except ValueError:
            logger.error(f"Invalid plugin ID: {plugin_id}")
            return False
        manifest = self.registry.get(uid)
        if not manifest:
            logger.error(f"Plugin {plugin_id} not found.")
            return False
        if manifest.state == PluginState.ACTIVE:
            logger.info(f"Plugin {manifest.name} already active.")
            return True
        # If installed but not loaded, load it first
        if manifest.state == PluginState.INSTALLED:
            if not self.load(plugin_id):
                return False
        if manifest.state not in (PluginState.LOADED, PluginState.INSTALLED):
            logger.warning(f"Plugin {manifest.name} must be loaded before activation.")
            return False
        try:
            module = self.loaded_plugins.get(manifest.name)
            if module and hasattr(module, "initialize"):
                module.initialize()
            self.registry.update_state(uid, PluginState.ACTIVE)
            self.registry.update_health(uid, HealthStatus.HEALTHY)
            self._publish_event("PluginActivated", {"id": str(uid), "name": manifest.name})
            logger.info(f"Activated plugin: {manifest.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to activate plugin {manifest.name}: {e}")
            self.registry.update_state(uid, PluginState.FAILED)
            self.registry.update_health(uid, HealthStatus.UNHEALTHY)
            return False

    def deactivate(self, plugin_id: str) -> bool:
        try:
            uid = UUID(plugin_id)
        except ValueError:
            logger.error(f"Invalid plugin ID: {plugin_id}")
            return False
        manifest = self.registry.get(uid)
        if not manifest:
            return False
        if manifest.state != PluginState.ACTIVE:
            logger.info(f"Plugin {manifest.name} is not active.")
            return True
        try:
            module = self.loaded_plugins.get(manifest.name)
            if module and hasattr(module, "shutdown"):
                module.shutdown()
            self.registry.update_state(uid, PluginState.INACTIVE)
            self._publish_event("PluginDeactivated", {"id": str(uid), "name": manifest.name})
            logger.info(f"Deactivated plugin: {manifest.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate plugin {manifest.name}: {e}")
            return False

    def update(self, plugin_id: str, new_manifest: PluginManifest) -> bool:
        try:
            uid = UUID(plugin_id)
        except ValueError:
            logger.error(f"Invalid plugin ID: {plugin_id}")
            return False
        manifest = self.registry.get(uid)
        if not manifest:
            return False
        if manifest.state == PluginState.ACTIVE:
            self.deactivate(plugin_id)
        manifest.version = new_manifest.version
        manifest.description = new_manifest.description
        manifest.dependencies = new_manifest.dependencies
        manifest.capabilities = new_manifest.capabilities
        manifest.permissions = new_manifest.permissions
        manifest.updated_at = datetime.now()
        manifest.state = PluginState.UPDATING
        self.registry.register(manifest)
        self.load(plugin_id)
        self.activate(plugin_id)
        self._publish_event("PluginUpdated", {"id": str(uid), "name": manifest.name})
        logger.info(f"Updated plugin: {manifest.name}")
        return True

    def remove(self, plugin_id: str) -> bool:
        try:
            uid = UUID(plugin_id)
        except ValueError:
            logger.error(f"Invalid plugin ID: {plugin_id}")
            return False
        manifest = self.registry.get(uid)
        if not manifest:
            return False
        if manifest.state == PluginState.ACTIVE:
            self.deactivate(plugin_id)
        self.loaded_plugins.pop(manifest.name, None)
        self.registry.update_state(uid, PluginState.REMOVED)
        self._publish_event("PluginRemoved", {"id": str(uid), "name": manifest.name})
        logger.info(f"Removed plugin: {manifest.name}")
        return True

    def health_check(self, plugin_id: str) -> HealthStatus:
        try:
            uid = UUID(plugin_id)
        except ValueError:
            logger.error(f"Invalid plugin ID: {plugin_id}")
            return HealthStatus.UNKNOWN
        manifest = self.registry.get(uid)
        if not manifest:
            return HealthStatus.UNKNOWN
        if manifest.state != PluginState.ACTIVE:
            return HealthStatus.UNKNOWN
        try:
            module = self.loaded_plugins.get(manifest.name)
            if module and hasattr(module, "health"):
                result = module.health()
                if isinstance(result, bool):
                    health = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                else:
                    health = result
            else:
                health = HealthStatus.HEALTHY
            self.registry.update_health(uid, health)
            return health
        except Exception as e:
            logger.error(f"Health check failed for plugin {manifest.name}: {e}")
            self.registry.update_health(uid, HealthStatus.UNHEALTHY)
            return HealthStatus.UNHEALTHY
