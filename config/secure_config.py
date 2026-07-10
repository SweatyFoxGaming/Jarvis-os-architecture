import os
from pathlib import Path
from dotenv import load_dotenv

class AppConfig:
    _initialized = False
    BRAVE_API_KEY: str = None
    OPENAI_API_KEY: str = None
    INTERNAL_API_KEY: str = None  # <-- ADDED

    @classmethod
    def load(cls):
        if cls._initialized:
            return

        env_path = Path.cwd() / ".env"
        if not env_path.exists():
            env_path = Path(__file__).parent.parent / ".env"

        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
            print(f"[CONFIG] Loaded .env from {env_path}")
        else:
            print("[CONFIG] WARNING: No .env file found. Trying system environment variables.")
            load_dotenv()

        cls.BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")
        cls.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        cls.INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")  # <-- ADDED

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
        # INTERNAL_API_KEY is optional – we only warn if missing
        if not cls.INTERNAL_API_KEY:
            print("[CONFIG] WARNING: INTERNAL_API_KEY not set. API authentication will fall back to OPENAI_API_KEY or dev mode.")
        else:
            print("[CONFIG] INTERNAL_API_KEY loaded successfully.")

        cls._initialized = True
        print("[CONFIG] Configuration validated successfully.")

if __name__ == "__main__":
    AppConfig.load()
    print(f"Brave Key loaded: {AppConfig.BRAVE_API_KEY[:5]}...")
    print(f"Internal API Key loaded: {AppConfig.INTERNAL_API_KEY[:8] if AppConfig.INTERNAL_API_KEY else 'Not set'}")
