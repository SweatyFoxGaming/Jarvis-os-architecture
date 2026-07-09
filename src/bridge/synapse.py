from typing import Any, Dict, Optional
from src.core.security import SecurityModule

class SynapseInterface:
    """
    The exclusive, deterministic gateway to Phoenix OS internals.
    """
    def __init__(self, security: SecurityModule):
        self.security = security

    def read_file(self, path: str) -> Optional[str]:
        if not self.security.validate_path(path):
            self.security.audit_log("read_file", path, "denied")
            return None

        try:
            self.security.audit_log("read_file", path, "approved")
            with open(path, 'r') as f:
                return f.read()
        except Exception as e:
            return f"Error: {e}"

    def write_file(self, path: str, content: str) -> bool:
        if not self.security.validate_path(path):
            self.security.audit_log("write_file", path, "denied")
            return False

        try:
            self.security.audit_log("write_file", path, "approved")
            with open(path, 'w') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Write error: {e}")
            return False

    def execute_command(self, command: str) -> str:
        if not self.security.validate_command(command):
            self.security.audit_log("execute_command", command, "denied")
            return "Security Denial: Command not allowed."

        # Placeholder for actual subprocess call
        self.security.audit_log("execute_command", command, "approved")
        return f"Simulated output for: {command}"
