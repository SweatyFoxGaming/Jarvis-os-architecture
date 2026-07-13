import os
import shlex
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class SecurityPolicy:
    """
    Immutable security policy once frozen.
    """
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # ---------- Allowed Paths ----------
        self._allowed_paths: List[str] = [
            os.path.join(base_dir, "data"),
            os.path.join(base_dir, "tmp"),
            "/tmp/jarvis",
            os.path.join(base_dir, "logs"),
            "/tmp",
            "/var/log",
            "/home",
            "/etc",
            "/usr/local/bin",
            "/usr/bin",
        ]

        # ---------- Allowed Commands ----------
        self._allowed_commands: List[str] = [
            "ls", "cat", "head", "tail", "wc", "sort", "uniq", "grep", "find",
            "mkdir", "rm", "cp", "mv", "chmod", "chown", "ln",
            "df", "du", "free", "ps", "top", "htop", "uptime", "who", "w",
            "kill", "pkill", "killall", "nice", "renice",
            "ping", "curl", "wget", "netstat", "ss", "ifconfig", "ip",
            "apt", "apt-get", "dpkg",
            "systemctl", "journalctl", "service",
            "echo", "printf", "sed", "awk", "cut", "paste", "join",
            "tar", "gzip", "gunzip", "zip", "unzip",
            "make", "gcc", "g++", "python3", "pip", "pip3",
            "date", "time", "which", "whereis", "locate", "updatedb",
            "ssh", "scp", "rsync",
            "docker", "docker-compose",
            # Added for chained commands
            "cd", "git",
        ]

        self._frozen = False

        for path in self._allowed_paths:
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                logger.warning(f"[SecurityPolicy] Could not create {path}: {e}")

    def freeze(self):
        self._frozen = True
        logger.info("[SecurityPolicy] Policy frozen. No further modifications allowed.")

    @property
    def allowed_paths(self) -> List[str]:
        return self._allowed_paths.copy()

    @property
    def allowed_commands(self) -> List[str]:
        return self._allowed_commands.copy()

    def add_allowed_path(self, path: str) -> bool:
        if self._frozen:
            raise RuntimeError("SecurityPolicy is frozen. Cannot add allowed path.")
        abs_path = os.path.abspath(path)
        if abs_path not in self._allowed_paths:
            self._allowed_paths.append(abs_path)
            os.makedirs(abs_path, exist_ok=True)
            logger.info(f"[SecurityPolicy] Added allowed path: {abs_path}")
            return True
        return True

    def add_allowed_command(self, command: str) -> bool:
        if self._frozen:
            raise RuntimeError("SecurityPolicy is frozen. Cannot add allowed command.")
        if command and command not in self._allowed_commands:
            self._allowed_commands.append(command.strip())
            logger.info(f"[SecurityPolicy] Added allowed command: {command}")
            return True
        return False


class CapabilityToken:
    def __init__(self, resource: str, permissions: List[str]):
        self.resource = resource
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def __repr__(self) -> str:
        return f"CapabilityToken(resource={self.resource}, permissions={self.permissions})"


class SecurityModule:
    def __init__(self, secure_memory: Optional[Any] = None, secure_runner: Optional[Any] = None):
        self.policy = SecurityPolicy()
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner
        self._audit_log: List[Dict[str, Any]] = []
        logger.info(f"[SecurityModule] Initialized. SecureMemory: {secure_memory is not None}")

    def set_secure_memory(self, secure_memory: Any) -> None:
        self._secure_memory = secure_memory
        logger.info("[SecurityModule] SecureMemoryStore attached.")

    def set_secure_runner(self, secure_runner: Any) -> None:
        self._secure_runner = secure_runner
        logger.info("[SecurityModule] SecureCommandRunner attached.")

    def validate_path(self, path: str) -> bool:
        try:
            if not path:
                return False
            abs_path = os.path.abspath(path)
            for allowed in self.policy.allowed_paths:
                if abs_path.startswith(allowed):
                    return True
            self.audit_log("validate_path", path, "DENIED")
            return False
        except Exception as e:
            logger.error(f"[SecurityModule] validate_path error: {e}")
            return False

    def validate_command(self, command: str) -> bool:
        """
        Validate a command by checking its first token (base command).
        Supports chained commands (e.g., "cd /app && git ...") – only the first token is checked.
        """
        try:
            if not command:
                return False
            # Simple whitespace split to get the first token
            parts = command.strip().split()
            if not parts:
                return False
            base_cmd = parts[0]
            if base_cmd in self.policy.allowed_commands:
                return True
            self.audit_log("validate_command", command, "DENIED")
            return False
        except Exception as e:
            logger.error(f"[SecurityModule] validate_command error: {e}")
            return False

    def audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None):
        log_entry = {"action": action, "resource": resource, "status": status, "details": details or {}}
        self._audit_log.append(log_entry)
        logger.info(f"Audit: {status.upper()} - Action='{action}' on Resource='{resource}'")
        if self._secure_memory:
            try:
                self._secure_memory.insert(
                    text=f"AUDIT: {action} on {resource}",
                    metadata={"type": "security_audit", "action": action, "resource": resource, "status": status, "details": details or {}}
                )
            except Exception as e:
                logger.warning(f"[SecurityModule] Failed to store audit entry: {e}")

    def sanitize_input(self, input_string: str, max_length: int = 2048) -> str:
        if not input_string:
            return ""
        try:
            if len(input_string) > max_length:
                logger.warning(f"[SecurityModule] Input truncated from {len(input_string)} to {max_length}")
                input_string = input_string[:max_length]
            return ''.join(c for c in input_string if 31 < ord(c) < 127 or c in '\n\r\t')
        except Exception as e:
            logger.error(f"[SecurityModule] sanitize_input error: {e}")
            return ""

    def get_audit_trail(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._audit_log[-limit:]

    def shutdown(self):
        logger.info("[SecurityModule] Shutting down.")
        self._audit_log.clear()
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[SecurityModule] Error closing secure memory: {e}")
