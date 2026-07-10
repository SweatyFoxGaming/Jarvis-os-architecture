"""
Ambient UI for JARVIS V3 – Phoenix Intelligence Platform.

Provides a dark‑themed, multi‑panel desktop interface for interacting with
the cognitive engine, monitoring system status, and issuing commands.
"""

import sys
import os
import logging
import traceback
from typing import Optional

# PyQt6 imports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QLabel, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QCoreApplication
from PyQt6.QtGui import QColor, QPalette, QFont

# System monitoring (with fallback)
try:
    import psutil
except ImportError:
    psutil = None

# Project imports (ensure path resolution)
from src.v2_main import CognitiveEngineV3
from src.core.security import SecurityModule
from src.memory.tiered_memory import HierarchicalMemory
from src.core.event_bus import EventBus

# Logger
logger = logging.getLogger(__name__)


# ---------- UI Components ----------
class Panel(QFrame):
    """
    A stylised panel with a title and a read‑only text display.
    """
    def __init__(self, title: str):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setStyleSheet(
            "border: 2px solid white; background-color: #0a0c10; color: white;"
        )

        layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Monospace", 10, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("border: none; background-color: transparent;")
        layout.addWidget(self.display)

        self.setLayout(layout)

    def append_text(self, text: str):
        """Append text to the display."""
        self.display.append(text)

    def clear(self):
        """Clear the display."""
        self.display.clear()


# ---------- Background Worker ----------
class JarvisWorker(QThread):
    """
    Worker thread for processing chat messages without freezing the GUI.
    """
    finished = pyqtSignal(str)      # Emits the final response
    error = pyqtSignal(str)         # Emits error messages

    def __init__(self, message: str, engine: CognitiveEngineV3):
        super().__init__()
        self.message = message
        self.engine = engine
        logger.debug(f"[JarvisWorker] Created for message: {message[:50]}...")

    def run(self):
        """Execute the engine's processing in a separate thread."""
        try:
            logger.info(f"[JarvisWorker] Processing: {self.message[:50]}...")
            response = self.engine.run(self.message)
            # Dispatch tasks to departments (non‑blocking)
            try:
                self.engine.dispatch_tasks()
            except Exception as e:
                logger.warning(f"[JarvisWorker] Task dispatch warning: {e}")
            self.finished.emit(response)
        except Exception as e:
            error_trace = traceback.format_exc()
            logger.error(f"[JarvisWorker] Error: {e}\n{error_trace}")
            self.error.emit(f"Internal error: {str(e)}")


