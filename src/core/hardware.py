import psutil
import platform
import multiprocessing
from typing import Dict, Any

class HardwareManager:
    @staticmethod
    def detect_hardware() -> Dict[str, Any]:
        info = {
            "os": platform.system(),
            "os_release": platform.release(),
            "cpu_count": multiprocessing.cpu_count(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "ram_available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
            "architecture": platform.machine(),
            "processor": platform.processor()
        }

        # Simple GPU detection (placeholder for more robust logic)
        try:
            # This is a very basic check, normally would use nvidia-smi or similar
            import subprocess
            if platform.system() == "Linux":
                res = subprocess.check_output(["lspci"]).decode()
                if "NVIDIA" in res:
                    info["gpu"] = "NVIDIA (Detected via lspci)"
                elif "AMD" in res:
                    info["gpu"] = "AMD (Detected via lspci)"
        except:
            pass

        return info

    @staticmethod
    def get_optimized_settings(hardware_info: Dict[str, Any]) -> Dict[str, Any]:
        ram = hardware_info.get("ram_total_gb", 4)
        cpu = hardware_info.get("cpu_count", 2)

        settings = {
            "threads": max(1, cpu - 1),
            "batch_size": 512,
            "context_window": 2048
        }

        if ram <= 2:
            settings["context_window"] = 1024
            settings["model_quantization"] = "Q4_K_M"
        elif ram <= 4:
            settings["context_window"] = 2048
            settings["model_quantization"] = "Q4_K_M"
        else:
            settings["context_window"] = 4096
            settings["model_quantization"] = "Q8_0"

        return settings
