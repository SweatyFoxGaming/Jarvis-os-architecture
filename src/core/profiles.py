import os
from enum import Enum

class HardwareProfile(Enum):
    LOW = "low"
    PERFORMANCE = "performance"

    @staticmethod
    def get_settings():
        profile = os.getenv("HARDWARE_PROFILE", HardwareProfile.LOW)
        if profile == HardwareProfile.PERFORMANCE:
            return {
                "threads": 4,
                "context_window": 4096,
                "model_quantization": "Q8_0",
                "semantic_search": True
            }
        else:
            return {
                "threads": 2,
                "context_window": 2048,
                "model_quantization": "Q4_K_M",
                "semantic_search": False
            }
