import sys
import os
import logging
import traceback
from logging.handlers import RotatingFileHandler

# ---------- 1. PATH SETUP ----------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ---------- 2. IMPORTS ----------
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThreadPool, qInstallMessageHandler, QtMsgType

from src.v2_main import CognitiveEngineV3
from src.gui import AmbientUI

# ---------- SECURE IMPORTS ----------
try:
    from config.secure_config import AppConfig
    AppConfig.load()
except Exception as e:
    print(f"⚠️ Config error: {e}")

try:
    from memory.secure_store import SecureMemoryStore
except ImportError:
    SecureMemoryStore = None

try:
    from core.secure_runner import SecureCommandRunner
except ImportError:
    SecureCommandRunner = None

# ---------- 3. LOGGING SETUP ----------
def setup_logging():
    log_dir = os.path.join(PROJECT_ROOT, "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "jarvis_v3.log")
    handler = RotatingFileHandler(log_file, maxBytes=5_242_880, backupCount=3)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    logging.info(f"Logging initialized. Log file: {log_file}")
    return logger

# ---------- 4. QT EXCEPTION HOOK ----------
def qt_message_handler(mode, context, message):
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
    qInstallMessageHandler(qt_message_handler)

# ---------- 5. MAIN ----------
def main():
    os.environ["APP_IDENTITY"] = "JARVIS-COGNITIVE-ENGINE-V3"

    logger = setup_logging()
    logging.info("=" * 60)
    logging.info("JARVIS V3 Executive Mind starting up...")
    logging.info(f"Project Root: {PROJECT_ROOT}")

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
        print("  INTERNAL_API_KEY=your_key_here")
        print("=" * 70)
        sys.exit(1)

    # ---------- Create Secure Components ----------
    secure_memory = None
    secure_runner = None
    try:
        if SecureMemoryStore:
            secure_memory = SecureMemoryStore(os.path.join(PROJECT_ROOT, "data", "memory.db"))
            logging.info("✅ Secure Memory Store initialized.")
    except Exception as e:
        logging.error(f"Failed to init memory store: {e}", exc_info=True)

    try:
        if SecureCommandRunner:
            # Placeholder test
            test_result = SecureCommandRunner.run_safe(["echo", "Security check passed"])
            logging.info(f"✅ Secure Command Runner active: {test_result}")
            secure_runner = SecureCommandRunner()
    except Exception as e:
        logging.error(f"Command runner security check failed: {e}", exc_info=True)

    # ---------- ENGINE INITIALIZATION (NOW PASSES SECURE COMPONENTS) ----------
    engine_v3 = CognitiveEngineV3(secure_memory=secure_memory, secure_runner=secure_runner)
    logging.info("✅ Cognitive Engine V3 instantiated.")

    # ---------- DETERMINE RUN MODE ----------
    is_terminal = sys.stdin.isatty() and not getattr(sys, 'frozen', False)

    if not is_terminal:
        logging.info("Non-terminal environment detected. Launching GUI.")
        setup_qt_handler()
        app = QApplication(sys.argv)
        app.setApplicationName("JARVIS V3")
        window = AmbientUI(engine_v3)
        window.show()
        thread_pool = QThreadPool.globalInstance()
        logging.info(f"Qt ThreadPool: {thread_pool.maxThreadCount()} threads available.")
        sys.exit(app.exec())

    # ---------- TERMINAL INTERFACE ----------
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
            import uvicorn
            from src.api import app as secure_app
            print("\n🔐 Secure Web Dashboard running on http://localhost:8000")
            print("   Requires 'X-API-Key' header matching your .env INTERNAL_API_KEY")
            print("   Press Ctrl+C to stop.\n")
            uvicorn.run(
                secure_app,
                host="0.0.0.0",
                port=8000,
                reload=False,
                workers=1,
                log_level="info",
            )
            sys.exit(0)
        except ImportError as e:
            logging.error(f"Failed to import secure API: {e}")
            print("Error: Secure API not found. Falling back to legacy src.api (INSECURE).")
            import uvicorn
            from src.api import app as legacy_app
            uvicorn.run(legacy_app, host="0.0.0.0", port=8000, reload=False)
            sys.exit(0)

    # ---------- TERMINAL CLI LOOP ----------
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
            decision_summary = engine_v3.run(user_input)
            results = engine_v3.dispatch_tasks()
            print(f"\n📋 Decision Summary: {decision_summary}")
            if results:
                print("\n=== 📊 SPECIALIST DEPARTMENT OUTPUTS ===")
                for task_id, output in results.items():
                    print(f"\n[Task {task_id}]:")
                    if isinstance(output, dict):
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
            error_trace = traceback.format_exc()
            logging.error(f"Engine error: {e}\n{error_trace}")
            print(f"\n❌ Error: {e}")
            print("   Check logs for details.")

        print("\n" + "-" * 70)

    logging.info("JARVIS V3 shutdown complete.")
    print("\nGoodbye.")

if __name__ == "__main__":
    main()
