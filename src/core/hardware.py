import os
import logging
from enum import Enum
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

logger = logging.getLogger(__name__)


class HardwareProfile(Enum):
    """Hardware performance profiles."""
    LOW = "low"
    PERFORMANCE = "performance"

    @classmethod
    def from_env(cls) -> "HardwareProfile":
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
        if self == HardwareProfile.PERFORMANCE:
            return {
                "threads": 4,
                "context_window": 4096,
                "n_ctx": 4096,
                "n_batch": 512,
                "model_quantization": "Q8_0",
                "semantic_search": True,
                "gpu_layers": 0,
            }
        else:  # LOW
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
    """Hardware detection and optimization manager."""
    _secure_memory: Optional[SecureMemoryStore] = None
    _secure_runner: Optional[SecureCommandRunner] = None

    @staticmethod
    def set_secure_memory(secure_memory: SecureMemoryStore) -> None:
        HardwareManager._secure_memory = secure_memory
        logger.info("[HardwareManager] SecureMemoryStore attached.")

    @staticmethod
    def set_secure_runner(secure_runner: SecureCommandRunner) -> None:
        HardwareManager._secure_runner = secure_runner
        logger.info("[HardwareManager] SecureCommandRunner attached.")

    @staticmethod
    def detect_hardware() -> Dict[str, Any]:
        logger.info("[HardwareManager] Detecting hardware...")
        try:
            import psutil
            cpu_count = psutil.cpu_count(logical=True)
            mem = psutil.virtual_memory()
            total_ram_gb = mem.total / (1024 ** 3)

            info = {
                "cpu_count": cpu_count or 2,
                "total_ram_gb": round(total_ram_gb, 1),
                "available_ram_gb": round(mem.available / (1024 ** 3), 1),
                "platform": os.uname().sysname if hasattr(os, 'uname') else "Unknown",
            }
            logger.info(f"[HardwareManager] Detection complete: {info}")
            return info
        except ImportError:
            logger.warning("psutil not installed. Hardware detection limited.")
            return {"cpu_count": 2, "total_ram_gb": 4.0, "available_ram_gb": 2.0, "platform": "Unknown"}
        except Exception as e:
            logger.error(f"Hardware detection failed: {e}", exc_info=True)
            return {"cpu_count": 2, "total_ram_gb": 4.0, "available_ram_gb": 2.0, "platform": "Unknown"}

    @staticmethod
    def get_optimized_settings(hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        profile = HardwareProfile.from_env()
        settings = profile.get_settings()

        cpu_count = hardware_info.get("cpu_count", 2)
        ram_gb = hardware_info.get("total_ram_gb", 4.0)

        if cpu_count >= 4 and ram_gb >= 8:
            settings["threads"] = min(cpu_count, 8)
            settings["n_batch"] = 512
            logger.info(f"Upgraded threads to {settings['threads']} based on hardware.")

        if ram_gb < 4:
            settings["context_window"] = 1024
            settings["n_ctx"] = 1024
            logger.warning("Low RAM detected. Reduced context window to 1024.")

        # Environment overrides
        for key in ["threads", "n_ctx", "n_batch", "gpu_layers"]:
            env_key = f"HARDWARE_{key.upper()}"
            if os.getenv(env_key):
                try:
                    settings[key] = int(os.getenv(env_key))
                    logger.info(f"Override: {key} = {settings[key]} from {env_key}")
                except ValueError:
                    logger.warning(f"Invalid integer for {env_key}: {os.getenv(env_key)}")

        if HardwareManager._secure_memory:
            try:
                HardwareManager._secure_memory.insert(
                    text=f"HARDWARE_SETTINGS: {settings}",
                    metadata={"type": "hardware_settings", "settings": settings.copy()},
                )
            except Exception as e:
                logger.warning(f"Failed to audit log settings: {e}")

        logger.info(f"[HardwareManager] Final optimized settings: {settings}")
        return settings

    @staticmethod
    def get_profile() -> HardwareProfile:
        return HardwareProfile.from_env()

    @staticmethod
    def shutdown():
        logger.info("[HardwareManager] Shutting down.")
        if HardwareManager._secure_memory and hasattr(HardwareManager._secure_memory, 'close'):
            try:
                HardwareManager._secure_memory.close()
            except Exception as e:
                logger.warning(f"Error closing secure memory: {e}")
        HardwareManager._secure_memory = None
        HardwareManager._secure_runner = None
