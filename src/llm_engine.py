import os
from llama_cpp import Llama

class LLMEngine:
    def __init__(self, model_path=None):
        self.model_path = model_path or os.getenv("MODEL_PATH", "models/phi-2.Q4_K_M.gguf")
        self.llm = None

        if os.path.exists(self.model_path):
            self.load_model()
        else:
            print(f"Warning: Model not found at {self.model_path}. Please download it.")

    def load_model(self):
        print(f"Loading model from {self.model_path}...")

        try:
            from profiles import HardwareProfile
            settings = HardwareProfile.get_settings()
        except ImportError:
            settings = {"n_ctx": 2048, "n_batch": 512}

        lora_path = os.getenv("LORA_PATH", "models/refined_model")

        self.llm = Llama(
            model_path=self.model_path,
            lora_path=lora_path if os.path.exists(lora_path) else None,
            n_ctx=int(os.getenv("N_CTX", str(settings["n_ctx"]))),
            n_batch=int(os.getenv("N_BATCH", str(settings["n_batch"]))),
            n_threads=int(os.getenv("N_THREADS", str(os.cpu_count()))),
            n_gpu_layers=0,
            embedding=True, # Enable embeddings for semantic search
            verbose=False
        )
        print("Model loaded successfully" + (f" with adapter from {lora_path}" if os.path.exists(lora_path) else ""))

    def embed(self, text):
        if not self.llm:
            return None
        return self.llm.create_embedding(text)["data"][0]["embedding"]

    def generate(self, prompt, max_tokens=512, stop=None):
        if not self.llm:
            return "Error: LLM not initialized. Model might be missing."

        output = self.llm(
            prompt,
            max_tokens=max_tokens,
            stop=stop or ["Q:", "User:"],
            echo=False
        )
        return output["choices"][0]["text"].strip()

if __name__ == "__main__":
    # Test initialization
    engine = LLMEngine()
