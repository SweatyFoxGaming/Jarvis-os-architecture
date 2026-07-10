import sys
import traceback
from typing import Any, Callable, Tuple, Dict

from PyQt6.QtCore import QRunnable, QObject, pyqtSignal, QThreadPool, QCoreApplication
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QTextEdit

# ---------- Worker Signal & Class ----------
class WorkerSignals(QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = pyqtSignal(object)  # Emits the result (any type)
    error = pyqtSignal(str)        # Emits the error traceback
    progress = pyqtSignal(int)     # Optional: for progress bars

class GenericWorker(QRunnable):
    """
    Worker thread for running any long-running function (e.g., LLM calls, file I/O).
    """
    def __init__(self, fn: Callable, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        """
        This runs in the background thread. 
        DO NOT update GUI elements directly from here.
        """
        try:
            # Execute the target function
            result = self.fn(*self.args, **self.kwargs)
            # Emit the result back to the main thread
            self.signals.finished.emit(result)
        except Exception as e:
            # Capture the full traceback to show in the GUI
            error_msg = traceback.format_exc()
            self.signals.error.emit(error_msg)


# ---------- Mock LLM Engine (Simulates long processing) ----------
class MockLLMEngine:
    @staticmethod
    def generate(prompt: str) -> str:
        """Simulates a slow LLM call."""
        import time
        time.sleep(3)  # Simulate network/GPU latency
        return f"JARVIS Response to: {prompt}"


# ---------- Main GUI Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Async JARVIS")
        self.setGeometry(100, 100, 600, 400)

        # Initialize the LLM Engine (replace with your actual import)
        self.llm = MockLLMEngine()
        
        # Create a thread pool (manages all background tasks)
        self.threadpool = QThreadPool()
        print(f"[GUI] Multithreading with max {self.threadpool.maxThreadCount()} threads")

        # Setup UI
        layout = QVBoxLayout()
        
        self.input_field = QTextEdit()
        self.input_field.setPlaceholderText("Enter your command here...")
        layout.addWidget(self.input_field)

        self.send_btn = QPushButton("Send to JARVIS")
        self.send_btn.clicked.connect(self.on_send_clicked)
        layout.addWidget(self.send_btn)

        self.output_field = QTextEdit()
        self.output_field.setReadOnly(True)
        self.output_field.setPlaceholderText("Response will appear here...")
        layout.addWidget(self.output_field)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def on_send_clicked(self):
        """Handles the send button click. Disables button, starts worker."""
        prompt = self.input_field.toPlainText().strip()
        if not prompt:
            self.output_field.setText("Please enter a prompt.")
            return

        # Disable button to prevent multiple clicks
        self.send_btn.setEnabled(False)
        self.output_field.setText("[JARVIS] Thinking...")

        # Create a worker that calls self.llm.generate
        worker = GenericWorker(self.llm.generate, prompt)
        
        # Connect signals to GUI update functions
        worker.signals.finished.connect(self.on_response_received)
        worker.signals.error.connect(self.on_worker_error)
        
        # Start the worker in the background
        self.threadpool.start(worker)

    def on_response_received(self, response: str):
        """Slot called when the worker finishes successfully."""
        self.output_field.setText(response)
        self.send_btn.setEnabled(True)

    def on_worker_error(self, error_traceback: str):
        """Slot called when the worker crashes."""
        self.output_field.setText(f"ERROR:\n{error_traceback}")
        self.send_btn.setEnabled(True)


# ---------- Application Entry Point ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())