import sys
import os
import shutil
import re

# Ensure backend and ui imports resolve cleanly regardless of invocation path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QFileDialog, QDialog, QCheckBox, QDialogButtonBox,
    QMessageBox, QLineEdit, QGroupBox, QInputDialog, QLabel, QPushButton
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QSettings

from ui.statusbar import MainStatusBar
from ui.console import ConsoleDock
from ui.toolbar import MainToolBar
from ui.project_tree import ProjectExplorerDock
from ui.editor import CentralWorkspace

class NewProjectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Project")
        self.setMinimumWidth(500)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<b>Project Name:</b>"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., visionfive2_bringup")
        layout.addWidget(self.name_input)
        
        layout.addWidget(QLabel("<b>Project Location:</b>"))
        loc_layout = QHBoxLayout()
        self.loc_input = QLineEdit()
        self.loc_input.setPlaceholderText("/path/to/workspace")
        self.btn_browse = QPushButton("Browse...")
        self.btn_browse.clicked.connect(self.browse_location)
        loc_layout.addWidget(self.loc_input)
        loc_layout.addWidget(self.btn_browse)
        layout.addLayout(loc_layout)
        
        layout.addWidget(QLabel("<b>Import DTS File:</b>"))
        dts_layout = QHBoxLayout()
        self.dts_input = QLineEdit()
        self.dts_input.setPlaceholderText("Select .dts file...")
        self.btn_dts_browse = QPushButton("Browse DTS...")
        self.btn_dts_browse.clicked.connect(self.browse_dts)
        dts_layout.addWidget(self.dts_input)
        dts_layout.addWidget(self.btn_dts_browse)
        layout.addLayout(dts_layout)
        
        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        
        self.cb_toolchain = QCheckBox("Build toolchain")
        self.cb_toolchain.setChecked(True)
        self.cb_toolchain.setEnabled(False) 
        config_layout.addWidget(self.cb_toolchain)
        
        self.cb_baremetal = QCheckBox("Bare metal Environment")
        self.cb_rtos = QCheckBox("RTOS Bootup")
        self.cb_emulation = QCheckBox("Emulation")
        
        config_layout.addWidget(self.cb_baremetal)
        config_layout.addWidget(self.cb_rtos)
        config_layout.addWidget(self.cb_emulation)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Create Project")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def browse_location(self):
        home_dir = os.path.expanduser("~")
        directory = QFileDialog.getExistingDirectory(self, "Select Project Location", home_dir)
        if directory: self.loc_input.setText(directory)
            
    def browse_dts(self):
        home_dir = os.path.expanduser("~")
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Device Tree Source", home_dir, "Device Tree Files (*.dts)")
        if file_name: self.dts_input.setText(file_name)

    def get_project_details(self):
        configs = ["Toolchain"]
        if self.cb_baremetal.isChecked(): configs.append("Bare Metal")
        if self.cb_rtos.isChecked(): configs.append("RTOS")
        if self.cb_emulation.isChecked(): configs.append("Emulation")
        return {
            "name": self.name_input.text(), "location": self.loc_input.text(),
            "dts_file": self.dts_input.text(), "configs": configs
        }


