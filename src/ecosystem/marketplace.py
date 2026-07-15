"""
Ecosystem Platform – Marketplace client for remote plugin discovery and installation.
"""

import json
import os
import logging
import requests
import tempfile
import zipfile
import shutil
from typing import List, Optional

from src.ecosystem.models import PluginPackage

logger = logging.getLogger(__name__)


class MarketplaceClient:
    """
    Client for interacting with a remote marketplace registry (GitHub-based).
    """

    def __init__(self, registry_url: Optional[str] = None):
        # Default to a public registry; user can override with env var or config.
        self.registry_url = registry_url or os.getenv(
            "JARVIS_MARKETPLACE_URL",
            "https://raw.githubusercontent.com/jarvis-community/marketplace/main/marketplace.json"
        )
        self._cache: Optional[List[PluginPackage]] = None

    def _fetch_registry(self) -> List[PluginPackage]:
        """Fetch the marketplace registry JSON."""
        if self._cache is not None:
            return self._cache
        try:
            resp = requests.get(self.registry_url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            plugins = []
            for item in data.get("plugins", []):
                plugins.append(PluginPackage(**item))
            self._cache = plugins
            logger.info(f"[Marketplace] Fetched {len(plugins)} plugins from registry.")
            return plugins
        except Exception as e:
            logger.error(f"[Marketplace] Failed to fetch registry: {e}")
            return []

    def search(self, query: str = "") -> List[PluginPackage]:
        """Search the marketplace for plugins matching the query."""
        plugins = self._fetch_registry()
        if not query:
            return plugins
        q = query.lower()
        return [p for p in plugins if q in p.name.lower() or q in p.description.lower()]

    def get_plugin(self, plugin_id: str) -> Optional[PluginPackage]:
        """Get a specific plugin by ID from the marketplace."""
        for p in self._fetch_registry():
            if p.id == plugin_id:
                return p
        return None

    def install_from_marketplace(self, plugin_id: str) -> bool:
        """
        Download a plugin from the marketplace and install it.
        (Renamed from download_and_install for compatibility with manager)
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            logger.error(f"Plugin {plugin_id} not found in marketplace.")
            return False

        download_url = plugin.download_url
        if not download_url:
            logger.error(f"Plugin {plugin_id} has no download URL.")
            return False

        try:
            # Download the plugin archive
            resp = requests.get(download_url, stream=True, timeout=30)
            resp.raise_for_status()

            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            # Extract to plugins directory
            plugin_path = "plugins"
            target_dir = os.path.join(plugin_path, plugin.name)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            os.makedirs(target_dir, exist_ok=True)

            with zipfile.ZipFile(tmp_path, 'r') as zip_ref:
                zip_ref.extractall(target_dir)

            # Clean up temp file
            os.unlink(tmp_path)

            logger.info(f"[Marketplace] Installed plugin {plugin.name} from marketplace.")
            return True
        except Exception as e:
            logger.error(f"[Marketplace] Failed to install plugin {plugin.name}: {e}")
            return False
