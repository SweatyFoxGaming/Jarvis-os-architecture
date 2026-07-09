import sys
import os
from dotenv import load_dotenv

# Ensure the project root is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.v2_main import CognitiveEngineV3
from src.gui import AmbientUI
from PyQt6.QtWidgets import QApplication

def get_base_path():
    """ Get absolute path to base directory, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_resource_path(relative_path):
    return os.path.join(get_base_path(), relative_path)

import logging

def main():
    # Set app identity
    os.environ["APP_IDENTITY"] = "JARVIS-COGNITIVE-ENGINE-V3"

    # Setup logging
    log_path = "/tmp/jarvis_startup.log"
    logging.basicConfig(filename=log_path, level=logging.DEBUG, 
                        format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("JARVIS V3 Starting up...")

    # Setup absolute pathing for standalone execution
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.chdir("..") # Go to project root

    load_dotenv()
    
    print("--- JARVIS V3: Executive Mind Architecture ---")
    
    # Default to GUI if run without terminal
    is_terminal = sys.stdin.isatty()

    if not is_terminal:
        logging.info("Non-terminal environment detected. Launching GUI.")
        app = QApplication(sys.argv)
        engine_v3 = CognitiveEngineV3()
        window = AmbientUI(engine_v3)
        window.show()
        sys.exit(app.exec())

    # Terminal Logic
    engine_v3 = CognitiveEngineV3()
    
    print("\nSelect Interface:")
    print("[1] Desktop GUI")
    print("[2] Terminal CLI")
    print("[3] Web Dashboard")
    i_choice = input("Choice: ").strip()
    
    if i_choice == '1':
        app = QApplication(sys.argv)
        window = AmbientUI(engine_v3)
        window.show()
        sys.exit(app.exec())
    elif i_choice == '3':
        import uvicorn
        print("Launching Web Dashboard on http://localhost:8000")
        uvicorn.run("src.api:app", host="0.0.0.0", port=8000, reload=False)
        sys.exit(0)

    while True:
        print("\nJARVIS V3 Executive Terminal")
        try:
            user_input = input("Request (q to quit): ").strip()
        except EOFError:
            break
        if user_input.lower() == 'q':
            break
        
        print("\nExecutive Mind Reasoning...")
        res = engine_v3.run(user_input)
        results = engine_v3.dispatch_tasks()
        
        print(f"\n[Mind] Decision: {res}")
        if results:
            for task_id, output in results.items():
                print(f"\n[Specialist Output]:\n{output}")

if __name__ == "__main__":
    main()
