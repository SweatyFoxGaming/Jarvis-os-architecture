from typing import List, Dict, Any, Optional
import os
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class SecurityPolicy:
    def __init__(self):
        # Strict sandboxing for Phoenix OS
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.allowed_paths: List[str] = [
            os.path.join(base_dir, "data"),
            os.path.join(base_dir, "tmp"),
            "/tmp/jarvis"
        ]
        self.allowed_commands: List[str] = ["ls", "grep", "cat", "echo"]

        # Ensure allowed paths exist
        for path in self.allowed_paths:
            try:
                os.makedirs(path, exist_ok=True)
            except:
                pass

class CapabilityToken:
    def __init__(self, resource: str, permissions: List[str]):
        self.resource = resource
        self.permissions = permissions

class SecurityModule:
    def __init__(self):
        self.policy = SecurityPolicy()

    def validate_path(self, path: str) -> bool:
        abs_path = os.path.abspath(path)
        for allowed in self.policy.allowed_paths:
            if abs_path.startswith(allowed):
                return True
        return False

    def validate_command(self, command: str) -> bool:
        base_cmd = command.split()[0]
        return base_cmd in self.policy.allowed_commands

    def audit_log(self, action: str, resource: str, status: str):
        print(f"[Audit] {status.upper()}: Action='{action}' on Resource='{resource}'")
