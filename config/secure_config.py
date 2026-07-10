import os
from pathlib import Path
from dotenv import load_dotenv

class AppConfig:
    """
    Singleton-style configuration loader.
    Place a .env file in your project root with BRAVE_API_KEY and OPENAI_API_KEY.
    """
    _initialized = False
    BRAVE_API_KEY: str = None
    OPENAI_API_KEY: str = None

    @classmethod
    def load(cls):
        if cls._initialized:
            return

        # Look for .env in the parent directory of this file, or current working dir
        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            # Try going up one level (common in src/config setups)
            env_path = Path(__file__).parent.parent / ".env"

        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"[CONFIG] Loaded .env from {env_path}")
        else:
            print("[CONFIG] WARNING: No .env file found. Trying system environment variables.")
            load_dotenv()  # Fallback to system env

        cls.BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        
        # CRITICAL: No fallback values here. If missing, we crash loudly.
        if not cls.BRAVE_API_KEY:
            raise ValueError(
                "BRAVE_API_KEY not found in .env file. "
                "Create a .env file with BRAVE_API_KEY=your_key_here"
            )
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not found in .env file. "
                "Create a .env file with OPENAI_API_KEY=your_key_here"
            )
        
        cls._initialized = True
        print("[CONFIG] Configuration validated successfully.")

# Example usage (put this at the bottom of your main.py):
if __name__ == "__main__":
    # Simulate loading config at app startup
    AppConfig.load()
    print(f"Brave Key loaded: {AppConfig.BRAVE_API_KEY[:5]}...")
