import sys
import os
import logging
import traceback
from logging.handlers import RotatingFileHandler

# ---------- 1. PATH SETUP (No more os.chdir hacks!) ----------
# Get the absolute project root ONCE and keep it.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------- 2. IMPORTS ----------
# Framework / GUI
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThreadPool, qInstallMessageHandler, QtMsgType

# Your core engine
from src.v2_main import CognitiveEngineV3
from src.gui import AmbientUI

# ---------- SECURE IMPORTS (Now actually used!) ----------
from config.secure_config import AppConfig
from memory.secure_store import SecureMemoryStore
from core.secure_runner import SecureCommandRunner

# ---------- 3. LOGGING SETUP (Rotating logs, not just /tmp) ----------
def setup_logging():
    """Configure rotating logs inside the project root."""
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "jarvis_v3.log")
    
    # Rotate logs when they hit 5 MB, keep 3 backups
    handler = RotatingFileHandler(
        log_file, maxBytes=5_242_880, backupCount=3
    )
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Root logger config
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    # Also print to console for CLI mode
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    
    logging.info(f"Logging initialized. Log file: {log_file}")
    return logger

# ---------- 4. RESOURCE PATH HELPER (For PyInstaller) ----------
def get_base_path():
    """Get absolute path to base directory, works for dev and PyInstaller."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return PROJECT_ROOT

def get_resource_path(relative_path):
    return os.path.join(get_base_path(), relative_path)

# ---------- 5. QT EXCEPTION HOOK (Prevents silent crashes in GUI) ----------
def qt_message_handler(mode, context, message):
    """Redirect Qt's debug/warning/error messages to Python logging."""
    if mode == QtMsgType.QtDebugMsg:
        logging.debug(f"Qt: {message}")
    elif mode == QtMsgType.QtInfoMsg:
        logging.info(f"Qt: {message}")
    elif mode == QtMsgType.QtWarningMsg:
        logging.warning(f"Qt: {message}")
    elif mode == QtMsgType.QtCriticalMsg:
        logging.critical(f"Qt: {message}")
    elif mode == QtMsgType.QtFatalMsg:
        logging.critical(f"Qt FATAL: {message}")
        sys.exit(1)

def setup_qt_handler():
    """Install the Qt message handler."""
    qInstallMessageHandler(qt_message_handler)

