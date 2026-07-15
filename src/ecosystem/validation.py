"""
Ecosystem Platform – Plugin validation tools.
"""

import os
import json
import logging
from typing import List, Dict, Any
from src.ecosystem.models import PluginManifest

logger = logging.getLogger(__name__)


class PluginValidator:
    """
    Validates plugin structure and manifest.
    """

    def __init__(self, plugin_path: str = "plugins"):
        self.plugin_path = plugin_path

    def validate_manifest(self, manifest: PluginManifest) -> List[str]:
        """Validate a plugin manifest."""
        errors = []
        if not manifest.name:
            errors.append("Plugin name is required")
        if not manifest.version:
            errors.append("Plugin version is required")
        if not manifest.description:
            errors.append("Plugin description is required")
        if not manifest.author:
            errors.append("Plugin author is required")
        if not manifest.jarvis_version:
            errors.append("Jarvis version is required")
        return errors

    def validate_plugin(self, name: str) -> List[str]:
        """Validate a plugin's directory structure and files."""
        errors = []
        plugin_dir = os.path.join(self.plugin_path, name)
        if not os.path.exists(plugin_dir):
            errors.append(f"Plugin directory {plugin_dir} not found")
            return errors

        # Check manifest.json
        manifest_path = os.path.join(plugin_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            errors.append("manifest.json not found")
        else:
            try:
                with open(manifest_path, 'r') as f:
                    data = json.load(f)
                required = ["name", "version", "description", "author"]
                for field in required:
                    if field not in data:
                        errors.append(f"Missing field '{field}' in manifest.json")
            except Exception as e:
                errors.append(f"Invalid manifest.json: {e}")

        # Check __init__.py (optional)
        init_path = os.path.join(plugin_dir, "__init__.py")
        if not os.path.exists(init_path):
            errors.append("No __init__.py found; plugin may not be loadable as a module")

        # Check README.md (optional)
        readme_path = os.path.join(plugin_dir, "README.md")
        if not os.path.exists(readme_path):
            errors.append("No README.md found (recommended)")

        return errors

    def validate_all(self) -> Dict[str, List[str]]:
        """Validate all plugins in the plugin_path."""
        results = {}
        if not os.path.exists(self.plugin_path):
            return results
        for entry in os.listdir(self.plugin_path):
            if os.path.isdir(os.path.join(self.plugin_path, entry)):
                results[entry] = self.validate_plugin(entry)
        return results
