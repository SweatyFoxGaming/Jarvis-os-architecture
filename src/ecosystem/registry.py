"""
Ecosystem Platform – Plugin Registry.
"""

import os
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from src.ecosystem.models import PluginManifest, PluginState

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Stores and manages plugin metadata.
    """

    def __init__(self, data_path: str = "data/plugins.json"):
        self.data_path = data_path
        self.plugins: Dict[UUID, PluginManifest] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r') as f:
                    data = json.load(f)
                    for item in data:
                        manifest = PluginManifest(**item)
                        self.plugins[manifest.id] = manifest
                logger.info(f"[PluginRegistry] Loaded {len(self.plugins)} plugins.")
            except Exception as e:
                logger.error(f"[PluginRegistry] Failed to load plugins: {e}")

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        try:
            with open(self.data_path, 'w') as f:
                json.dump([p.model_dump(mode='json') for p in self.plugins.values()], f, indent=2)
        except Exception as e:
            logger.error(f"[PluginRegistry] Failed to save plugins: {e}")

    def register(self, manifest: PluginManifest) -> None:
        self.plugins[manifest.id] = manifest
        self._save()
        logger.info(f"[PluginRegistry] Registered plugin: {manifest.name}")

    def get(self, plugin_id: UUID) -> Optional[PluginManifest]:
        return self.plugins.get(plugin_id)

    def get_by_name(self, name: str) -> Optional[PluginManifest]:
        for p in self.plugins.values():
            if p.name == name:
                return p
        return None

    def list(self, state: Optional[PluginState] = None) -> List[PluginManifest]:
        if state:
            return [p for p in self.plugins.values() if p.state == state]
        return list(self.plugins.values())

    def update_state(self, plugin_id: UUID, state: PluginState) -> bool:
        manifest = self.get(plugin_id)
        if not manifest:
            return False
        manifest.state = state
        manifest.updated_at = datetime.now()
        self._save()
        return True

    def update_health(self, plugin_id: UUID, health: str) -> bool:
        manifest = self.get(plugin_id)
        if not manifest:
            return False
        manifest.health = health
        self._save()
        return True

    def unregister(self, plugin_id: UUID) -> bool:
        if plugin_id not in self.plugins:
            return False
        del self.plugins[plugin_id]
        self._save()
        return True
