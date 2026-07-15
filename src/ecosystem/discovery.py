"""
Ecosystem Platform – Discovery Engine.
"""

import os
import json
import logging
import importlib.util
from typing import List, Optional
from pathlib import Path

from src.ecosystem.models import PluginManifest, PluginState

logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """
    Discovers plugins from various sources.
    """

    def __init__(self, plugin_path: str = "plugins"):
        self.plugin_path = plugin_path

    def discover_local(self) -> List[PluginManifest]:
        """Discover plugins in the local plugins directory."""
        manifests = []
        if not os.path.exists(self.plugin_path):
            return manifests

        for entry in os.listdir(self.plugin_path):
            dir_path = os.path.join(self.plugin_path, entry)
            if os.path.isdir(dir_path):
                manifest_path = os.path.join(dir_path, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r') as f:
                            data = json.load(f)
                        manifest = PluginManifest(
                            name=data.get('name', entry),
                            version=data.get('version', '1.0.0'),
                            description=data.get('description', ''),
                            author=data.get('author', 'Unknown'),
                            homepage=data.get('homepage'),
                            license=data.get('license'),
                            jarvis_version=data.get('jarvis_version', '1.0.0'),
                            dependencies=data.get('dependencies', []),
                            permissions=data.get('permissions', []),
                            capabilities=data.get('capabilities', []),
                            providers=data.get('providers', []),
                            source="local",
                            state=PluginState.DISCOVERED,
                        )
                        manifests.append(manifest)
                        logger.info(f"[Discovery] Discovered local plugin: {entry}")
                    except Exception as e:
                        logger.error(f"[Discovery] Failed to parse manifest for {entry}: {e}")
                else:
                    # Treat directory as a simple plugin with default metadata
                    manifest = PluginManifest(
                        name=entry,
                        version="1.0.0",
                        description=f"Plugin {entry}",
                        author="Unknown",
                        source="local",
                        state=PluginState.DISCOVERED,
                    )
                    manifests.append(manifest)
                    logger.info(f"[Discovery] Discovered local plugin (default): {entry}")

        return manifests

    def discover_package(self, package_name: str) -> Optional[PluginManifest]:
        """Discover a plugin installed as a Python package."""
        try:
            spec = importlib.util.find_spec(package_name)
            if spec is None:
                return None
            import importlib.metadata
            metadata = importlib.metadata.metadata(package_name)
            manifest = PluginManifest(
                name=metadata.get('Name', package_name),
                version=metadata.get('Version', '1.0.0'),
                description=metadata.get('Summary', ''),
                author=metadata.get('Author', 'Unknown'),
                homepage=metadata.get('Home-page'),
                license=metadata.get('License'),
                source="package",
                state=PluginState.DISCOVERED,
            )
            logger.info(f"[Discovery] Discovered package plugin: {package_name}")
            return manifest
        except Exception as e:
            logger.debug(f"[Discovery] Failed to discover package {package_name}: {e}")
            return None

    def discover_all(self) -> List[PluginManifest]:
        """Discover plugins from all sources."""
        all_manifests = []
        all_manifests.extend(self.discover_local())
        # Add package discovery later
        return all_manifests
