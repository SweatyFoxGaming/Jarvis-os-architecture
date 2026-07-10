"""
SecureCommandRunner – Safe subprocess execution with whitelist and audit logging.
"""

import subprocess
import shlex
import logging
import os
import time
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class SecureCommandRunner:
    """
    Executes system commands with strict security controls.
    - Whitelist only
    - shell=False
    - Argument sanitization
    - Audit logging
    - Timeout support
    """

    # ---------- Whitelist of allowed commands ----------
    ALLOWED_COMMANDS = {
        "ls", "grep", "cat", "echo", "pwd", "mkdir", "rm", "cp", "mv", "head", "tail", "wc", "sort", "uniq", "find"
    }

    # ---------- Forbidden patterns in arguments ----------
    FORBIDDEN_PATTERNS = [
        ";", "&&", "||", "|", ">", "<", ">>", "<<", "`", "$(", "${", "(", ")", "[", "]", "{", "}", "&"
    ]

    def __init__(self, secure_memory=None):
        """
        Initialize the runner with optional secure memory for audit logging.
        """
        self._secure_memory = secure_memory
        self._audit_log: List[Dict[str, Any]] = []
        logger.info("[SecureCommandRunner] Initialized.")

    def set_secure_memory(self, secure_memory):
        """Inject secure memory for audit logging."""
        self._secure_memory = secure_memory
        logger.info("[SecureCommandRunner] SecureMemoryStore attached.")

    # ---------- Sanitization ----------
    @staticmethod
    def _sanitize_args(args: List[str]) -> List[str]:
        """
        Check each argument for forbidden patterns.
        Raises ValueError if a pattern is found.
        """
        for arg in args:
            for pattern in SecureCommandRunner.FORBIDDEN_PATTERNS:
                if pattern in arg:
                    raise ValueError(f"Argument contains forbidden pattern: '{pattern}' in '{arg}'")
        return args

    # ---------- Execution ----------
    def run_safe(self, command_args: List[str], timeout: int = 30, cwd: Optional[str] = None) -> str:
        """
        Execute a command with a list of arguments.
        Returns stdout+stderr or an error message.
        """
        if not command_args:
            return "Error: Empty command."

        command_name = command_args[0]
        if command_name not in self.ALLOWED_COMMANDS:
            msg = f"Command '{command_name}' is not allowed."
            logger.warning(f"[SecureCommandRunner] {msg}")
            self._audit_log("run_safe", command_name, "DENIED", {"args": command_args})
            return f"Security Denial: {msg}"

        # Sanitize the arguments
        try:
            safe_args = self._sanitize_args(command_args[1:])
        except ValueError as e:
            logger.warning(f"[SecureCommandRunner] Argument sanitization failed: {e}")
            self._audit_log("run_safe", command_name, "DENIED", {"args": command_args, "reason": str(e)})
            return f"Security Denial: {e}"

        full_command = [command_name] + safe_args
        logger.info(f"[SecureCommandRunner] Executing: {' '.join(full_command)}")
        self._audit_log("run_safe", command_name, "APPROVED", {"args": full_command})

        try:
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                shell=False,          # <-- CRITICAL: prevents injection
                timeout=timeout,
                cwd=cwd,
                check=False,
            )
            output = result.stdout + result.stderr
            if result.returncode != 0:
                logger.warning(f"[SecureCommandRunner] Command '{command_name}' exited with code {result.returncode}")
                self._audit_log("run_safe", command_name, "FAILED", {"returncode": result.returncode, "output": output[:200]})
                return f"Command failed (code {result.returncode}): {output.strip()}"
            else:
                self._audit_log("run_safe", command_name, "SUCCESS", {"output_preview": output[:200]})
                return output.strip()

        except subprocess.TimeoutExpired:
            logger.error(f"[SecureCommandRunner] Command '{command_name}' timed out after {timeout}s")
            self._audit_log("run_safe", command_name, "TIMEOUT", {"timeout": timeout})
            return f"Error: Command timed out after {timeout} seconds."

        except Exception as e:
            logger.error(f"[SecureCommandRunner] Execution error: {e}", exc_info=True)
            self._audit_log("run_safe", command_name, "ERROR", {"error": str(e)})
            return f"Error executing command: {e}"

    # ---------- Convenience: run from string ----------
    def run_from_string(self, user_input: str, timeout: int = 30, cwd: Optional[str] = None) -> str:
        """
        Parse a user string and execute safely.
        """
        try:
            args = shlex.split(user_input)
        except ValueError as e:
            logger.warning(f"[SecureCommandRunner] Failed to parse user input: {e}")
            return f"Error: Invalid command syntax – {e}"
        if not args:
            return "Error: No command provided."
        return self.run_safe(args, timeout, cwd)

    # ---------- Audit Helpers ----------
    def _audit_log(self, action: str, command: str, status: str, details: Optional[Dict[str, Any]] = None):
        """Internal audit logging to memory and secure memory."""
        log_entry = {
            "timestamp": time.time(),
            "action": action,
            "command": command,
            "status": status,
            "details": details or {},
        }
        self._audit_log.append(log_entry)

        # Log to standard logger
        logger.info(f"[Audit] {status.upper()}: {action} on command '{command}'")

        # Store in secure memory if available
        if self._secure_memory:
            try:
                self._secure_memory.insert(
                    text=f"AUDIT: {action} on {command} – {status}",
                    metadata={"type": "command_audit", "action": action, "command": command, "status": status, "details": details or {}}
                )
            except Exception as e:
                logger.warning(f"[SecureCommandRunner] Failed to store audit in secure memory: {e}")

    def get_audit_trail(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the last `limit` audit entries."""
        return self._audit_log[-limit:]

    def shutdown(self):
        """Clean up resources."""
        logger.info("[SecureCommandRunner] Shutting down.")
        self._audit_log.clear()
        if self._secure_memory and hasattr(self._secure_memory, 'close'):
            try:
                self._secure_memory.close()
            except Exception as e:
                logger.warning(f"[SecureCommandRunner] Error closing secure memory: {e}")
        self._secure_memory = None
