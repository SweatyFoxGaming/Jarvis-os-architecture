"""
Ecosystem Platform – SDK: Plugin testing framework.
"""

import logging
import importlib
import sys
from typing import Optional, Dict, Any

from src.ecosystem.sdk import JarvisPlugin, PluginHealth

logger = logging.getLogger(__name__)


class PluginTestHarness:
    """
    Testing framework for plugins.
    """

    def __init__(self, plugin_path: str):
        self.plugin_path = plugin_path

    def test_plugin(self, plugin_name: str) -> Dict[str, Any]:
        """Test a plugin by importing and initializing it."""
        result = {
            "name": plugin_name,
            "loaded": False,
            "initialized": False,
            "health": PluginHealth.UNHEALTHY,
            "errors": [],
        }

        try:
            # Import the plugin module
            module_name = f"{self.plugin_path}.{plugin_name}"
            module = importlib.import_module(module_name)

            # Check if plugin instance exists
            if not hasattr(module, "plugin"):
                result["errors"].append("No 'plugin' instance found in module")
                return result

            plugin = module.plugin
            if not isinstance(plugin, JarvisPlugin):
                result["errors"].append("Plugin instance does not inherit from JarvisPlugin")
                return result

            result["loaded"] = True

            # Initialize
            try:
                plugin.initialize()
                result["initialized"] = True
            except Exception as e:
                result["errors"].append(f"Initialization failed: {e}")
                return result

            # Check health
            try:
                health = plugin.health()
                result["health"] = health
            except Exception as e:
                result["errors"].append(f"Health check failed: {e}")

            # Shutdown
            try:
                plugin.shutdown()
            except Exception as e:
                result["errors"].append(f"Shutdown failed: {e}")

        except ImportError as e:
            result["errors"].append(f"Import failed: {e}")
        except Exception as e:
            result["errors"].append(f"Unexpected error: {e}")

        return result

    def test_all(self) -> Dict[str, Dict[str, Any]]:
        """Test all plugins in the plugin directory."""
        import os
        results = {}
        if not os.path.exists(self.plugin_path):
            return results
        for item in os.listdir(self.plugin_path):
            path = os.path.join(self.plugin_path, item)
            if os.path.isdir(path):
                results[item] = self.test_plugin(item)
        return results
