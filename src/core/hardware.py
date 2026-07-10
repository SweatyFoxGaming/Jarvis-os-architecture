"""
Hardware detection and optimization module for Phoenix OS.

Provides:
- Real‑time hardware detection (CPU, RAM, OS, GPU)
- Optimized settings based on hardware and environment variables
- Audit logging to secure memory (optional)
"""

import os
import logging
import platform
import multiprocessing
from typing import Dict, Any, Optional

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

# Logger
logger = logging.getLogger(__name__)


class HardwareManager:
    """
    Hardware detection and optimization manager.
    Provides static methods to detect hardware and return optimized settings.
    Now with logging, exception handling, and optional audit logging.
    """

    @staticmethod
    def set_secure_memory(secure_memory: SecureMemoryStore) -> None:
        """
        Inject secure memory for audit logging (global for the class).
        """
        HardwareManager._secure_memory = secure_memory
        logger.info("[HardwareManager] SecureMemoryStore attached.")

    @staticmethod
    def set_secure_runner(secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        HardwareManager._secure_runner = secure_runner
        logger.info("[HardwareManager] SecureCommandRunner attached.")

    # Class-level storage for secure components
    _secure_memory: Optional[SecureMemoryStore] = None
    _secure_runner: Optional[SecureCommandRunner] = None

    @staticmethod
    def detect_hardware() -> Dict[str, Any]:
        """
        Detect hardware capabilities: OS, CPU, RAM, GPU (if possible).

        Returns:
            Dictionary containing hardware information.

        Raises:
            Exception: If detection fails (caught internally and logged).
        """
        logger.info("[HardwareManager] Detecting hardware...")

        try:
            # Basic system info
            info = {
                "os": platform.system(),
                "os_release": platform.release(),
                "cpu_count": multiprocessing.cpu_count(),
                "architecture": platform.machine(),
                "processor": platform.processor() or "Unknown",
            }

            # RAM info using psutil (fallback if not installed)
            try:
                import psutil
                mem = psutil.virtual_memory()
                info["ram_total_gb"] = round(mem.total / (1024 ** 3), 2)
                info["ram_available_gb"] = round(mem.available / (1024 ** 3), 2)
            except ImportError:
                logger.warning("psutil not installed. RAM detection unavailable.")
                info["ram_total_gb"] = 4.0  # fallback
                info["ram_available_gb"] = 2.0

            # GPU detection (optional, try subprocess)
            try:
                import subprocess
                if platform.system() == "Linux":
                    # Try lspci
                    result = subprocess.run(
                        ["lspci"], capture_output=True, text=True, timeout=2
                    )
                    if "NVIDIA" in result.stdout:
                        info["gpu"] = "NVIDIA (detected via lspci)"
                    elif "AMD" in result.stdout:
                        info["gpu"] = "AMD (detected via lspci)"
                    else:
                        info["gpu"] = "Unknown (no discrete GPU found)"
                elif platform.system() == "Windows":
                    # Could use wmic, but skip for simplicity
                    info["gpu"] = "Windows GPU detection not implemented"
                else:
                    info["gpu"] = "Unknown"
            except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
                logger.debug(f"GPU detection failed: {e}")
                info["gpu"] = "Not detected (lspci/wmic unavailable)"

            logger.info(f"[HardwareManager] Detection complete: {info}")
            return info

        except Exception as e:
            logger.error(f"[HardwareManager] Hardware detection failed: {e}", exc_info=True)
            # Return minimal fallback
            return {
                "os": platform.system(),
                "cpu_count": 2,
                "ram_total_gb": 4.0,
                "ram_available_gb": 2.0,
                "gpu": "Unknown (detection failed)",
            }

    @staticmethod
    def get_optimized_settings(hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute optimized LLM settings based on hardware and environment variables.

        Args:
            hardware_info: Dictionary from detect_hardware().

        Returns:
            Settings dictionary with keys: threads, batch_size, context_window,
            model_quantization, and optionally others.

        Overrides via environment variables (prefixed with HARDWARE_):
            - HARDWARE_THREADS
            - HARDWARE_BATCH_SIZE
            - HARDWARE_CONTEXT_WINDOW
            - HARDWARE_MODEL_QUANTIZATION
        """
        ram_gb = hardware_info.get("ram_total_gb", 4.0)
        cpu_count = hardware_info.get("cpu_count", 2)

        # Base settings
        settings = {
            "threads": max(1, cpu_count - 1),  # leave one core for system
            "batch_size": 512,
            "context_window": 2048,
        }

        # Adjust based on RAM
        if ram_gb <= 2:
            settings["context_window"] = 1024
            settings["model_quantization"] = "Q4_K_M"
            settings["batch_size"] = 256
            logger.info("[HardwareManager] Low RAM (<2GB) → small context and quantization.")
        elif ram_gb <= 4:
            settings["context_window"] = 2048
            settings["model_quantization"] = "Q4_K_M"
            logger.info("[HardwareManager] Medium RAM (2-4GB) → standard settings.")
        else:
            settings["context_window"] = 4096
            settings["model_quantization"] = "Q8_0"
            settings["batch_size"] = 1024
            logger.info("[HardwareManager] High RAM (>4GB) → large context and high quantization.")

        # Apply environment overrides
        env_overrides = {
            "threads": os.getenv("HARDWARE_THREADS"),
            "batch_size": os.getenv("HARDWARE_BATCH_SIZE"),
            "context_window": os.getenv("HARDWARE_CONTEXT_WINDOW"),
            "model_quantization": os.getenv("HARDWARE_MODEL_QUANTIZATION"),
        }

        for key, value in env_overrides.items():
            if value is not None:
                try:
                    if key in ("threads", "batch_size", "context_window"):
                        settings[key] = int(value)
                    else:
                        settings[key] = value
                    logger.info(f"[HardwareManager] Override: {key} = {settings[key]} (from env)")
                except ValueError:
                    logger.warning(f"[HardwareManager] Invalid integer for {key}='{value}' — ignored.")

        # Audit log (if secure memory is available)
        if HardwareManager._secure_memory:
            try:
                HardwareManager._secure_memory.insert(
                    text=f"HARDWARE_SETTINGS: {settings}",
                    metadata={
                        "type": "hardware_settings",
                        "ram_gb": ram_gb,
                        "cpu_count": cpu_count,
                        "settings": settings.copy(),
                    },
                )
            except Exception as e:
                logger.warning(f"[HardwareManager] Failed to audit log settings: {e}")

        logger.info(f"[HardwareManager] Final optimized settings: {settings}")
        return settings

    @staticmethod
    def get_profile_summary(hardware_info: Dict[str, Any]) -> str:
        """Return a human-readable summary of the hardware profile."""
        cpu = hardware_info.get("cpu_count", "?")
        ram = hardware_info.get("ram_total_gb", "?")
        gpu = hardware_info.get("gpu", "Unknown")
        return f"CPU: {cpu} cores, RAM: {ram} GB, GPU: {gpu}"

    @staticmethod
    def shutdown() -> None:
        """Clean up resources (close secure memory if used)."""
        logger.info("[HardwareManager] Shutting down.")
        if HardwareManager._secure_memory and hasattr(HardwareManager._secure_memory, 'close'):
            try:
                HardwareManager._secure_memory.close()
            except Exception as e:
                logger.warning(f"[HardwareManager] Error closing secure memory: {e}")
        HardwareManager._secure_memory = None
        HardwareManager._secure_runner = None
