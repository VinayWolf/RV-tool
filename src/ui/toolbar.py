from PyQt6.QtWidgets import QToolBar, QPushButton, QWidget, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal

class MainToolBar(QToolBar):
    run_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Main Toolbar", parent)
        self.setObjectName("topToolBar")
        self.setMovable(False)
        
        self.btn_play = QPushButton("▶ Run")
        self.btn_play.setObjectName("runBtn")
        self.btn_play.setStyleSheet("background-color: #2ea043; color: white; border: none; border-radius: 4px; padding: 8px 18px; font-weight: bold;")
        self.btn_play.clicked.connect(self.run_requested.emit)
        self.addWidget(self.btn_play)
        
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setStyleSheet("background-color: #d73a49; color: white; border: none; border-radius: 4px; padding: 8px 18px; font-weight: bold;")
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        self.addWidget(self.btn_stop)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.addWidget(spacer)
