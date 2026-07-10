"""
Synapse Interface – The exclusive, deterministic gateway to Phoenix OS internals.

Provides controlled access to file system operations and command execution,
enforcing security policies and logging all actions.
"""

import os
import subprocess
import logging
from typing import Optional, Dict, Any

# Secure components (injected for audit logging and command execution)
try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

from src.core.security import SecurityModule

# Logger
logger = logging.getLogger(__name__)


class SynapseInterface:
    """
    The exclusive, deterministic gateway to Phoenix OS internals.

    All file I/O and command execution passes through this interface,
    which enforces security policies and logs every action.
    Now with full logging, secure memory integration, and proper error handling.
    """

    def __init__(
        self,
        security: SecurityModule,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        """
        Initialize the Synapse Interface.

        Args:
            security: The SecurityModule instance to use for validation.
            secure_memory: Optional SecureMemoryStore for audit logging.
            secure_runner: Optional SecureCommandRunner for safe command execution.
        """
        if security is None:
            raise ValueError("security module cannot be None")

        self.security = security
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        # If secure_runner is not provided, we'll use a fallback subprocess call
        self._use_secure_runner = secure_runner is not None

        logger.info(
            f"[SynapseInterface] Initialized. "
            f"SecureMemory: {secure_memory is not None}, "
            f"SecureRunner: {secure_runner is not None}"
        )

    # ---------- Dependency Injection ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore) -> None:
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info("[SynapseInterface] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner) -> None:
        """Inject secure command runner for safe subprocess execution."""
        self._secure_runner = secure_runner
        self._use_secure_runner = secure_runner is not None
        logger.info("[SynapseInterface] SecureCommandRunner attached.")

    # ---------- Audit Helpers ----------
    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Log an audit event to secure memory (if available) and to the security module."""
        # First, log via the security module (which may also log to console)
        self.security.audit_log(action, resource, status)

        # Then, if we have secure memory, store a structured record
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"SYNAPSE: {action} on {resource} - {status}",
                    metadata={
                        "type": "synapse_audit",
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details or {},
                    },
                )
            except Exception as e:
                logger.warning(f"[SynapseInterface] Failed to audit log: {e}")

    # ---------- File Operations ----------
    def read_file(self, path: str) -> Optional[str]:
        """
        Read a file from the filesystem after security validation.

        Args:
            path: The file path to read.

        Returns:
            The file content as a string, or None if access denied or error.
        """
        if not path:
            logger.warning("[SynapseInterface] read_file called with empty path.")
            return None

        if not self.security.validate_path(path):
            logger.warning(f"[SynapseInterface] Read denied for path: {path}")
            self._audit_log("read_file", path, "DENIED")
            return None

        self._audit_log("read_file", path, "APPROVED")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            logger.debug(f"[SynapseInterface] Read {len(content)} bytes from {path}")
            return content
        except FileNotFoundError:
            logger.error(f"[SynapseInterface] File not found: {path}")
            self._audit_log("read_file", path, "FAILED", {"error": "file_not_found"})
            return None
        except PermissionError:
            logger.error(f"[SynapseInterface] Permission denied reading: {path}")
            self._audit_log("read_file", path, "FAILED", {"error": "permission_denied"})
            return None
        except Exception as e:
            logger.error(f"[SynapseInterface] Read error on {path}: {e}", exc_info=True)
            self._audit_log("read_file", path, "FAILED", {"error": str(e)})
            return None

    def write_file(self, path: str, content: str) -> bool:
        """
        Write content to a file after security validation.

        Args:
            path: The file path to write.
            content: The content to write.

        Returns:
            True if successful, False otherwise.
        """
        if not path:
            logger.warning("[SynapseInterface] write_file called with empty path.")
            return False

        if not self.security.validate_path(path):
            logger.warning(f"[SynapseInterface] Write denied for path: {path}")
            self._audit_log("write_file", path, "DENIED")
            return False

        self._audit_log("write_file", path, "APPROVED", {"size": len(content)})

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.debug(f"[SynapseInterface] Wrote {len(content)} bytes to {path}")
            self._audit_log("write_file", path, "SUCCESS", {"size": len(content)})
            return True
        except PermissionError:
            logger.error(f"[SynapseInterface] Permission denied writing: {path}")
            self._audit_log("write_file", path, "FAILED", {"error": "permission_denied"})
            return False
        except Exception as e:
            logger.error(f"[SynapseInterface] Write error on {path}: {e}", exc_info=True)
            self._audit_log("write_file", path, "FAILED", {"error": str(e)})
            return False

    # ---------- Command Execution ----------
    def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        Execute a system command after security validation.

        Args:
            command: The command string to execute.
            timeout: Maximum execution time in seconds.

        Returns:
            The command output (stdout + stderr) or an error message.
        """
        if not command:
            logger.warning("[SynapseInterface] execute_command called with empty command.")
            return "Error: No command provided."

        # Validate the command
        if not self.security.validate_command(command):
            logger.warning(f"[SynapseInterface] Command denied: {command}")
            self._audit_log("execute_command", command, "DENIED")
            return "Security Denial: Command not allowed."

        self._audit_log("execute_command", command, "APPROVED")

        try:
            # If we have a secure runner, use it
            if self._use_secure_runner and self._secure_runner is not None:
                # The secure runner expects a list of args
                import shlex
                args = shlex.split(command)
                result = self._secure_runner.run_safe(args, timeout=timeout)
                self._audit_log("execute_command", command, "SUCCESS", {"output_preview": result[:200]})
                return result

            # Fallback: use subprocess directly (still with shell=False)
            import shlex
            args = shlex.split(command)
            # But we must ensure the base command is in the whitelist (already checked by validate_command)
            # However, we also need to sanitize arguments if using direct subprocess
            # We'll use a safe subprocess call
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                shell=False,
                timeout=timeout,
            )
            output = result.stdout + result.stderr
            if result.returncode != 0:
                logger.warning(f"[SynapseInterface] Command '{command}' exited with code {result.returncode}")
                self._audit_log("execute_command", command, "FAILED", {"returncode": result.returncode})
                return f"Command failed (code {result.returncode}): {output.strip()}"
            self._audit_log("execute_command", command, "SUCCESS", {"output_preview": output[:200]})
            return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"[SynapseInterface] Command '{command}' timed out after {timeout}s")
            self._audit_log("execute_command", command, "FAILED", {"error": "timeout"})
            return f"Error: Command timed out after {timeout} seconds."
        except Exception as e:
            logger.error(f"[SynapseInterface] Command execution error: {e}", exc_info=True)
            self._audit_log("execute_command", command, "FAILED", {"error": str(e)})
            return f"Error executing command: {e}"

    # ---------- Shutdown ----------
    def shutdown(self) -> None:
        """Clean up resources."""
        logger.info("[SynapseInterface] Shutting down.")
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[SynapseInterface] Error closing secure memory: {e}")
        self._secure_memory = None
        self._secure_runner = None
        self._use_secure_runner = False
