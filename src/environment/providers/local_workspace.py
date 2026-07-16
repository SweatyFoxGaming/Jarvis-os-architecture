"""
Environment Platform – Local Workspace provider.
Provides awareness of the user's current desktop environment.
"""

import os
import logging
import subprocess
from typing import Dict, Any, List, Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import pyperclip
    PYPERCLIP_AVAILABLE = True
except ImportError:
    PYPERCLIP_AVAILABLE = False

from src.environment.providers.base import EnvironmentProvider
from src.environment.models import ProviderHealth, ProviderMetadata, Domain, EnvironmentProviderCapability

logger = logging.getLogger(__name__)


class LocalWorkspaceProvider(EnvironmentProvider):
    """
    Provides information about the user's workspace.
    Supports: active window, current application, clipboard, running processes.
    """

    def __init__(self, secure_memory=None):
        self.secure_memory = secure_memory
        self._health = ProviderHealth.LOADING
        self._initialized = False

    def initialize(self) -> None:
        self._health = ProviderHealth.AVAILABLE
        self._initialized = True
        logger.info("[LocalWorkspaceProvider] Initialized.")

    def shutdown(self) -> None:
        self._health = ProviderHealth.OFFLINE
        self._initialized = False
        logger.info("[LocalWorkspaceProvider] Shut down.")

    def health(self) -> ProviderHealth:
        return self._health

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="local_workspace",
            domain=Domain.WORKSPACE,
            version="1.0.0",
            author="Jarvis Core Team",
            description="Provides workspace awareness (active window, clipboard, processes).",
            capabilities=[
                EnvironmentProviderCapability(
                    name="status",
                    description="Get comprehensive workspace status",
                    parameters={},
                    returns={"workspace": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="active_window",
                    description="Get the active window title and application",
                    parameters={},
                    returns={"title": {"type": "string"}, "application": {"type": "string"}}
                ),
                EnvironmentProviderCapability(
                    name="clipboard",
                    description="Get the current clipboard content",
                    parameters={},
                    returns={"clipboard": {"type": "string"}}
                ),
                EnvironmentProviderCapability(
                    name="processes",
                    description="List running processes (filtered)",
                    parameters={"limit": {"type": "integer"}},
                    returns={"processes": {"type": "array"}}
                ),
                EnvironmentProviderCapability(
                    name="current_directory",
                    description="Get the current working directory",
                    parameters={},
                    returns={"cwd": {"type": "string"}}
                ),
            ]
        )

    def capabilities(self) -> List[str]:
        return ["status", "active_window", "clipboard", "processes", "current_directory"]

    def _get_active_window(self) -> Dict[str, str]:
        """
        Attempt to get active window title and application.
        Tries xdotool first (Linux X11), then falls back to psutil.
        """
        # Try xdotool (Linux X11)
        try:
            # Get active window ID
            result = subprocess.run(
                ['xdotool', 'getactivewindow'],
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                window_id = result.stdout.strip()
                # Get window title
                title_result = subprocess.run(
                    ['xdotool', 'getwindowname', window_id],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                title = title_result.stdout.strip() if title_result.returncode == 0 else "Unknown"
                # Get window class/application
                class_result = subprocess.run(
                    ['xdotool', 'getwindowclassname', window_id],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                app = class_result.stdout.strip().split('\n')[0] if class_result.returncode == 0 else "Unknown"
                return {"title": title, "application": app}
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"xdotool not available or failed: {e}")

        # Fallback: try psutil to get current process
        if PSUTIL_AVAILABLE:
            try:
                # Get the process that owns the current terminal (approximate)
                # Alternatively, we can try to get the foreground process using psutil on Linux
                # But it's not straightforward; we'll just return a placeholder
                pass
            except Exception:
                pass

        # Fallback: return environment info
        return {
            "title": os.getenv("TERM", "Terminal"),
            "application": "Terminal"
        }

    def _get_clipboard(self) -> str:
        if PYPERCLIP_AVAILABLE:
            try:
                return pyperclip.paste()
            except Exception:
                pass
        return "Clipboard not accessible (pyperclip not installed or no X11)"

    def _get_processes(self, limit: int = 20) -> List[Dict]:
        processes = []
        if PSUTIL_AVAILABLE:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        processes.append({
                            "pid": proc.info['pid'],
                            "name": proc.info['name'],
                            "cmdline": ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                # Sort by CPU or memory? Just sort by name for now.
                processes = sorted(processes, key=lambda x: x['name'])[:limit]
            except Exception as e:
                logger.error(f"Failed to get processes: {e}")
        else:
            processes = [{"error": "psutil not installed"}]
        return processes

    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Provider not initialized"}

        try:
            if capability == "status":
                return {
                    "workspace": {
                        "active_window": self._get_active_window(),
                        "clipboard": self._get_clipboard(),
                        "cwd": os.getcwd(),
                        "processes": self._get_processes(limit=10),
                    }
                }

            elif capability == "active_window":
                return self._get_active_window()

            elif capability == "clipboard":
                return {"clipboard": self._get_clipboard()}

            elif capability == "processes":
                limit = params.get('limit', 20)
                return {"processes": self._get_processes(limit)}

            elif capability == "current_directory":
                return {"cwd": os.getcwd()}

            else:
                return {"error": f"Unknown capability: {capability}"}

        except Exception as e:
            logger.error(f"[LocalWorkspaceProvider] Error executing {capability}: {e}", exc_info=True)
            return {"error": str(e)}
