"""
Ecosystem Platform – Security Sandbox for plugins.
Enforces permissions and restricts access to sensitive resources.
"""

import os
import logging
from typing import List, Optional, Dict, Any, Callable
from src.ecosystem.models import PluginPermission, PluginManifest

logger = logging.getLogger(__name__)


class PermissionDenied(Exception):
    """Raised when a plugin attempts an operation without the required permission."""
    pass


class PluginSandbox:
    """
    Sandbox that enforces plugin permissions.
    Each plugin is assigned a set of permissions from its manifest.
    """

    def __init__(self, manifest: Optional[PluginManifest] = None):
        self.manifest = manifest
        self.permissions: List[PluginPermission] = []
        if manifest:
            self.permissions = manifest.permissions

    def set_manifest(self, manifest: PluginManifest) -> None:
        """Set or update the plugin manifest."""
        self.manifest = manifest
        self.permissions = manifest.permissions

    def check_permission(self, permission: PluginPermission) -> bool:
        """Check if a permission is granted."""
        return permission in self.permissions

    def require(self, permission: PluginPermission) -> None:
        """Raise PermissionDenied if the permission is not granted."""
        if not self.check_permission(permission):
            raise PermissionDenied(
                f"Plugin {self.manifest.name if self.manifest else 'unknown'} "
                f"does not have permission: {permission.value}"
            )

    def require_any(self, permissions: List[PluginPermission]) -> None:
        """Require at least one of the listed permissions."""
        for p in permissions:
            if self.check_permission(p):
                return
        raise PermissionDenied(
            f"Plugin {self.manifest.name if self.manifest else 'unknown'} "
            f"requires one of: {[p.value for p in permissions]}"
        )

    def require_all(self, permissions: List[PluginPermission]) -> None:
        """Require all of the listed permissions."""
        for p in permissions:
            self.require(p)

    # ---------- Domain‑specific permission checks ----------

    def filesystem_read(self, path: str) -> None:
        """Check filesystem read permission."""
        self.require(PluginPermission.FILESYSTEM)

    def filesystem_write(self, path: str) -> None:
        """Check filesystem write permission."""
        self.require(PluginPermission.FILESYSTEM)

    def network_access(self, url: str = "") -> None:
        """Check network permission."""
        self.require(PluginPermission.NETWORK)

    def terminal_access(self) -> None:
        """Check terminal permission."""
        self.require(PluginPermission.TERMINAL)

    def clipboard_read(self) -> None:
        """Check clipboard read permission."""
        self.require(PluginPermission.CLIPBOARD)

    def clipboard_write(self) -> None:
        """Check clipboard write permission."""
        self.require(PluginPermission.CLIPBOARD)

    def environment_read(self, key: str) -> None:
        """Check environment read permission."""
        self.require(PluginPermission.ENVIRONMENT)

    def environment_write(self, key: str) -> None:
        """Check environment write permission."""
        self.require(PluginPermission.ENVIRONMENT)

    def calendar_access(self) -> None:
        """Check calendar permission."""
        self.require(PluginPermission.CALENDAR)

    def email_access(self) -> None:
        """Check email permission."""
        self.require(PluginPermission.EMAIL)

    def browser_access(self) -> None:
        """Check browser permission."""
        self.require(PluginPermission.BROWSER)

    def notifications_access(self) -> None:
        """Check notifications permission."""
        self.require(PluginPermission.NOTIFICATIONS)

    def devices_access(self) -> None:
        """Check devices permission."""
        self.require(PluginPermission.DEVICES)

    # ---------- Function Wrapper ----------
    def wrap(self, func: Callable, required_permission: PluginPermission) -> Callable:
        """Wrap a function with a permission check."""
        def wrapper(*args, **kwargs):
            self.require(required_permission)
            return func(*args, **kwargs)
        return wrapper

    # ---------- Context Manager ----------
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
