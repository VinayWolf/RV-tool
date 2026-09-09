from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit
from PyQt6.QtCore import Qt

class ConsoleDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Integrated Terminal", parent)
        
        console_widget = QWidget()
        layout = QVBoxLayout(console_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        console_toolbar = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("background-color: #333; color: #ccc; border-radius: 4px; padding: 4px 12px;")
        clear_btn.clicked.connect(lambda: self.console_output.clear())
        console_toolbar.addStretch()
        console_toolbar.addWidget(clear_btn)
        
        self.console_output = QTextEdit()
        self.console_output.setObjectName("consolePane")
        self.console_output.setReadOnly(True)
        self.console_output.setStyleSheet("font-family: 'Consolas', monospace; font-size: 13px; background-color: #181818;")
        
        layout.addLayout(console_toolbar)
        layout.addWidget(self.console_output)
        
        self.setWidget(console_widget)

    def log_to_console(self, module, message, level="info"):
        colors = {"info": "#4facf7", "warn": "#d7ba7d", "error": "#f44747", "emu": "#4caf50"}
        color = colors.get(level, "#ffffff")
        html_msg = f"<span style='color: {color}; font-weight: bold;'>[{module}]</span> <span style='color: #cccccc;'>{message}</span>"
        self.console_output.append(html_msg)
        self.console_output.verticalScrollBar().setValue(self.console_output.verticalScrollBar().maximum())
