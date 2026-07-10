# src/bridge/synapse.py (reinforced)

import os
import subprocess
import shlex
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SynapseInterface:
    """
    The exclusive, deterministic gateway to Phoenix OS internals.
    This interface is IMMUTABLE – its security policy cannot be changed at runtime.
    """
    def __init__(self, security_module, secure_memory=None, secure_runner=None):
        if security_module is None:
            raise ValueError("security_module cannot be None")
        self._security = security_module
        self._secure_memory = secure_memory
        self._secure_runner = secure_runner

        # Freeze the security policy to prevent any runtime changes
        self._security.policy.freeze()
        logger.info("[SynapseInterface] Security policy frozen. Gateway is now immutable.")

        # Store a copy of allowed paths/commands for fast access (read-only)
        self._allowed_paths = self._security.policy.allowed_paths
        self._allowed_commands = self._security.policy.allowed_commands
        logger.info(f"[SynapseInterface] Allowed paths: {len(self._allowed_paths)}")
        logger.info(f"[SynapseInterface] Allowed commands: {self._allowed_commands}")

    def _audit_log(self, action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None):
        # ... same as before ...

    def read_file(self, path: str) -> Optional[str]:
        # Implementation unchanged, but relies on frozen policy
        if not self._security.validate_path(path):
            self._audit_log("read_file", path, "DENIED")
            return None
        # ... rest

    def write_file(self, path: str, content: str) -> bool:
        # ... same ...

    def execute_command(self, command: str, timeout: int = 30) -> str:
        """
        Execute a command ONLY if it passes the immutable security policy.
        The LLM never influences this decision.
        """
        if not command:
            return "Error: No command provided."

        # Validate command against the frozen whitelist
        if not self._security.validate_command(command):
            self._audit_log("execute_command", command, "DENIED_BY_IMMUTABLE_POLICY")
            return "SECURITY DENIAL: Command not allowed by immutable system policy."

        self._audit_log("execute_command", command, "APPROVED")

        # Execute using SecureCommandRunner if available, otherwise fallback
        try:
            if self._secure_runner is not None:
                args = shlex.split(command)
                result = self._secure_runner.run_safe(args, timeout=timeout)
                return result
            else:
                # Use subprocess with shell=False (safe)
                args = shlex.split(command)
                # Additional check: ensure the base command is still in the whitelist
                # (redundant but defensive)
                if args[0] not in self._allowed_commands:
                    self._audit_log("execute_command", command, "DENIED_BY_RUNTIME_CHECK")
                    return "SECURITY DENIAL: Command base not allowed."
                result = subprocess.run(
                    args,
                    capture_output=True,
                    text=True,
                    shell=False,
                    timeout=timeout,
                )
                output = result.stdout + result.stderr
                if result.returncode != 0:
                    return f"Command failed (code {result.returncode}): {output.strip()}"
                return output.strip()
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {timeout} seconds."
        except Exception as e:
            logger.error(f"[SynapseInterface] Command execution error: {e}", exc_info=True)
            return f"Error executing command: {e}"

    # No setter methods for allowed paths/commands – they are immutable.
    # Attempts to add/modify will be rejected.
