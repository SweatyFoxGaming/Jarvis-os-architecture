import os

class HardwareProfile:
    LOW = "low"         # 1-2GB RAM
    PERFORMANCE = "perf" # 4GB+ RAM

    PROFILES = {
        LOW: {
            "n_ctx": 2048,
            "n_batch": 512,
            "model_hint": "TinyLlama-1.1B or Phi-2-2.7B",
            "semantic_search": False
        },
        PERFORMANCE: {
            "n_ctx": 4096,
            "n_batch": 1024,
            "model_hint": "Llama-3-8B or Mistral-7B",
            "semantic_search": True
        }
    }

    @staticmethod
    def get_current():
        return os.getenv("HARDWARE_PROFILE", HardwareProfile.LOW)

    @staticmethod
    def get_settings():
        profile = HardwareProfile.get_current()
        return HardwareProfile.PROFILES.get(profile, HardwareProfile.PROFILES[HardwareProfile.LOW])
