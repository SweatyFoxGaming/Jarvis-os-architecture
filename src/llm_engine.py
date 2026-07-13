# src/llm_engine.py
import os
import sys
import logging
from typing import Optional, Generator, Union

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from config.secure_config import AppConfig
    AppConfig.load()
except ImportError:
    AppConfig = None
except ValueError:
    AppConfig = None

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None
    print("llama-cpp-python not available. Running in simulation mode.")

logger = logging.getLogger(__name__)


class LLMEngine:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = self._resolve_model_path(model_path)
        self.llm: Optional[Llama] = None
        self._load_model()

    def _resolve_model_path(self, provided_path: Optional[str]) -> str:
        if provided_path and os.path.exists(provided_path):
            return os.path.abspath(provided_path)
        env_path = os.getenv("MODEL_PATH")
        if env_path and os.path.exists(env_path):
            return os.path.abspath(env_path)
        if getattr(sys, 'frozen', False):
            base_dir = sys._MEIPASS
        else:
            base_dir = PROJECT_ROOT
        default_path = os.path.join(base_dir, "models", "dolphin-2_6-phi-2.Q4_K_M.gguf")
        logger.info(f"Resolved default model path: {default_path}")
        return default_path

    def _load_model(self):
        if Llama is None:
            logger.warning("llama-cpp-python not installed. Running in simulation mode.")
            return

        if not os.path.exists(self.model_path):
            logger.warning(f"Model not found at {self.model_path}. Attempting download...")
            try:
                from src.core.downloader import download_model
                success = download_model(save_path=self.model_path)
                if not success:
                    logger.error("Model download failed.")
                    return
            except Exception as e:
                logger.error(f"Download error: {e}", exc_info=True)
                return

        try:
            try:
                from src.core.profiles import HardwareProfile
                settings = HardwareProfile.get_settings()
            except Exception:
                logger.warning("HardwareProfile not found, using default settings.")
                settings = {"context_window": 2048, "n_ctx": 2048, "n_batch": 512}

            n_ctx = settings.get("n_ctx") or settings.get("context_window") or 2048
            n_batch = settings.get("n_batch") or 512
            n_ctx = int(os.getenv("N_CTX", n_ctx))
            n_batch = int(os.getenv("N_BATCH", n_batch))
            n_threads = int(os.getenv("N_THREADS", os.cpu_count() or 2))

            lora_path = os.getenv("LORA_PATH", "models/refined_model")
            if not os.path.exists(lora_path):
                lora_path = None

            logger.info(f"Loading model: {self.model_path}")
            logger.info(f"Context: {n_ctx}, Batch: {n_batch}, Threads: {n_threads}")

            self.llm = Llama(
                model_path=self.model_path,
                lora_path=lora_path,
                n_ctx=n_ctx,
                n_batch=n_batch,
                n_threads=n_threads,
                n_gpu_layers=0,
                embedding=True,
                verbose=False
            )
            logger.info("✅ Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            self.llm = None

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        stop: Optional[list] = None,
        stream: bool = False,
        temperature: float = 0.7
    ) -> Union[str, Generator[str, None, None]]:
        if self.llm is None:
            logger.info("Running in simulation mode.")
            return self._simulate_response(prompt, stream)

        if stop is None:
            stop = ["User:", "Q:", "\n\n\n"]

        try:
            logger.info(f"Generating response for prompt: {prompt[:50]}...")
            if stream:
                def token_generator():
                    try:
                        for token in self.llm(
                            prompt,
                            max_tokens=max_tokens,
                            stop=stop,
                            stream=True,
                            temperature=temperature,
                            echo=False
                        ):
                            if 'choices' in token and len(token['choices']) > 0:
                                delta = token['choices'][0].get('delta', {})
                                content = delta.get('content', '')
                                if content:
                                    yield content
                    except Exception as e:
                        logger.error(f"Streaming error: {e}", exc_info=True)
                        if "context window" in str(e).lower() or "tokens" in str(e).lower():
                            yield "\n[ERROR] The prompt is too long. Please shorten your request."
                        else:
                            yield f"\n[ERROR] Generation failed: {e}"
                return token_generator()
            else:
                response = self.llm(
                    prompt,
                    max_tokens=max_tokens,
                    stop=stop,
                    stream=False,
                    temperature=temperature,
                    echo=False
                )
                if 'choices' in response and len(response['choices']) > 0:
                    return response['choices'][0].get('text', '').strip()
                else:
                    logger.warning("Unexpected response format from LLM.")
                    return "Error: Invalid response from model."
        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
            if "context window" in str(e).lower() or "tokens" in str(e).lower():
                return "[ERROR] The prompt is too long. Please shorten your request or ask about a specific topic."
            return f"[ERROR] Model generation failed: {str(e)}"

    def _simulate_response(self, prompt: str, stream: bool) -> Union[str, Generator[str, None, None]]:
        lower_prompt = prompt.lower()
        responses = {
            "status": "I am JARVIS V3 — the Executive Mind of the Phoenix Intelligence Platform.\nCurrent Status: Fully operational in Executive Architecture mode.\n- Executive Mind + Board: Active\n- Research & Coding Departments: Ready\n- Memory System: Online\n⚠️ Running in SIMULATION mode (real model not loaded).",
            "hello": "Hello! I am JARVIS, the cognitive core for Phoenix OS. How can I assist you today?",
            "capability": "I can perform research, generate and review code, plan complex tasks, and manage long-term goals.",
            "who are you": "I am JARVIS V3, the AIOS cognitive core. I manage departments, memory, and executive functions."
        }
        response_text = "[JARVIS] Acknowledged."
        for key, value in responses.items():
            if key in lower_prompt:
                response_text = value
                break
        else:
            response_text = f"[JARVIS] Acknowledged: {prompt[:120]}...\nI am processing this through the Executive Mind."

        if stream:
            def sim_generator():
                for word in response_text.split(" "):
                    yield word + " "
            return sim_generator()
        else:
            return response_text

    def unload(self):
        if self.llm:
            logger.info("Unloading model from memory.")
            del self.llm
            self.llm = None
            import gc
            gc.collect()
            logger.info("Model unloaded.")
