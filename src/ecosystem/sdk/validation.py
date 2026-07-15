"""
Ecosystem Platform – SDK: Plugin validation.
"""

import os
import json
import logging
from typing import List, Optional

from src.ecosystem.models import PluginManifest

logger = logging.getLogger(__name__)


class PluginValidator:
    """
    Validates plugin structure, manifest, and compatibility.
    """

    @staticmethod
    def validate_manifest(manifest: dict) -> List[str]:
        """Validate a plugin manifest."""
        errors = []
        required_fields = ["name", "version", "description", "author"]
        for field in required_fields:
            if field not in manifest:
                errors.append(f"Missing required field: {field}")
        if "name" in manifest and not manifest["name"]:
            errors.append("Name cannot be empty")
        if "version" in manifest and not manifest["version"]:
            errors.append("Version cannot be empty")
        return errors

    @staticmethod
    def validate_plugin_path(path: str) -> List[str]:
        """Validate a plugin directory."""
        errors = []
        if not os.path.exists(path):
            errors.append(f"Path does not exist: {path}")
            return errors
        if not os.path.isdir(path):
            errors.append(f"Path is not a directory: {path}")
            return errors

        manifest_path = os.path.join(path, "manifest.json")
        if not os.path.exists(manifest_path):
            errors.append("manifest.json not found")
            return errors

        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            errors.extend(PluginValidator.validate_manifest(manifest))
        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON in manifest: {e}")

        return errors

    @staticmethod
    def validate_compatibility(manifest: PluginManifest, jarvis_version: str = "1.0.0") -> bool:
        """Validate plugin compatibility with Jarvis version."""
        return manifest.jarvis_version == jarvis_version
