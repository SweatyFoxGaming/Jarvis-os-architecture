import os
import shlex
import logging
from typing import List, Dict, Any, Optional

# Secure components (injected for consistency)
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


class SecurityPolicy:
    """
    Defines the security policy for Phoenix OS.
    Contains allowed file system paths and system commands.
    """
    def __init__(self):
        # Base directory: project root (two levels up from src/core)
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # Allowed paths (whitelist)
        self.allowed_paths: List[str] = [
            os.path.join(base_dir, "data"),
            os.path.join(base_dir, "tmp"),
            "/tmp/jarvis",
            os.path.join(base_dir, "logs"),  # Added for consistency
        ]

        # Allowed system commands (whitelist)
        self.allowed_commands: List[str] = ["ls", "grep", "cat", "echo", "pwd"]

        # Ensure allowed paths exist, with proper error handling
        for path in self.allowed_paths:
            try:
                os.makedirs(path, exist_ok=True)
                logger.debug(f"[SecurityPolicy] Ensured path exists: {path}")
            except PermissionError as e:
                logger.warning(f"[SecurityPolicy] Permission denied creating {path}: {e}")
            except OSError as e:
                logger.warning(f"[SecurityPolicy] OS error creating {path}: {e}")
            except Exception as e:
                logger.error(f"[SecurityPolicy] Unexpected error creating {path}: {e}", exc_info=True)

        # Log initialization
        logger.info(
            f"[SecurityPolicy] Initialized. Allowed paths: {len(self.allowed_paths)}, "
            f"Allowed commands: {self.allowed_commands}"
        )

    def add_allowed_path(self, path: str) -> bool:
        """Dynamically add a new allowed path at runtime (with validation)."""
        try:
            abs_path = os.path.abspath(path)
            if abs_path not in self.allowed_paths:
                self.allowed_paths.append(abs_path)
                os.makedirs(abs_path, exist_ok=True)
                logger.info(f"[SecurityPolicy] Added allowed path: {abs_path}")
                return True
            return True  # Already exists
        except Exception as e:
            logger.error(f"[SecurityPolicy] Failed to add path {path}: {e}", exc_info=True)
            return False

    def add_allowed_command(self, command: str) -> bool:
        """Dynamically add a new allowed command at runtime."""
        if command and command not in self.allowed_commands:
            self.allowed_commands.append(command.strip())
            logger.info(f"[SecurityPolicy] Added allowed command: {command}")
            return True
        return False


class CapabilityToken:
    """
    Simple capability token representing a resource and its allowed permissions.
    Used for fine-grained access control.
    """
    def __init__(self, resource: str, permissions: List[str]):
        self.resource = resource
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        """Check if this token grants a specific permission."""
        return permission in self.permissions

    def __repr__(self) -> str:
        return f"CapabilityToken(resource={self.resource}, permissions={self.permissions})"