# ---------- Main Window ----------
class AmbientUI(QMainWindow):
    """
    Main window for the JARVIS Ambient UI.
    """

    def __init__(
        self,
        engine: Optional[CognitiveEngineV3] = None,
        event_bus: Optional[EventBus] = None,
        secure_memory: Optional[SecureMemoryStore] = None,
        secure_runner: Optional[SecureCommandRunner] = None,
    ):
        super().__init__()
        self.engine = engine
        self.event_bus = event_bus
        self.secure_memory = secure_memory
        self.secure_runner = secure_runner

        # Worker reference
        self.worker: Optional[JarvisWorker] = None

        # Set up UI
        self._setup_ui()

        # Start status polling timer
        self.sentinel_timer = QTimer()
        self.sentinel_timer.timeout.connect(self.poll_system)
        self.sentinel_timer.start(2000)  # every 2 seconds

        # Log initialization
        logger.info("[AmbientUI] Initialized.")

    def _setup_ui(self):
        """Build the user interface."""
        self.setWindowTitle("JARVIS - Phoenix OS Ambient UI")
        self.resize(1024, 768)

        # Dark theme
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(10, 12, 16))
        self.setPalette(palette)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left column: Command and Chat panels
        left_layout = QVBoxLayout()

        self.command_panel = Panel("COMMAND SYSTEM")
        self.chat_panel = Panel("JARVIS CHAT")

        # Command input
        self.command_input = QLineEdit()
        self.command_input.setStyleSheet(
            "background-color: #0a0c10; color: #00ffff; border: 1px solid white;"
        )
        self.command_input.returnPressed.connect(self.submit_command)
        self.command_panel.layout().addWidget(self.command_input)

        # Chat input
        self.chat_input = QLineEdit()
        self.chat_input.setStyleSheet(
            "background-color: #0a0c10; color: white; border: 1px solid white;"
        )
        self.chat_input.returnPressed.connect(self.submit_chat)
        self.chat_panel.layout().addWidget(self.chat_input)

        left_layout.addWidget(self.command_panel)
        left_layout.addWidget(self.chat_panel)

        # Right panel: System status
        self.status_panel = Panel("SYSTEM STATUS")
        self.status_panel.setFixedWidth(300)

        main_layout.addLayout(left_layout, stretch=2)
        main_layout.addWidget(self.status_panel, stretch=1)

    # ---------- Event Handlers ----------
    def submit_chat(self):
        """Handle chat message submission."""
        text = self.chat_input.text().strip()
        if not text:
            return
        self.chat_input.clear()

        # Display user message
        self.chat_panel.append_text(f"<b>You:</b> {text}")
        self.chat_panel.append_text("<b>JARVIS:</b> ")

        # Check if engine is available
        if self.engine is None:
            self.chat_panel.append_text("[ERROR] Engine not initialized.")
            return

        # Cancel any running worker
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()

        # Start new worker
        self.worker = JarvisWorker(text, self.engine)
        self.worker.finished.connect(self.finalize_response)
        self.worker.error.connect(self.handle_worker_error)
        self.worker.start()

    def finalize_response(self, full_response: str):
        """Append the final response from the worker."""
        # The response might already be printed; we add it to the chat.
        # The worker already emitted the response, we can display it.
        # For better UX, we overwrite the "JARVIS: " line with the full response.
        # Since we can't easily replace text, we'll just append.
        self.chat_panel.append_text(full_response)

    def handle_worker_error(self, error_msg: str):
        """Handle errors from the worker thread."""
        self.chat_panel.append_text(f"[ERROR] {error_msg}")
        logger.error(f"[AmbientUI] Worker error: {error_msg}")

    def submit_command(self):
        """Handle system command submission."""
        cmd = self.command_input.text().strip()
        if not cmd:
            return
        self.command_input.clear()
        self.command_panel.append_text(f"> {cmd}")

        if self.engine is None:
            self.command_panel.append_text("[ERROR] Engine not initialized.")
            return

        # Process command via the engine (synchronous, but commands are quick)
        try:
            res = self.engine.run(f"SYSTEM: {cmd}")
            self.engine.dispatch_tasks()
            self.command_panel.append_text(res)
        except Exception as e:
            logger.error(f"[AmbientUI] Command error: {e}", exc_info=True)
            self.command_panel.append_text(f"[ERROR] {e}")

    def poll_system(self):
        """Update the system status panel."""
        if psutil is None:
            self.status_panel.display.setText("psutil not installed.")
            return

        try:
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            stats = {
                "CPU Usage": f"{cpu}%",
                "RAM Available": f"{mem.available // (1024*1024)} MB",
                "RAM Used": f"{mem.percent}%",
                "Disk Usage": f"{disk.percent}%",
                "Active Threads": f"{psutil.cpu_count() * 2 if psutil.cpu_count() else 'N/A'}",
                "OS": os.uname().sysname if hasattr(os, 'uname') else "Unknown",
            }
            # Update status panel
            self.status_panel.clear()
            for key, val in stats.items():
                self.status_panel.append_text(f"{key}: {val}")
        except Exception as e:
            logger.warning(f"[AmbientUI] System poll error: {e}")

    # ---------- Shutdown ----------
    def closeEvent(self, event):
        """Handle window close event – clean shutdown."""
        logger.info("[AmbientUI] Closing window...")

        # Stop timer
        if self.sentinel_timer:
            self.sentinel_timer.stop()

        # Terminate worker if running
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()

        # Shutdown engine if available
        if self.engine and hasattr(self.engine, 'shutdown'):
            try:
                self.engine.shutdown()
            except Exception as e:
                logger.warning(f"[AmbientUI] Engine shutdown error: {e}")

        # Close any secure memory connections
        if self.secure_memory and hasattr(self.secure_memory, 'close'):
            try:
                self.secure_memory.close()
            except Exception as e:
                logger.warning(f"[AmbientUI] Secure memory close error: {e}")

        event.accept()


# ---------- Application Entry Point ----------
def run_gui(engine: Optional[CognitiveEngineV3] = None):
    """
    Launch the GUI application.
    If engine is None, it will be created with default components.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS V3")
    app.setStyle("Fusion")  # consistent cross‑platform style

    # If no engine provided, instantiate with secure components (if available)
    if engine is None:
        logger.info("[run_gui] Creating default engine...")
        try:
            # Import secure components (they should be available)
            from src.core.security import SecurityModule
            from src.core.event_bus import EventBus
            from src.core.digital_twin import DigitalTwin
            from src.memory.tiered_memory import HierarchicalMemory
            from config.secure_config import AppConfig
            AppConfig.load()  # ensure .env loaded

            # Create components
            secure_memory = None
            try:
                from memory.secure_store import SecureMemoryStore
                secure_memory = SecureMemoryStore("data/memory.db")
            except ImportError:
                pass

            event_bus = EventBus()
            if secure_memory:
                event_bus.set_secure_memory(secure_memory)

            twin = DigitalTwin(secure_memory=secure_memory)
            # Build engine with these components (implementation may vary)
            # For now, we'll assume CognitiveEngineV3 can accept them via setter
            engine = CognitiveEngineV3()
            if hasattr(engine, 'set_secure_memory') and secure_memory:
                engine.set_secure_memory(secure_memory)
            if hasattr(engine, 'set_secure_runner'):
                # secure_runner is not defined here, but we can pass None
                pass

        except Exception as e:
            logger.error(f"[run_gui] Failed to create engine: {e}", exc_info=True)
            QMessageBox.critical(None, "Startup Error", f"Could not initialize JARVIS engine:\n{e}")
            return

    window = AmbientUI(
        engine=engine,
        event_bus=event_bus if 'event_bus' in locals() else None,
        secure_memory=secure_memory if 'secure_memory' in locals() else None,
    )
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    # This allows running the GUI standalone (e.g., `python -m src.gui`)
    run_gui()
