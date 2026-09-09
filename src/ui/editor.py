import os
from PyQt6.QtWidgets import QStackedWidget, QLabel, QTabWidget, QTextEdit
from PyQt6.QtCore import Qt
from backend.dts_parser import parse_dts_file

class CentralWorkspace(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.lbl_no_file = QLabel("Create or Load a project to begin.")
        self.lbl_no_file.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_file.setStyleSheet("color: #555555; font-size: 16px; font-weight: bold;")
        self.addWidget(self.lbl_no_file)
        
        self.tabs = QTabWidget()
        self.hw_tab = QTextEdit()
        self.hw_tab.setReadOnly(True)
        self.code_tab = QTextEdit()
        self.code_tab.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 14px; background: #1e1e1e; color: #d4d4d4;")
        
        self.tabs.addTab(self.hw_tab, "Hardware Map")
        self.tabs.addTab(self.code_tab, "Editor")
        
        self.addWidget(self.tabs)

    def set_empty_state(self):
        self.setCurrentIndex(0)

    def show_workspace(self):
        self.setCurrentIndex(1)

    def open_file(self, file_path):
        if os.path.isfile(file_path):
            if any(file_path.endswith(ext) for ext in [".dts", ".c", ".S", ".ld", ".toml"]):
                self.setCurrentIndex(1)
                self.tabs.setCurrentIndex(1) 
                try:
                    with open(file_path, "r") as f:
                        self.code_tab.setPlainText(f.read())
                except Exception:
                    pass

    def update_hardware_map(self, project_path, dts_filename):
        if not dts_filename or not project_path:
            self.hw_tab.setHtml("<h2 style='color: #4facf7; font-family: sans-serif;'>Hardware Map</h2><p>No valid DTS file imported.</p>")
            return

        dts_full_path = os.path.join(project_path, dts_filename)
        if not os.path.exists(dts_full_path):
            self.hw_tab.setHtml("<h2 style='color: #4facf7; font-family: sans-serif;'>Hardware Map</h2><p>No valid DTS file imported.</p>")
            return

        parsed_data = parse_dts_file(dts_full_path)

        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif; color: #d4d4d4;">
            <h2 style="color: #4facf7; border-bottom: 1px solid #333; padding-bottom: 5px;">Hardware Configuration Map</h2>
            
            <h3 style="color: #d7ba7d; margin-top: 15px;">System Core</h3>
            <table style="border-collapse: collapse; width: 60%; font-size: 14px;">
                <tr><td style="padding: 8px; border: 1px solid #444; background-color: #252526; font-weight: bold; width: 40%;">Machine Model</td><td style="padding: 8px; border: 1px solid #444;">{parsed_data['model']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #444; background-color: #252526; font-weight: bold;">Instruction Set (ISA)</td><td style="padding: 8px; border: 1px solid #444;">{parsed_data['isa']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #444; background-color: #252526; font-weight: bold;">MMU Type</td><td style="padding: 8px; border: 1px solid #444;">{parsed_data['mmu']}</td></tr>
                <tr><td style="padding: 8px; border: 1px solid #444; background-color: #252526; font-weight: bold;">Main Memory Base</td><td style="padding: 8px; border: 1px solid #444; font-family: monospace; color: #4caf50;">{parsed_data['memory_base']}</td></tr>
            </table>

            <h3 style="color: #d7ba7d; margin-top: 25px;">Memory Mapped Peripherals</h3>
            <table style="border-collapse: collapse; width: 90%; font-size: 14px;">
                <tr>
                    <th style="padding: 8px; border: 1px solid #444; background-color: #252526; text-align: left;">Base Address</th>
                    <th style="padding: 8px; border: 1px solid #444; background-color: #252526; text-align: left;">Device Node</th>
                    <th style="padding: 8px; border: 1px solid #444; background-color: #252526; text-align: left;">Compatible Driver</th>
                </tr>
        """
        for p in parsed_data["peripherals"]:
            html += f"""
                <tr>
                    <td style="padding: 6px 8px; border: 1px solid #444; font-family: monospace; color: #4caf50;">{p['addr']}</td>
                    <td style="padding: 6px 8px; border: 1px solid #444;">{p['name']}</td>
                    <td style="padding: 6px 8px; border: 1px solid #444; font-style: italic;">{p['compatible']}</td>
                </tr>
            """
        html += "</table></div>"
        self.hw_tab.setHtml(html)
