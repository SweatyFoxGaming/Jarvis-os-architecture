import os
import sys

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None
    print("llama-cpp-python not available. Using simulation mode.")

class LLMEngine:
    def __init__(self, model_path=None):
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        default_path = os.path.join(base_dir, "models/dolphin-2_6-phi-2.Q4_K_M.gguf")
        self.model_path = model_path or os.getenv("MODEL_PATH", default_path)
        self.llm = None
        
        if not os.path.exists(self.model_path):
            print(f"Model not found at {self.model_path}. Attempting download...")
            try:
                from src.core.downloader import download_model
                success = download_model(save_path=self.model_path)
                if not success:
                    print("Warning: Model download failed.")
            except Exception as e:
                print(f"Download error: {e}")
        
        if os.path.exists(self.model_path):
            self.load_model()
        else:
            print(f"Warning: Model not found. Running in simulation mode.")

    def load_model(self):
        if Llama is None:
            print("Cannot load real model (llama-cpp not installed). Using simulation.")
            return
            
        print(f"Loading model from {self.model_path}...")
        
        # Safe settings loading
        try:
            from src.core.profiles import HardwareProfile
            settings = HardwareProfile.get_settings()
        except Exception:
            settings = {"context_window": 2048, "n_ctx": 2048, "n_batch": 512}
        
        # Fallback for different key names
        n_ctx = settings.get("n_ctx") or settings.get("context_window") or 2048
        n_batch = settings.get("n_batch") or 512
        
        lora_path = os.getenv("LORA_PATH", "models/refined_model")
        
        self.llm = Llama(
            model_path=self.model_path,
            lora_path=lora_path if os.path.exists(lora_path) else None,
            n_ctx=int(os.getenv("N_CTX", str(n_ctx))),
            n_batch=int(os.getenv("N_BATCH", str(n_batch))),
            n_threads=int(os.getenv("N_THREADS", str(os.cpu_count() or 2))),
            n_gpu_layers=0,
            embedding=True,
            verbose=False
        )
        print("✅ Model loaded successfully")

    def generate(self, prompt, max_tokens=512, stop=None, stream=False):
        if not self.llm:
            msg = "Error: LLM not initialized. Running in simulation mode."
            if stream:
                yield msg
                return
            return msg

        try:
            formatted_prompt = prompt
            stop_seq = stop or ["Instruct:", "User:", "###", "<|end_of_text|>"]

            if stream:
                yield "[Simulation Mode] Streaming not fully implemented."
            else:
                return f"[JARVIS] I received your request: {prompt[:80]}..."
        except Exception as e:
            return f"Generation error: {e}"

if __name__ == "__main__":
    engine = LLMEngine()
