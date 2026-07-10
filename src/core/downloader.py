"""
Model downloader module for Phoenix OS.

Downloads large model files from Hugging Face with progress bars,
retry logic, and audit logging.
"""

import os
import time
import logging
from typing import Optional, Dict, Any

import requests
from tqdm import tqdm

# Secure components (injected for audit logging)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

# Logger
logger = logging.getLogger(__name__)


class ModelDownloader:
    """
    Handles downloading of GGUF model files from Hugging Face.
    Supports retries, chunked downloads, and audit logging.
    """

    def __init__(self):
        self._secure_memory: Optional[SecureMemoryStore] = None
        self._secure_runner: Optional[SecureCommandRunner] = None
        logger.info("[ModelDownloader] Initialized.")

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info("[ModelDownloader] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner (for future use)."""
        self._secure_runner = secure_runner
        logger.info("[ModelDownloader] SecureCommandRunner attached.")

    # ---------- Core Download Logic ----------
    def download_model(
        self,
        model_url: str = "https://huggingface.co/TheBloke/dolphin-2.6-phi-2-GGUF/resolve/main/dolphin-2_6-phi-2.Q4_K_M.gguf",
        save_path: str = "models/dolphin-2_6-phi-2.Q4_K_M.gguf",
        max_retries: int = 3,
        retry_delay: int = 5,
        timeout: int = 120,  # seconds for initial connection
        chunk_size: int = 8192,
    ) -> bool:
        """
        Download a model from the given URL to the given path.

        Args:
            model_url: URL to download from.
            save_path: Local file path to save the model.
            max_retries: Number of retry attempts on failure.
            retry_delay: Seconds to wait between retries.
            timeout: Connection timeout in seconds.
            chunk_size: Bytes per chunk.

        Returns:
            True if download succeeded, False otherwise.
        """
        # Resolve absolute path and ensure directory exists
        abs_path = os.path.abspath(os.path.expanduser(save_path))
        dir_path = os.path.dirname(abs_path)

        # Check if already exists
        if os.path.exists(abs_path):
            # Verify file size > 0
            if os.path.getsize(abs_path) > 0:
                logger.info(f"[ModelDownloader] Model already exists at {abs_path}")
                self._audit_log("download_model", abs_path, "SKIPPED", {"reason": "exists"})
                return True
            else:
                logger.warning(f"[ModelDownloader] Existing file at {abs_path} has size 0. Re-downloading.")
                os.remove(abs_path)

        # Ensure directory exists
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            logger.error(f"[ModelDownloader] Failed to create directory {dir_path}: {e}")
            return False

        # Perform download with retries
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"[ModelDownloader] Download attempt {attempt}/{max_retries} from {model_url}")
                self._audit_log("download_model", abs_path, "STARTED", {"attempt": attempt})

                # Make request with stream and timeout
                response = requests.get(model_url, stream=True, timeout=timeout)
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))

                # If total_size is 0, fallback to a warning
                if total_size == 0:
                    logger.warning("[ModelDownloader] Content-Length header missing or zero. Progress bar will be indeterminate.")

                # Use a temporary file to avoid corruption on partial downloads
                temp_path = abs_path + ".part"
                with open(temp_path, 'wb') as file:
                    with tqdm(
                        desc=f"Downloading {os.path.basename(abs_path)}",
                        total=total_size if total_size > 0 else None,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        ascii=True,
                        miniters=1,
                    ) as bar:
                        for chunk in response.iter_content(chunk_size=chunk_size):
                            if chunk:
                                file.write(chunk)
                                if total_size > 0:
                                    bar.update(len(chunk))
                                else:
                                    bar.update(len(chunk))  # still updates but no total

                # Rename temp file to final
                os.rename(temp_path, abs_path)
                file_size = os.path.getsize(abs_path)
                logger.info(f"[ModelDownloader] Download complete: {file_size} bytes to {abs_path}")
                self._audit_log("download_model", abs_path, "SUCCESS", {"size_bytes": file_size, "attempt": attempt})
                return True

            except requests.exceptions.Timeout:
                logger.warning(f"[ModelDownloader] Timeout on attempt {attempt}")
                self._audit_log("download_model", abs_path, "RETRY", {"reason": "timeout", "attempt": attempt})
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"[ModelDownloader] Download failed after {max_retries} attempts (timeout).")
                    self._audit_log("download_model", abs_path, "FAILED", {"reason": "timeout", "attempt": attempt})
                    return False

            except requests.exceptions.HTTPError as e:
                logger.error(f"[ModelDownloader] HTTP error on attempt {attempt}: {e}")
                self._audit_log("download_model", abs_path, "FAILED", {"reason": "http_error", "status": e.response.status_code if e.response else "unknown"})
                # Don't retry on 4xx errors (client errors)
                if e.response and 400 <= e.response.status_code < 500:
                    return False
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    return False

            except requests.exceptions.ConnectionError as e:
                logger.warning(f"[ModelDownloader] Connection error on attempt {attempt}: {e}")
                self._audit_log("download_model", abs_path, "RETRY", {"reason": "connection_error", "attempt": attempt})
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    logger.error(f"[ModelDownloader] Download failed after {max_retries} attempts (connection error).")
                    self._audit_log("download_model", abs_path, "FAILED", {"reason": "connection_error", "attempt": attempt})
                    return False

            except Exception as e:
                logger.error(f"[ModelDownloader] Unexpected error on attempt {attempt}: {e}", exc_info=True)
                self._audit_log("download_model", abs_path, "FAILED", {"reason": "unexpected_error", "error": str(e), "attempt": attempt})
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    return False

        return False

    # ---------- Utility: Simple wrapper function ----------
    @staticmethod
    def download_simple(
        model_url: str = "https://huggingface.co/TheBloke/dolphin-2.6-phi-2-GGUF/resolve/main/dolphin-2_6-phi-2.Q4_K_M.gguf",
        save_path: str = "models/dolphin-2_6-phi-2.Q4_K_M.gguf",
    ) -> bool:
        """
        Convenience static method that creates a downloader and runs download_model().
        """
        downloader = ModelDownloader()
        return downloader.download_model(model_url, save_path)

    # ---------- Audit Logging ----------
    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Internal audit logging to secure memory."""
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"DOWNLOADER: {action} on {resource} - {status}",
                    metadata={
                        "type": "downloader_audit",
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details or {},
                    },
                )
            except Exception as e:
                logger.warning(f"[ModelDownloader] Failed to audit log: {e}")

    # ---------- Shutdown ----------
    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("[ModelDownloader] Shutting down.")
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[ModelDownloader] Error closing secure memory: {e}")
        self._secure_memory = None
        self._secure_runner = None


# For backward compatibility with existing code that uses the function directly
def download_model(
    model_url: str = "https://huggingface.co/TheBloke/dolphin-2.6-phi-2-GGUF/resolve/main/dolphin-2_6-phi-2.Q4_K_M.gguf",
    save_path: str = "models/dolphin-2_6-phi-2.Q4_K_M.gguf",
) -> bool:
    """
    Legacy function wrapper that uses the ModelDownloader class.
    """
    return ModelDownloader.download_simple(model_url, save_path)