# ---------- 6. MAIN FUNCTION ----------
def main():
    # Set app identity early
    os.environ["APP_IDENTITY"] = "JARVIS-COGNITIVE-ENGINE-V3"
    
    # Setup logging first
    logger = setup_logging()
    logging.info("=" * 60)
    logging.info("JARVIS V3 Executive Mind starting up...")
    logging.info(f"Project Root: {PROJECT_ROOT}")

    # ---------- 7. SECURE CONFIG LOAD (CRITICAL FIX) ----------
    # We loaded the .env inside secure_config, but we need to ensure it's called.
    # AppConfig.load() is idempotent - safe to call multiple times.
    try:
        AppConfig.load()
        logging.info("✅ Secure configuration validated successfully.")
        logging.info(f"   OpenAI Key: {AppConfig.OPENAI_API_KEY[:8]}... (truncated)")
        logging.info(f"   Brave Key:  {AppConfig.BRAVE_API_KEY[:8]}... (truncated)")
    except ValueError as e:
        logging.critical(f"❌ Configuration error: {e}")
        print("\n" + "=" * 70)
        print("CRITICAL ERROR: Missing API Keys!")
        print("Please create a .env file in the project root with:")
        print("  BRAVE_API_KEY=your_key_here")
        print("  OPENAI_API_KEY=your_key_here")
        print("=" * 70)
        sys.exit(1)

    # ---------- 8. INITIALIZE SECURE COMPONENTS (Ready for engine) ----------
    # Even if the engine doesn't use them yet, we instantiate them to:
    #  - Create the database file early (so permissions are set)
    #  - Validate the whitelist at startup
    try:
        memory_store = SecureMemoryStore(db_path=os.path.join(PROJECT_ROOT, "data", "memory.db"))
        logging.info("✅ Secure Memory Store initialized.")
    except Exception as e:
        logging.error(f"Failed to init memory store: {e}", exc_info=True)
        # Non-fatal - engine might fall back.

    try:
        # Just test the runner to ensure the whitelist is loaded
        test_result = SecureCommandRunner.run_safe(["echo", "Security check passed"])
        logging.info(f"✅ Secure Command Runner active: {test_result}")
    except Exception as e:
        logging.error(f"Command runner security check failed: {e}", exc_info=True)
        # Non-fatal - we can still run without shell commands.

    # ---------- 9. ENGINE INITIALIZATION ----------
    # It's safe to pass the secure components if your CognitiveEngineV3 accepts them.
    # If not, we just create it as usual - but at least secrets are validated.
    engine_v3 = CognitiveEngineV3()
    logging.info("✅ Cognitive Engine V3 instantiated.")

    # ---------- 10. DETERMINE RUN MODE ----------
    # Detect if we are running in a terminal (CLI) or launched as a GUI app.
    is_terminal = sys.stdin.isatty() and not getattr(sys, 'frozen', False)

    # If not a terminal, force GUI mode (useful for .desktop shortcuts)
    if not is_terminal:
        logging.info("Non-terminal environment detected. Launching GUI.")
        setup_qt_handler()
        app = QApplication(sys.argv)
        app.setApplicationName("JARVIS V3")

        # (Optional) Inject secure components into the UI if it accepts them
        # window = AmbientUI(engine_v3, memory_store=memory_store)
        window = AmbientUI(engine_v3)
        window.show()
        
        # Set up QThreadPool globally if your engine/GUI uses it.
        # Your gui/async_worker.py uses QThreadPool.globalInstance() by default.
        thread_pool = QThreadPool.globalInstance()
        logging.info(f"Qt ThreadPool: {thread_pool.maxThreadCount()} threads available.")
        
        sys.exit(app.exec())

    # ---------- 11. TERMINAL INTERFACE ----------
    print("\n" + "=" * 70)
    print("  JARVIS V3: Executive Mind Architecture")
    print("  Secure Configuration: ✅ Active")
    print("=" * 70)
    print("\nSelect Interface:")
    print("  [1] Desktop GUI")
    print("  [2] Terminal CLI (Default)")
    print("  [3] Web Dashboard (Secure API)")
    
    i_choice = input("Choice: ").strip() or '2'
    
    if i_choice == '1':
        setup_qt_handler()
        app = QApplication(sys.argv)
        window = AmbientUI(engine_v3)
        window.show()
        sys.exit(app.exec())
        
    elif i_choice == '3':
        logging.info("Launching Secure Web Dashboard...")
        try:
            # Use the SECURE API server we built earlier!
            # If you want to keep your old src.api, change this import, but the secure one is better.
            import uvicorn
            from api.secure_server import app as secure_app  # <-- Uses X-API-Key auth!
            
            print("\n🔐 Secure Web Dashboard running on http://localhost:8000")
            print("   Requires 'X-API-Key' header matching your .env OPENAI_API_KEY")
            print("   Press Ctrl+C to stop.\n")
            
            uvicorn.run(
                secure_app,  # <-- Imported from api.secure_server
                host="0.0.0.0",
                port=8000,
                reload=False,   # NEVER True in production
                workers=2,
                log_level="warning"
            )
            sys.exit(0)
        except ImportError as e:
            logging.error(f"Failed to import secure API: {e}")
            print("Error: Secure API not found. Falling back to legacy src.api (INSECURE).")
            import uvicorn
            from src.api import app as legacy_app
            uvicorn.run(legacy_app, host="0.0.0.0", port=8000, reload=False)
            sys.exit(0)

    # ---------- 12. TERMINAL CLI LOOP (with robust error handling) ----------
    print("\n" + "=" * 70)
    print("  JARVIS V3 Terminal CLI")
    print("  Type 'q' to quit, 'clear' to clear screen.")
    print("=" * 70)

    while True:
        try:
            user_input = input("\n📝 Request: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting...")
            break

        if not user_input:
            continue
            
        if user_input.lower() == 'q':
            print("Shutting down JARVIS...")
            break
            
        if user_input.lower() == 'clear':
            os.system('clear' if os.name == 'posix' else 'cls')
            continue

        print("\n🧠 [Executive Mind] Processing request...")
        try:
            # Run the engine
            decision_summary = engine_v3.run(user_input)
            results = engine_v3.dispatch_tasks()
            
            print(f"\n📋 Decision Summary: {decision_summary}")
            
            if results:
                print("\n=== 📊 SPECIALIST DEPARTMENT OUTPUTS ===")
                for task_id, output in results.items():
                    print(f"\n[Task {task_id}]:")
                    if isinstance(output, dict):
                        # Pretty print the dict
                        if "report" in output:
                            print(output["report"])
                        elif "code" in output:
                            print(output.get("code", output))
                        elif "error" in output:
                            print(f"⚠️ Error: {output['error']}")
                        else:
                            print(output)
                    else:
                        print(str(output))
            else:
                print("\n[Info] No specialist output generated.")
                
        except Exception as e:
            # Catch ALL errors so the CLI doesn't crash.
            error_trace = traceback.format_exc()
            logging.error(f"Engine error: {e}\n{error_trace}")
            print(f"\n❌ Error: {e}")
            print("   Check logs for details.")
            
        print("\n" + "-" * 70)

    logging.info("JARVIS V3 shutdown complete.")
    print("\nGoodbye.")

# ---------- 13. SCRIPT ENTRY POINT ----------
if __name__ == "__main__":
    main()
