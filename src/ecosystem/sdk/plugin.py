"""
Ecosystem Platform – SDK: Base plugin interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum


class PluginHealth(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class JarvisPlugin(ABC):
    """
    Base interface for all Jarvis plugins.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass

    @property
    @abstractmethod
    def author(self) -> str:
        """Plugin author."""
        pass

    @property
    def dependencies(self) -> List[str]:
        """List of plugin dependencies."""
        return []

    @property
    def permissions(self) -> List[str]:
        """List of required permissions."""
        return []

    @property
    def capabilities(self) -> List[Dict[str, Any]]:
        """List of capabilities provided by this plugin."""
        return []

    def initialize(self) -> None:
        """
        Called when the plugin is activated.
        Override to perform setup tasks.
        """
        pass

    def shutdown(self) -> None:
        """
        Called when the plugin is deactivated.
        Override to perform cleanup tasks.
        """
        pass

    def health(self) -> PluginHealth:
        """
        Called periodically to check plugin health.
        Override to provide custom health checks.
        """
        return PluginHealth.HEALTHY
