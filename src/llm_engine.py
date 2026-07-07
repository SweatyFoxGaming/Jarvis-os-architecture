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
        self.llm = Llama(
            model_path=self.model_path,
            n_ctx=2048,
            n_threads=os.cpu_count(),
            n_gpu_layers=0 # Default to CPU
        )
        print("Model loaded successfully.")

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
