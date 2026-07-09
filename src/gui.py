import sys
import os
import psutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QLineEdit, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QPalette, QFont

class Panel(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(2)
        self.setStyleSheet("border: 2px solid white; background-color: #0a0c10; color: white;")
        
        self.layout = QVBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Monospace", 10, QFont.Weight.Bold))
        self.layout.addWidget(self.title_label)
        
        self.display = QTextEdit()
        self.display.setReadOnly(True)
        self.display.setStyleSheet("border: none; background-color: transparent;")
        self.layout.addWidget(self.display)
        
        self.setLayout(self.layout)

class JarvisWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, message, engine):
        super().__init__()
        self.message = message
        self.engine = engine

    def run(self):
        # Run synchronous for now
        response = self.engine.run(self.message)
        self.engine.dispatch_tasks()
        self.finished.emit(response)

class AmbientUI(QMainWindow):
    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine
        self.setWindowTitle("JARVIS - Phoenix OS Ambient UI")
        self.resize(1024, 768)
        
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(10, 12, 16))
        self.setPalette(palette)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        
        self.left_layout = QVBoxLayout()
        self.command_panel = Panel("COMMAND SYSTEM")
        self.chat_panel = Panel("JARVIS CHAT")
        
        self.command_input = QLineEdit()
        self.command_input.setStyleSheet("background-color: #0a0c10; color: #00ffff; border: 1px solid white;")
        self.command_panel.layout.addWidget(self.command_input)
        
        self.chat_input = QLineEdit()
        self.chat_input.setStyleSheet("background-color: #0a0c10; color: white; border: 1px solid white;")
        self.chat_input.returnPressed.connect(self.submit_chat)
        self.chat_panel.layout.addWidget(self.chat_input)
        
        self.command_input.returnPressed.connect(self.submit_command)
        
        self.left_layout.addWidget(self.command_panel)
        self.left_layout.addWidget(self.chat_panel)
        
        self.status_panel = Panel("SYSTEM STATUS")
        self.status_panel.setFixedWidth(300)
        
        self.main_layout.addLayout(self.left_layout)
        self.main_layout.addWidget(self.status_panel)
        
        self.sentinel_timer = QTimer()
        self.sentinel_timer.timeout.connect(self.poll_system)
        self.sentinel_timer.start(2000)

    def poll_system(self):
        stats = {
            "CPU Usage": f"{psutil.cpu_percent()}%",
            "RAM Available": f"{psutil.virtual_memory().available // (1024*1024)} MB",
            "Disk Usage": f"{psutil.disk_usage('/').percent}%",
            "Active Threads": f"{psutil.cpu_count() * 2}",
            "OS": "Ubuntu (Linux Host)"
        }
        self.update_status(stats)
        
    def submit_chat(self):
        text = self.chat_input.text().strip()
        if not text: return
        self.chat_input.clear()
        self.add_chat("You", text)
        
        self.chat_panel.display.append(f"<b>JARVIS:</b> ")

        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()

        self.worker = JarvisWorker(text, self.engine)
        self.worker.finished.connect(self.finalize_response)
        self.worker.start()

    def finalize_response(self, full_response):
        self.chat_panel.display.append(full_response)

    def submit_command(self):
        cmd = self.command_input.text().strip()
        if not cmd: return
        self.command_input.clear()
        self.add_command_output(f"> {cmd}")
        
        res = self.engine.run(f"SYSTEM: {cmd}")
        self.engine.dispatch_tasks()
        self.add_command_output(res)

    def add_chat(self, sender, message):
        self.chat_panel.display.append(f"<b>{sender}:</b> {message}")
        
    def add_command_output(self, text):
        self.command_panel.display.append(text)

    def update_status(self, stats):
        self.status_panel.display.clear()
        for key, val in stats.items():
            self.status_panel.display.append(f"{key}: {val}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AmbientUI(None)
    window.show()
    sys.exit(app.exec())
