from PyQt6.QtWidgets import QStatusBar, QLabel

class MainStatusBar(QStatusBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.project_status = QLabel(" Project: None ")
        self.workflow_status = QLabel(" Configs: None ")
        self.emu_status = QLabel(" Emulator: IDLE ")
        
        self.addPermanentWidget(self.project_status)
        self.addPermanentWidget(self.workflow_status)
        self.addPermanentWidget(self.emu_status)

    def update_status(self, project_name="None", configs_count=0, emu_state="IDLE"):
        self.project_status.setText(f" Project: {project_name} ")
        if project_name != "None":
            self.workflow_status.setText(f" Configs: {configs_count} active ")
        else:
            self.workflow_status.setText(" Configs: None ")
        self.emu_status.setText(f" Emulator: {emu_state} ")
