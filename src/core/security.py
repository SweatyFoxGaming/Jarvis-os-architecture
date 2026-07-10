# src/core/security.py (reinforced)

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
        self._allowed_paths: List[str] = [
            os.path.join(base_dir, "data"),
            os.path.join(base_dir, "tmp"),
            "/tmp/jarvis",
            os.path.join(base_dir, "logs"),
        ]
        self._allowed_commands: List[str] = ["ls", "grep", "cat", "echo", "pwd"]
        self._frozen = False

        # Ensure directories exist
        for path in self._allowed_paths:
            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                logger.warning(f"[SecurityPolicy] Could not create {path}: {e}")

    def freeze(self):
        """Make the policy immutable. Called once at startup."""
        self._frozen = True
        logger.info("[SecurityPolicy] Policy frozen. No further modifications allowed.")

    @property
    def allowed_paths(self) -> List[str]:
        return self._allowed_paths.copy()  # return a copy to prevent mutation

    @property
    def allowed_commands(self) -> List[str]:
        return self._allowed_commands.copy()

    def add_allowed_path(self, path: str) -> bool:
        if self._frozen:
            raise RuntimeError("SecurityPolicy is frozen. Cannot add allowed path.")
        # ... existing logic ...
        return True

    def add_allowed_command(self, command: str) -> bool:
        if self._frozen:
            raise RuntimeError("SecurityPolicy is frozen. Cannot add allowed command.")
        # ... existing logic ...
        return True
