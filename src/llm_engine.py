import os
import sys
from llama_cpp import Llama

class LLMEngine:
    def __init__(self, model_path=None):
        # Determine the base directory dynamically
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        default_path = os.path.join(base_dir, "models/phi-2.Q4_K_M.gguf")
        self.model_path = model_path or os.getenv("MODEL_PATH", default_path)
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

    def generate(self, prompt, max_tokens=512, stop=None, stream=False):
        if not self.llm:
            if stream: yield "Error: LLM not initialized."
            else: return "Error: LLM not initialized."
            return

        try:
            from templates import PromptTemplate
            formatted_prompt = PromptTemplate.format(prompt)
        except ImportError:
            formatted_prompt = prompt

        stop_seq = stop or ["Instruct:", "User:", "###", "<|end_of_text|>", "<|eot_id|>", "Q:", "A:"]

        if stream:
            output = self.llm(
                formatted_prompt,
                max_tokens=max_tokens,
                stop=stop_seq,
                echo=False,
                stream=True
            )
            for chunk in output:
                if "choices" in chunk and len(chunk["choices"]) > 0:
                    token = chunk["choices"][0].get("text", "")
                    if token:
                        yield token
        else:
            output = self.llm(
                formatted_prompt,
                max_tokens=max_tokens,
                stop=stop_seq,
                echo=False
            )
            res = output["choices"][0]["text"].strip()
            return res if res else "JARVIS: [Empty response]"

if __name__ == "__main__":
    # Test initialization
    engine = LLMEngine()