class RISCVBuilderIDE(QMainWindow):
    def __init__(self):
        super().__init__()
        self.base_title = "RISC-V Firmware Environment Builder"
        self.setWindowTitle(self.base_title)
        self.resize(1280, 800)
        
        self.current_project_path = None
        self.current_project_name = None
        self.current_dts_file = None
        self.current_configs = []
        
        self.settings = QSettings("AMI", "RISCV_Builder")

        self.setup_menu_bar()
        
        # ToolBar Component
        self.top_toolbar = MainToolBar(self)
        self.top_toolbar.run_requested.connect(self.mock_boot_action)
        self.top_toolbar.stop_requested.connect(self.mock_stop_action)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.top_toolbar)

        # Sidebar Component
        self.project_dock = ProjectExplorerDock(self)
        self.project_dock.file_double_clicked.connect(self.on_file_double_clicked)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.project_dock)

        # Central Editor Workspace
        self.workspace = CentralWorkspace(self)
        self.setCentralWidget(self.workspace)

        # Bottom Terminal Console
        self.console_dock = ConsoleDock(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)

        # Status Bar Component
        self.status_bar = MainStatusBar(self)
        self.setStatusBar(self.status_bar)
        
        self.update_recent_menu()

    def setup_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New Project", self)
        new_action.triggered.connect(self.action_new_project)
        file_menu.addAction(new_action)
        
        load_action = QAction("Load Project", self)
        load_action.triggered.connect(self.action_load_project)
        file_menu.addAction(load_action)
        
        self.recent_menu = file_menu.addMenu("Recent")
        file_menu.addSeparator()
        
        self.close_action = QAction("Close Project", self)
        self.close_action.triggered.connect(self.action_close_project)
        self.close_action.setEnabled(False) 
        file_menu.addAction(self.close_action)
        
        self.save_action = QAction("Save", self)
        self.save_action.triggered.connect(self.action_save_project)
        self.save_action.setEnabled(False) 
        file_menu.addAction(self.save_action)
        
        self.save_as_action = QAction("Save As...", self)
        self.save_as_action.triggered.connect(self.action_save_as_project)
        self.save_as_action.setEnabled(False) 
        file_menu.addAction(self.save_as_action)
        
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        edit_menu = menubar.addMenu("Edit")
        edit_menu.addAction("Preferences")
        
        view_menu = menubar.addMenu("View")
        view_menu.addAction("Toggle Console")
        
        about_menu = menubar.addMenu("About us")
        about_action = QAction("About This Tool", self)
        about_action.triggered.connect(self.action_about_us)
        about_menu.addAction(about_action)

    def update_recent_menu(self):
        self.recent_menu.clear()
        recent_files = self.settings.value("recent_projects", [])
        if isinstance(recent_files, str): recent_files = [recent_files]
        if not recent_files: recent_files = []
        
        valid_files = []
        for toml_path in recent_files:
            if os.path.exists(toml_path):
                valid_files.append(toml_path)
                p_name = os.path.basename(os.path.dirname(toml_path))
                action_text = f"{p_name}  [{toml_path}]"
                action = QAction(action_text, self)
                action.triggered.connect(lambda checked, p=toml_path: self.load_project_from_toml(p))
                self.recent_menu.addAction(action)

        if not valid_files:
            empty_action = QAction("No Recent Projects", self)
            empty_action.setEnabled(False)
            self.recent_menu.addAction(empty_action)
        else:
            self.recent_menu.addSeparator()
            clear_action = QAction("Clear Recent Projects", self)
            clear_action.triggered.connect(self.clear_recent_projects)
            self.recent_menu.addAction(clear_action)
            
        self.settings.setValue("recent_projects", valid_files)

    def add_to_recent(self, toml_path):
        recent_files = self.settings.value("recent_projects", [])
        if isinstance(recent_files, str): recent_files = [recent_files]
        if not recent_files: recent_files = []
        if toml_path in recent_files: recent_files.remove(toml_path)
            
        recent_files.insert(0, toml_path)
        recent_files = recent_files[:10]
        self.settings.setValue("recent_projects", recent_files)
        self.update_recent_menu()

    def clear_recent_projects(self):
        self.settings.setValue("recent_projects", [])
        self.update_recent_menu()

    def on_file_double_clicked(self, file_path):
        self.workspace.open_file(file_path)

    def write_toml_config(self, project_path, p_name, dts_file, configs):
        toml_path = os.path.join(project_path, "riscv_env.toml")
        with open(toml_path, "w") as f:
            f.write(f"[project]\nname = \"{p_name}\"\ndts_file = \"{dts_file}\"\n\n")
            f.write(f"[configs]\ntoolchain = true\n")
            f.write(f"bare_metal = {'true' if 'Bare Metal' in configs else 'false'}\n")
            f.write(f"rtos = {'true' if 'RTOS' in configs else 'false'}\n")
            f.write(f"emulation = {'true' if 'Emulation' in configs else 'false'}\n")
        return toml_path

    def load_workspace(self, project_path, p_name, dts_file, configs):
        self.current_project_path = os.path.normpath(project_path)
        self.current_project_name = p_name
        self.current_dts_file = dts_file
        self.current_configs = configs
        
        self.setWindowTitle(f"{self.base_title} - {self.current_project_name}")
        self.close_action.setEnabled(True)
        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)

        self.project_dock.load_project_folder(self.current_project_path, self.current_project_name)
        self.workspace.show_workspace()
        self.workspace.update_hardware_map(self.current_project_path, self.current_dts_file)
        
        self.status_bar.update_status(p_name, len(configs), "IDLE")

    def action_new_project(self):
        dialog = NewProjectDialog(self)
        dialog.setStyleSheet("""
            QLineEdit { background: #3c3c3c; border: 1px solid #555; padding: 6px; border-radius: 4px; color: white; font-size: 14px;}
            QGroupBox { font-weight: bold; border: 1px solid #555; border-radius: 4px; margin-top: 15px; padding-top: 15px; font-size: 14px;}
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; color: #4facf7; }
            QCheckBox { color: #ccc; font-size: 14px; padding: 4px;}
            QCheckBox:disabled { color: #777; }
            QPushButton { padding: 6px 12px; }
        """)
        if dialog.exec():
            details = dialog.get_project_details()
            p_name = details["name"].strip() or "UntitledProject"
            p_loc = details["location"].strip() or os.path.expanduser("~")
            dts_file = details["dts_file"].strip()
            configs = details["configs"]
            
            full_project_path = os.path.join(p_loc, p_name)
            try:
                os.makedirs(full_project_path, exist_ok=True)
                os.makedirs(os.path.join(full_project_path, "toolchain"), exist_ok=True)
                if "Bare Metal" in configs: os.makedirs(os.path.join(full_project_path, "bare_metal"), exist_ok=True)
                if "RTOS" in configs: os.makedirs(os.path.join(full_project_path, "rtos"), exist_ok=True)
                if "Emulation" in configs: os.makedirs(os.path.join(full_project_path, "emulation"), exist_ok=True)
                
                copied_dts_path = ""
                if dts_file and os.path.exists(dts_file):
                    filename = os.path.basename(dts_file)
                    dest_path = os.path.join(full_project_path, filename)
                    shutil.copy2(dts_file, dest_path)
                    copied_dts_path = filename

                toml_path = self.write_toml_config(full_project_path, p_name, copied_dts_path, configs)
                self.add_to_recent(toml_path)
                self.load_workspace(full_project_path, p_name, copied_dts_path, configs)
            except Exception:
                pass

    def action_load_project(self):
        home_dir = os.path.expanduser("~")
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Project TOML", home_dir, "TOML Config Files (*.toml)")
        if file_name:
            self.load_project_from_toml(file_name)

    def load_project_from_toml(self, file_name):
        if not os.path.exists(file_name): return
        project_dir = os.path.dirname(file_name)
        try:
            with open(file_name, 'r') as f: content = f.read()
            name_match = re.search(r'name\s*=\s*"([^"]+)"', content)
            dts_match = re.search(r'dts_file\s*=\s*"([^"]*)"', content)
            p_name = name_match.group(1) if name_match else os.path.basename(project_dir)
            dts_file = dts_match.group(1) if dts_match else ""
            
            configs = ["Toolchain"]
            if re.search(r'bare_metal\s*=\s*true', content): configs.append("Bare Metal")
            if re.search(r'rtos\s*=\s*true', content): configs.append("RTOS")
            if re.search(r'emulation\s*=\s*true', content): configs.append("Emulation")
            
            self.load_workspace(project_dir, p_name, dts_file, configs)
            self.add_to_recent(file_name)
        except Exception:
            pass

    def action_close_project(self):
        self.current_project_path = None
        self.current_project_name = None
        self.current_dts_file = None
        self.current_configs = []
        
        self.setWindowTitle(self.base_title)

        self.close_action.setEnabled(False)
        self.save_action.setEnabled(False)
        self.save_as_action.setEnabled(False)

        self.project_dock.set_empty_state()
        self.workspace.set_empty_state()
        self.status_bar.update_status()

    def action_save_project(self):
        if self.current_project_path:
            self.write_toml_config(self.current_project_path, self.current_project_name, self.current_dts_file, self.current_configs)

    def action_save_as_project(self):
        if not self.current_project_path: return
        home_dir = os.path.expanduser("~")
        new_parent_dir = QFileDialog.getExistingDirectory(self, "Select Destination for Save As...", home_dir)
        if new_parent_dir:
            new_name, ok = QInputDialog.getText(self, "Save As", "Enter new project name:", text=self.current_project_name + "_copy")
            if ok and new_name:
                new_project_path = os.path.join(new_parent_dir, new_name)
                try:
                    shutil.copytree(self.current_project_path, new_project_path)
                    toml_path = self.write_toml_config(new_project_path, new_name, self.current_dts_file, self.current_configs)
                    self.add_to_recent(toml_path)
                    self.load_workspace(new_project_path, new_name, self.current_dts_file, self.current_configs)
                except Exception:
                    pass

    def action_about_us(self):
        QMessageBox.information(self, "About Us", "RISC-V Firmware Environment Builder\nAutomates Hardware-to-Software environments.")

    def mock_boot_action(self):
        if not self.current_project_path: return
        self.console_dock.log_to_console("Toolchain", "Starting cross-compilation process...", "warn")

    def mock_stop_action(self):
        pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    qss_path = os.path.join(os.path.dirname(__file__), "style.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f: app.setStyleSheet(f.read())
    window = RISCVBuilderIDE()
    window.show()
    sys.exit(app.exec())
