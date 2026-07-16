"""
Environment Platform – Local Hardware & Network provider.
Provides system hardware and network status.
"""

import os
import logging
import subprocess
import socket
import platform
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from src.environment.providers.base import EnvironmentProvider
from src.environment.models import ProviderHealth, ProviderMetadata, Domain, EnvironmentProviderCapability

logger = logging.getLogger(__name__)


class LocalHardwareProvider(EnvironmentProvider):
    """
    Provides hardware and network information.
    Supports: CPU, memory, disk, battery, network interfaces, connectivity.
    """

    def __init__(self, secure_memory=None):
        self.secure_memory = secure_memory
        self._health = ProviderHealth.LOADING
        self._initialized = False

    def initialize(self) -> None:
        self._health = ProviderHealth.AVAILABLE
        self._initialized = True
        logger.info("[LocalHardwareProvider] Initialized.")

    def shutdown(self) -> None:
        self._health = ProviderHealth.OFFLINE
        self._initialized = False
        logger.info("[LocalHardwareProvider] Shut down.")

    def health(self) -> ProviderHealth:
        return self._health

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            name="local_hardware",
            domain=Domain.HARDWARE,
            version="1.0.0",
            author="Jarvis Core Team",
            description="Provides hardware and network status.",
            capabilities=[
                EnvironmentProviderCapability(
                    name="status",
                    description="Get comprehensive hardware and network status",
                    parameters={},
                    returns={"hardware": {"type": "object"}, "network": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="cpu",
                    description="Get CPU usage and info",
                    parameters={},
                    returns={"cpu": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="memory",
                    description="Get memory usage",
                    parameters={},
                    returns={"memory": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="disk",
                    description="Get disk usage for a path",
                    parameters={"path": {"type": "string"}},
                    returns={"disk": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="battery",
                    description="Get battery status (if available)",
                    parameters={},
                    returns={"battery": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="network",
                    description="Get network interfaces and connectivity",
                    parameters={},
                    returns={"network": {"type": "object"}}
                ),
                EnvironmentProviderCapability(
                    name="ping",
                    description="Ping a host to check connectivity",
                    parameters={"host": {"type": "string"}},
                    returns={"ping": {"type": "object"}}
                ),
            ]
        )

    def capabilities(self) -> List[str]:
        return ["status", "cpu", "memory", "disk", "battery", "network", "ping"]

    def _get_cpu_info(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not installed"}
        try:
            return {
                "percent": psutil.cpu_percent(interval=0.5),
                "count": psutil.cpu_count(),
                "count_logical": psutil.cpu_count(logical=True),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_memory_info(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not installed"}
        try:
            mem = psutil.virtual_memory()
            return {
                "total": mem.total,
                "available": mem.available,
                "used": mem.used,
                "percent": mem.percent,
                "swap": psutil.swap_memory()._asdict() if psutil.swap_memory() else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_disk_info(self, path: str = "/") -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not installed"}
        try:
            disk = psutil.disk_usage(path)
            return {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
                "path": path,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_battery_info(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not installed"}
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return {"available": False}
            return {
                "available": True,
                "percent": battery.percent,
                "secsleft": battery.secsleft,
                "power_plugged": battery.power_plugged,
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_network_info(self) -> Dict[str, Any]:
        if not PSUTIL_AVAILABLE:
            return {"error": "psutil not installed"}
        try:
            interfaces = []
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    interfaces.append({
                        "name": iface,
                        "family": str(addr.family),
                        "address": addr.address,
                        "netmask": addr.netmask,
                        "broadcast": addr.broadcast,
                    })
            stats = []
            for iface, stat in psutil.net_if_stats().items():
                stats.append({
                    "name": iface,
                    "is_up": stat.isup,
                    "speed": stat.speed,
                    "mtu": stat.mtu,
                })
            return {
                "interfaces": interfaces,
                "stats": stats,
                "hostname": socket.gethostname(),
                "default_gateway": self._get_default_gateway(),
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_default_gateway(self) -> Optional[str]:
        try:
            # Linux: read /proc/net/route
            with open('/proc/net/route', 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts[1] == '00000000':  # default gateway
                        import binascii
                        gateway_hex = parts[2]
                        gateway_bytes = binascii.unhexlify(gateway_hex)
                        gateway_ip = '.'.join(str(b) for b in gateway_bytes[:4])
                        return gateway_ip
        except:
            pass
        return None

    def _ping(self, host: str, count: int = 4) -> Dict[str, Any]:
        try:
            # Use ping command
            cmd = ['ping', '-c', str(count), host]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return {
                "host": host,
                "count": count,
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def execute(self, capability: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._initialized:
            return {"error": "Provider not initialized"}

        try:
            if capability == "status":
                return {
                    "hardware": {
                        "cpu": self._get_cpu_info(),
                        "memory": self._get_memory_info(),
                        "disk": self._get_disk_info(params.get('path', '/')),
                        "battery": self._get_battery_info(),
                    },
                    "network": self._get_network_info(),
                }

            elif capability == "cpu":
                return {"cpu": self._get_cpu_info()}

            elif capability == "memory":
                return {"memory": self._get_memory_info()}

            elif capability == "disk":
                path = params.get('path', '/')
                return {"disk": self._get_disk_info(path)}

            elif capability == "battery":
                return {"battery": self._get_battery_info()}

            elif capability == "network":
                return {"network": self._get_network_info()}

            elif capability == "ping":
                host = params.get('host')
                if not host:
                    return {"error": "Missing 'host' parameter"}
                return {"ping": self._ping(host)}

            else:
                return {"error": f"Unknown capability: {capability}"}

        except Exception as e:
            logger.error(f"[LocalHardwareProvider] Error executing {capability}: {e}", exc_info=True)
            return {"error": str(e)}
