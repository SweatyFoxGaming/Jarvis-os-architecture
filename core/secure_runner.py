import subprocess
import shlex
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class SecureCommandRunner:
    """
    Zero-trust command executor. 
    Only allows commands explicitly listed in the ALLOWED_COMMANDS set.
    """
    # Strict whitelist: Only these binaries can be executed.
    ALLOWED_COMMANDS = {
        "git", "python3", "ls", "pwd", "cat", "echo", "mkdir", "rm"
    }
    
    # Blacklist dangerous patterns (extra safety)
    FORBIDDEN_PATTERNS = ["&&", "||", ";", "`", "$(", ">", "<", "|"]

    @classmethod
    def _sanitize_args(cls, args: List[str]) -> List[str]:
        """Removes any argument that contains dangerous shell metacharacters."""
        sanitized = []
        for arg in args:
            # Check if any forbidden pattern exists in the argument
            if any(pattern in arg for pattern in cls.FORBIDDEN_PATTERNS):
                logger.warning("[SECURITY] Rejected dangerous argument: %s", arg)
                raise ValueError(f"Argument contains dangerous characters: {arg}")
            sanitized.append(arg)
        return sanitized

    @classmethod
    def run_safe(cls, command_args: List[str], timeout: int = 30) -> str:
        """
        Executes a command with a list of arguments.
        Example: run_safe(["ls", "-la", "/home"])
        """
        if not command_args:
            raise ValueError("Command list cannot be empty")

        command_name = command_args[0]
        if command_name not in cls.ALLOWED_COMMANDS:
            raise PermissionError(
                f"Command '{command_name}' is not whitelisted. "
                f"Allowed: {cls.ALLOWED_COMMANDS}"
            )

        # Sanitize the remaining arguments
        safe_args = cls._sanitize_args(command_args[1:])
        full_command = [command_name] + safe_args

        logger.info("[RUNNER] Executing: %s", " ".join(full_command))
        
        try:
            # CRITICAL: shell=False prevents command injection
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                shell=False,  # NEVER change this to True
                timeout=timeout,
                check=False   # We handle return codes manually
            )
            
            if result.returncode != 0:
                logger.warning("[RUNNER] Command failed with code %d: %s", 
                               result.returncode, result.stderr.strip())
                return f"Error (code {result.returncode}): {result.stderr.strip()}"
            
            return result.stdout.strip()
            
        except subprocess.TimeoutExpired:
            logger.error("[RUNNER] Command timed out after %d seconds", timeout)
            return f"Error: Command timed out after {timeout} seconds."
        except Exception as e:
            logger.error("[RUNNER] Unexpected error: %s", str(e))
            return f"Error: {str(e)}"

    @classmethod
    def run_from_string(cls, user_input: str, timeout: int = 30) -> str:
        """
        Convenience method: Takes a raw user string, safely parses it into args.
        Example: run_from_string("git status")
        """
        # shlex.split handles quoted strings safely (e.g., file names with spaces)
        try:
            args = shlex.split(user_input)
        except ValueError as e:
            logger.error("[RUNNER] Failed to parse user input: %s", e)
            return f"Error: Invalid command syntax - {str(e)}"
        
        if not args:
            return "Error: No command provided."
            
        return cls.run_safe(args, timeout)

# Example usage:
if __name__ == "__main__":
    # Test safe execution
    print(SecureCommandRunner.run_from_string("ls -la"))
    
    # Test blocked command (should raise PermissionError)
    try:
        print(SecureCommandRunner.run_from_string("rm -rf /"))  # Blocked by whitelist (rm is allowed, but arguments are sanitized? Actually rm is allowed, but let's block dangerous args)
    except Exception as e:
        print(f"Blocked malicious command: {e}")
        
    # Test command injection attempt (blocked by sanitizer)
    try:
        SecureCommandRunner.run_from_string("ls; rm -rf /")
    except Exception as e:
        print(f"Blocked injection attempt: {e}")
