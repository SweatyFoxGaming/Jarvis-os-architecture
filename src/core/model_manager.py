import os
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.core.models import Task, TaskStatus

# Logger
logger = logging.getLogger(__name__)


class ModelManager:
    """
    Manages multiple LLM models, handles loading, selection, and retrieval.
    Now with logging, error handling, and support for multiple backends.
    """

    def __init__(
        self,
        hardware_settings: Dict[str, Any],
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        """
        Initialize the ModelManager with hardware settings and optional secure components.

        Args:
            hardware_settings: Dictionary with hardware configuration (threads, context_window, etc.)
            secure_memory: Optional SecureMemoryStore for audit logging
            secure_runner: Optional SecureCommandRunner for safe subprocess execution
        """
        self.settings = hardware_settings
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        # Model storage: maps model_name -> model_instance
        self._models: Dict[str, Any] = {}

        # Model metadata: maps model_name -> metadata dict
        self._model_metadata: Dict[str, Dict[str, Any]] = {}

        # Default engine (for backward compatibility)
        self._default_engine = None

        logger.info(
            f"[ModelManager] Initialized with settings: {self._sanitize_settings(hardware_settings)}. "
            f"SecureMemory: {secure_memory is not None}"
        )

    def _sanitize_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive values from settings for logging."""
        safe = settings.copy()
        # No sensitive keys to remove, but keep for future
        return safe

    # ---------- Dependency Injection Setters ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        self._secure_memory = secure_memory
        logger.info("[ModelManager] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        self._secure_runner = secure_runner
        logger.info("[ModelManager] SecureCommandRunner attached.")

    # ---------- Model Management ----------
    def register_model(
        self,
        model_name: str,
        model_instance: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register a pre-loaded model instance with the manager.

        Args:
            model_name: Unique identifier for the model
            model_instance: The actual model object (e.g., Llama instance)
            metadata: Optional metadata (path, type, quantization, etc.)
        """
        if not model_name or not model_instance:
            raise ValueError("model_name and model_instance are required.")

        self._models[model_name] = model_instance
        self._model_metadata[model_name] = metadata or {
            "status": "loaded",
            "registered_at": str(datetime.now()),
        }

        # Set as default if this is the first model
        if self._default_engine is None:
            self._default_engine = model_instance
            logger.info(f"[ModelManager] Set '{model_name}' as default engine.")

        logger.info(f"[ModelManager] Registered model: '{model_name}'")

        # Audit log
        self._audit_log("register_model", model_name, "SUCCESS", metadata)

    def load_model(
        self,
        model_type: str,
        model_path: str,
        backend: str = "llama_cpp",
        **kwargs,
    ) -> Optional[Any]:
        """
        Load a model from disk using the specified backend.

        Args:
            model_type: Type identifier (e.g., "llama", "gguf", "openai")
            model_path: Path to the model file or API endpoint
            backend: Backend to use ("llama_cpp", "openai", "mock")
            **kwargs: Additional backend-specific arguments

        Returns:
            The loaded model instance, or None if loading failed.
        """
        if not model_path:
            logger.error("[ModelManager] model_path is required.")
            return None

        # Check if path exists (for local models)
        if backend != "openai" and not os.path.exists(model_path):
            logger.error(f"[ModelManager] Model path not found: {model_path}")
            self._audit_log("load_model", model_path, "FAILED", {"error": "path_not_found"})
            return None

        logger.info(f"[ModelManager] Loading {model_type} model from {model_path} with backend '{backend}'...")

        try:
            model_instance = None

            # ---------- Backend Selection ----------
            if backend == "llama_cpp":
                # Use the existing LLMEngine or load directly
                try:
                    from llama_cpp import Llama
                    model_instance = Llama(
                        model_path=model_path,
                        n_ctx=kwargs.get("n_ctx", self.settings.get("n_ctx", 2048)),
                        n_batch=kwargs.get("n_batch", self.settings.get("n_batch", 512)),
                        n_threads=kwargs.get("n_threads", self.settings.get("threads", 2)),
                        n_gpu_layers=kwargs.get("n_gpu_layers", self.settings.get("gpu_layers", 0)),
                        verbose=kwargs.get("verbose", False),
                    )
                    logger.info(f"[ModelManager] Successfully loaded Llama model from {model_path}")

                except ImportError:
                    logger.error("llama-cpp-python not installed. Cannot load llama_cpp model.")
                    self._audit_log("load_model", model_path, "FAILED", {"error": "import_error"})
                    return None

            elif backend == "openai":
                # For OpenAI API models (no local file needed)
                try:
                    import openai
                    openai.api_key = os.getenv("OPENAI_API_KEY")
                    model_instance = {
                        "backend": "openai",
                        "model_name": kwargs.get("openai_model", "gpt-4o-mini"),
                        "api_key_set": bool(openai.api_key),
                    }
                    logger.info(f"[ModelManager] Configured OpenAI model: {model_instance['model_name']}")
                except ImportError:
                    logger.error("openai package not installed. Cannot load OpenAI model.")
                    self._audit_log("load_model", model_path, "FAILED", {"error": "import_error"})
                    return None

            elif backend == "mock":
                # Mock model for testing
                model_instance = {
                    "backend": "mock",
                    "model_path": model_path,
                }
                logger.info("[ModelManager] Using mock model (for testing).")

            else:
                logger.error(f"[ModelManager] Unsupported backend: {backend}")
                self._audit_log("load_model", model_path, "FAILED", {"error": "unsupported_backend"})
                return None

            # Register the loaded model
            if model_instance:
                self.register_model(
                    model_name=model_type,
                    model_instance=model_instance,
                    metadata={
                        "path": model_path,
                        "backend": backend,
                        "loaded_at": str(datetime.now()),
                        **kwargs,
                    },
                )
                return model_instance

            return None

        except Exception as e:
            logger.error(f"[ModelManager] Failed to load model {model_type} from {model_path}: {e}", exc_info=True)
            self._audit_log("load_model", model_path, "FAILED", {"error": str(e)})
            return None

    def select_model_for_task(self, task: Task) -> Optional[str]:
        """
        Select the most appropriate model name for a given task.

        Args:
            task: The task requiring a model

        Returns:
            The model name to use, or None if no suitable model found.
        """
        if not task:
            logger.warning("[ModelManager] select_model_for_task called with None task.")
            return None

        # If no models are registered, return None
        if not self._models:
            logger.warning("[ModelManager] No models registered.")
            return None

        # Priority 1: If the task has a specific model requirement in input_data
        if task.input_data and task.input_data.get("model_name"):
            requested_model = task.input_data["model_name"]
            if requested_model in self._models:
                logger.debug(f"[ModelManager] Using requested model: {requested_model}")
                return requested_model
            else:
                logger.warning(f"[ModelManager] Requested model '{requested_model}' not found. Falling back.")

        # Priority 2: If the task has a target_capability that hints at model type
        capability = task.target_capability.lower() if task.target_capability else ""

        if "coding" in capability or "code" in capability or "debug" in capability:
            # Look for a coding-specific model
            for model_name in self._models:
                if "coding" in model_name.lower():
                    logger.debug(f"[ModelManager] Selected coding model: {model_name}")
                    return model_name

        if "research" in capability or "analysis" in capability or "report" in capability:
            # Look for a research/general model
            for model_name in self._models:
                if any(k in model_name.lower() for k in ["general", "research", "llama"]):
                    logger.debug(f"[ModelManager] Selected research model: {model_name}")
                    return model_name

        # Priority 3: Consider resource constraints
        if task.resource_budget and task.resource_budget.ram_limit_mb < 512:
            for model_name, _ in self._models.items():
                if "small" in model_name.lower() or "tiny" in model_name.lower():
                    logger.debug(f"[ModelManager] Selected small model for low RAM: {model_name}")
                    return model_name

        # Priority 4: Return the default model (first registered)
        default_model = next(iter(self._models.keys()))
        logger.debug(f"[ModelManager] Falling back to default model: {default_model}")
        return default_model

    def get_engine(self, model_name: Optional[str] = None):
        """
        Retrieve a model instance by name.
        If no name is provided, returns the default engine.

        Args:
            model_name: Optional name of the model to retrieve

        Returns:
            The model instance, or None if not found.
        """
        if model_name is None:
            # Return the default engine
            if self._default_engine is None and self._models:
                # Set default to first model
                self._default_engine = next(iter(self._models.values()))
            return self._default_engine

        engine = self._models.get(model_name)
        if engine is None:
            logger.warning(f"[ModelManager] Model '{model_name}' not found.")
        else:
            logger.debug(f"[ModelManager] Retrieved model: '{model_name}'")
        return engine

    def list_models(self) -> List[str]:
        """Return a list of all registered model names."""
        return list(self._models.keys())

    def get_model_metadata(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Return metadata for a specific model."""
        return self._model_metadata.get(model_name)

    def unload_model(self, model_name: str) -> bool:
        """
        Unload a model and free its resources.
        Returns True if successful, False otherwise.
        """
        if model_name not in self._models:
            logger.warning(f"[ModelManager] Model '{model_name}' not found.")
            return False

        try:
            # If the model has a close/unload method, call it
            model = self._models[model_name]
            if hasattr(model, 'close'):
                model.close()
            elif hasattr(model, '__del__'):
                # Some models free on deletion
                pass

            del self._models[model_name]
            if model_name in self._model_metadata:
                del self._model_metadata[model_name]

            # If this was the default, reset
            if self._default_engine == model:
                self._default_engine = None

            logger.info(f"[ModelManager] Unloaded model: '{model_name}'")
            self._audit_log("unload_model", model_name, "SUCCESS", {})
            return True

        except Exception as e:
            logger.error(f"[ModelManager] Failed to unload model '{model_name}': {e}", exc_info=True)
            self._audit_log("unload_model", model_name, "FAILED", {"error": str(e)})
            return False

    def reload_model(self, model_name: str) -> Optional[Any]:
        """
        Reload a model from its original path.
        Returns the reloaded model instance, or None on failure.
        """
        metadata = self._model_metadata.get(model_name)
        if not metadata:
            logger.error(f"[ModelManager] No metadata found for model '{model_name}'")
            return None

        path = metadata.get("path")
        backend = metadata.get("backend", "llama_cpp")
        if not path:
            logger.error(f"[ModelManager] No path found in metadata for '{model_name}'")
            return None

        # Unload first
        self.unload_model(model_name)

        # Re-load
        return self.load_model(model_name, path, backend=backend)

    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Internal audit logging to secure memory."""
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"MODEL_MANAGER: {action} on {resource}",
                    metadata={
                        "type": "model_manager_audit",
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details or {},
                    },
                )
            except Exception as e:
                logger.warning(f"[ModelManager] Failed to audit log: {e}")

    # ---------- Shutdown ----------
    def shutdown(self):
        """Clean up resources and unload all models."""
        logger.info("[ModelManager] Shutting down.")
        for model_name in list(self._models.keys()):
            self.unload_model(model_name)
        self._models.clear()
        self._model_metadata.clear()
        self._default_engine = None

        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[ModelManager] Error closing secure memory: {e}")


# Fix missing datetime import at module level
import datetime
