import os
import logging
from enum import Enum
from typing import Dict, Any, Optional

# Logger
logger = logging.getLogger(__name__)


class HardwareProfile(Enum):
    """Hardware performance profiles."""
    LOW = "low"
    PERFORMANCE = "performance"

    @classmethod
    def from_env(cls) -> "HardwareProfile":
        """
        Read HARDWARE_PROFILE environment variable and return the corresponding enum member.
        Defaults to LOW if the value is not recognized.
        """
        env_value = os.getenv("HARDWARE_PROFILE", "").strip().lower()
        if env_value == "performance":
            return cls.PERFORMANCE
        elif env_value == "low":
            return cls.LOW
        else:
            if env_value:
                logger.warning(f"Unknown HARDWARE_PROFILE '{env_value}'. Falling back to LOW.")
            return cls.LOW

    def get_settings(self) -> Dict[str, Any]:
        """
        Return the hardware settings dictionary for this profile.
        """
        if self == HardwareProfile.PERFORMANCE:
            return {
                "threads": 4,
                "context_window": 4096,
                "n_ctx": 4096,          # Alias for LLM compatibility
                "n_batch": 512,
                "model_quantization": "Q8_0",
                "semantic_search": True,
                "gpu_layers": 0,        # Default, can be overridden
            }
        else:  # LOW profile
            return {
                "threads": 2,
                "context_window": 2048,
                "n_ctx": 2048,
                "n_batch": 256,
                "model_quantization": "Q4_K_M",
                "semantic_search": False,
                "gpu_layers": 0,
            }


class HardwareManager:
    """
    Hardware detection and optimization manager.
    Provides methods to detect hardware capabilities and get optimized settings.
    Now with logging and robust error handling.
    """

    @staticmethod
    def detect_hardware() -> Dict[str, Any]:
        """
        Detect hardware capabilities (CPU cores, RAM, etc.).
        Returns a dictionary with hardware info.
        If detection fails, returns default values.
        """
        try:
            import psutil
            cpu_count = psutil.cpu_count(logical=True)
            mem = psutil.virtual_memory()
            total_ram_gb = mem.total / (1024 ** 3)

            hardware_info = {
                "cpu_count": cpu_count or 2,
                "total_ram_gb": round(total_ram_gb, 1),
                "available_ram_gb": round(mem.available / (1024 ** 3), 1),
                "platform": os.uname().sysname if hasattr(os, 'uname') else "Unknown",
            }
            logger.info(f"Hardware detected: {hardware_info}")
            return hardware_info

        except ImportError:
            logger.warning("psutil not installed. Hardware detection limited.")
            return {
                "cpu_count": 2,
                "total_ram_gb": 4.0,
                "available_ram_gb": 2.0,
                "platform": "Unknown",
            }
        except Exception as e:
            logger.error(f"Hardware detection failed: {e}", exc_info=True)
            return {
                "cpu_count": 2,
                "total_ram_gb": 4.0,
                "available_ram_gb": 2.0,
                "platform": "Unknown",
            }

    @staticmethod
    def get_optimized_settings(hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Given hardware info, return optimized settings for the LLM.
        This can override the profile-based settings based on actual hardware.
        """
        # Start with profile settings
        profile = HardwareProfile.from_env()
        settings = profile.get_settings()

        # Adjust based on hardware if available
        cpu_count = hardware_info.get("cpu_count", 2)
        ram_gb = hardware_info.get("total_ram_gb", 4.0)

        # If we have enough RAM and CPU, upgrade threads
        if cpu_count >= 4 and ram_gb >= 8:
            settings["threads"] = min(cpu_count, 8)
            settings["n_batch"] = 512
            logger.info(f"Upgraded threads to {settings['threads']} based on hardware.")

        # If very low RAM, reduce context window
        if ram_gb < 4:
            settings["context_window"] = 1024
            settings["n_ctx"] = 1024
            logger.warning("Low RAM detected. Reduced context window to 1024.")

        # Allow environment overrides
        for key in ["threads", "n_ctx", "n_batch", "gpu_layers"]:
            env_key = f"HARDWARE_{key.upper()}"
            if os.getenv(env_key):
                try:
                    settings[key] = int(os.getenv(env_key))
                    logger.info(f"Override: {key} = {settings[key]} from {env_key}")
                except ValueError:
                    logger.warning(f"Invalid integer for {env_key}: {os.getenv(env_key)}")

        return settings

    @staticmethod
    def get_profile() -> HardwareProfile:
        """Return the current hardware profile based on environment."""
        return HardwareProfile.from_env()