class SecurityModule:
    """
    Central security module for Phoenix OS.
    Handles path validation, command validation, and audit logging.
    Now with proper logging, exception handling, and injection support.
    """
    def __init__(
        self,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        self.policy = SecurityPolicy()
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        # In-memory audit trail (if secure memory is not available)
        self._audit_log: List[Dict[str, Any]] = []

        logger.info(
            f"[SecurityModule] Initialized. SecureMemory: {secure_memory is not None}, "
            f"SecureRunner: {secure_runner is not None}"
        )

    # ---------- Dependency Injection Setters ----------
    def set_secure_memory(self, secure_memory: SecureMemoryStore):
        """Inject secure memory after construction."""
        self._secure_memory = secure_memory
        logger.info("[SecurityModule] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: SecureCommandRunner):
        """Inject secure command runner after construction."""
        self._secure_runner = secure_runner
        logger.info("[SecurityModule] SecureCommandRunner attached.")

    # ---------- Path Validation ----------
    def validate_path(self, path: str) -> bool:
        """
        Validate that a given path is within the allowed paths whitelist.
        Returns True if allowed, False otherwise.
        """
        try:
            if not path:
                logger.warning("[SecurityModule] validate_path called with empty path.")
                return False

            abs_path = os.path.abspath(path)

            for allowed in self.policy.allowed_paths:
                if abs_path.startswith(allowed):
                    logger.debug(f"[SecurityModule] Path validated: {abs_path} (allowed: {allowed})")
                    return True

            logger.warning(f"[SecurityModule] Path rejected: {abs_path} (not in whitelist)")
            self.audit_log("validate_path", path, "DENIED")
            return False

        except TypeError as e:
            logger.error(f"[SecurityModule] Type error validating path: {e}")
            return False
        except Exception as e:
            logger.error(f"[SecurityModule] Unexpected error validating path: {e}", exc_info=True)
            return False

    # ---------- Command Validation ----------
    def validate_command(self, command: str) -> bool:
        """
        Validate that a given command is in the allowed commands whitelist.
        Returns True if allowed, False otherwise.
        Uses shlex to properly parse the command string.
        """
        try:
            if not command:
                logger.warning("[SecurityModule] validate_command called with empty command.")
                return False

            # Use shlex to split the command safely (handles quoted strings)
            parts = shlex.split(command)
            if not parts:
                return False

            base_cmd = parts[0]

            # Check if the base command is in the whitelist
            if base_cmd in self.policy.allowed_commands:
                logger.debug(f"[SecurityModule] Command validated: {base_cmd}")
                return True

            logger.warning(f"[SecurityModule] Command rejected: {base_cmd} (not in whitelist)")
            self.audit_log("validate_command", command, "DENIED")
            return False

        except ValueError as e:
            # shlex.split raises ValueError on malformed strings
            logger.warning(f"[SecurityModule] Malformed command string: {command} - {e}")
            return False
        except Exception as e:
            logger.error(f"[SecurityModule] Unexpected error validating command: {e}", exc_info=True)
            return False

    # ---------- Audit Logging ----------
    def audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None):
        """
        Log an audit event to the console, internal memory, and optionally secure memory.
        """
        log_entry = {
            "action": action,
            "resource": resource,
            "status": status,
            "details": details or {},
        }

        # 1. Log to Python logger
        log_msg = f"Audit: {status.upper()} - Action='{action}' on Resource='{resource}'"
        if details:
            log_msg += f" Details={details}"
        logger.info(log_msg)

        # 2. Store in in-memory audit trail
        self._audit_log.append(log_entry)

        # 3. Store in secure memory (if available)
        if self._secure_memory is not None:
            try:
                self._secure_memory.insert(
                    text=f"AUDIT: {action} on {resource}",
                    metadata={
                        "type": "security_audit",
                        "action": action,
                        "resource": resource,
                        "status": status,
                        "details": details,
                    },
                )
            except Exception as e:
                logger.warning(f"[SecurityModule] Failed to store audit entry in secure memory: {e}")

    # ---------- Utility: Sanitize Input ----------
    def sanitize_input(self, input_string: str, max_length: int = 2048) -> str:
        """
        Sanitize user input to prevent injection attacks.
        Truncates to max_length and removes control characters.
        """
        if not input_string:
            return ""
        try:
            # Truncate
            if len(input_string) > max_length:
                logger.warning(f"[SecurityModule] Input truncated from {len(input_string)} to {max_length} chars.")
                input_string = input_string[:max_length]

            # Remove null bytes and other dangerous control characters
            # Keep newline, tab, and printable characters
            sanitized = ''.join(char for char in input_string if 31 < ord(char) < 127 or char in '\n\r\t')
            return sanitized
        except Exception as e:
            logger.error(f"[SecurityModule] Error sanitizing input: {e}")
            return ""

    # ---------- Utility: Get Audit Trail ----------
    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the last `limit` audit log entries."""
        return self._audit_log[-limit:]

    # ---------- Shutdown ----------
    def shutdown(self):
        """Clean up resources if needed."""
        logger.info("[SecurityModule] Shutting down.")
        self._audit_log.clear()
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[SecurityModule] Error closing secure memory: {e}")
