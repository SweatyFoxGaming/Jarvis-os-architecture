"""
Ecosystem Platform – Entry point.
"""

from src.ecosystem.manager import EcosystemManager
from src.ecosystem.models import PluginManifest, PluginState, HealthStatus, PluginCapability, PluginPermission, PluginPackage

__all__ = [
    "EcosystemManager",
    "PluginManifest",
    "PluginState",
    "HealthStatus",
    "PluginCapability",
    "PluginPermission",
    "PluginPackage",
]
