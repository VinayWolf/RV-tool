import sys
import os
import shutil
import re
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QDockWidget, QTreeView, QTabWidget, QTextEdit, QMenuBar, QMenu,
    QToolBar, QStatusBar, QLabel, QPushButton, QSpacerItem,
    QSizePolicy, QFileDialog, QDialog, QCheckBox, QDialogButtonBox,
    QMessageBox, QLineEdit, QGroupBox, QInputDialog, QStackedWidget,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QSize, QSettings
from PyQt6.QtGui import QAction, QFont, QFileSystemModel

# --- DTS PARSER LOGIC ---
def parse_dts_file(filepath):
    data = {
        "model": "Unknown", "isa": "Unknown", "mmu": "Unknown",
        "memory_base": "Unknown", "peripherals": []
    }
    
    if not filepath or not os.path.exists(filepath): return data

    try:
        with open(filepath, 'r') as f: content = f.read()
        model_m = re.search(r'model\s*=\s*"([^"]+)"', content)
        if model_m: data["model"] = model_m.group(1)
        isa_m = re.search(r'riscv,isa\s*=\s*"([^"]+)"', content)
        if isa_m: data["isa"] = isa_m.group(1)
        mmu_m = re.search(r'mmu-type\s*=\s*"([^"]+)"', content)
        if mmu_m: data["mmu"] = mmu_m.group(1)

        for match in re.finditer(r'([a-zA-Z0-9_-]+)@([0-9a-fA-F]+)\s*\{', content):
            node_name = match.group(1)
            node_addr = match.group(2)
            start_idx = match.end()

            brace_count = 1
            idx = start_idx
            while idx < len(content) and brace_count > 0:
                if content[idx] == '{': brace_count += 1
                elif content[idx] == '}': brace_count -= 1
                idx += 1

            block = content[start_idx:idx-1]
            if node_name == "memory":
                data["memory_base"] = "0x" + node_addr
            elif node_name != "cpu": 
                comp_m = re.search(r'compatible\s*=\s*"([^"]+)"', block)
                if comp_m:
                    data["peripherals"].append({
                        "name": node_name,
                        "addr": "0x" + node_addr.upper(),
                        "compatible": comp_m.group(1)
                    })
    except Exception as e:
        print(f"Parser error: {e}")
        
    data["peripherals"] = sorted(data["peripherals"], key=lambda x: int(x["addr"], 16))
    return data

# --- UI LOGIC ---
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
        self.setup_top_toolbar()
        self.setup_left_sidebar()
        self.setup_central_workspace()
        self.setup_bottom_console()
        self.setup_status_bar()
        
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

    def setup_top_toolbar(self):
        self.top_toolbar = QToolBar("Main Toolbar")
        self.top_toolbar.setObjectName("topToolBar")
        self.top_toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.top_toolbar)
        
        self.btn_play = QPushButton("▶ Run")
        self.btn_play.setObjectName("runBtn")
        self.btn_play.setStyleSheet("background-color: #2ea043; color: white; border: none; border-radius: 4px; padding: 8px 18px; font-weight: bold;")
        self.btn_play.clicked.connect(self.mock_boot_action)
        self.top_toolbar.addWidget(self.btn_play)
        
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_stop.setStyleSheet("background-color: #d73a49; color: white; border: none; border-radius: 4px; padding: 8px 18px; font-weight: bold;")
        self.btn_stop.clicked.connect(self.mock_stop_action)
        self.top_toolbar.addWidget(self.btn_stop)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.top_toolbar.addWidget(spacer)

    def setup_left_sidebar(self):
        self.sidebar_dock = QDockWidget("Project Explorer", self)
        self.sidebar_dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.sidebar_stack = QStackedWidget()
        
        # --- Index 0: Blank State ---
        self.lbl_no_project = QLabel("No active project.")
        self.lbl_no_project.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_project.setStyleSheet("color: #777777;")
        self.sidebar_stack.addWidget(self.lbl_no_project)
        
        # --- Index 1: VS Code Style Explorer Widget ---
        explorer_widget = QWidget()
        explorer_layout = QVBoxLayout(explorer_widget)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)
        
        # The VS Code style "Root Project Header" label
        self.project_header_lbl = QLabel("PROJECT")
        self.project_header_lbl.setStyleSheet("font-weight: bold; padding: 8px 10px; background-color: #2a2d2e; color: #cccccc; font-size: 11px; letter-spacing: 1px;")
        
        # Standard File System Model
        self.file_model = QFileSystemModel()
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        
        # Disable focus rectangle & select full row
        self.tree_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_view.setAllColumnsShowFocus(True)
        self.tree_view.setStyleSheet("QTreeView { outline: none; border: none; } QTreeView::item { outline: none; }")
        
        for col in range(1, 4):
            self.tree_view.hideColumn(col)
            
        self.tree_view.doubleClicked.connect(self.on_file_double_clicked)
        
        explorer_layout.addWidget(self.project_header_lbl)
        explorer_layout.addWidget(self.tree_view)
        
        self.sidebar_stack.addWidget(explorer_widget)
        
        self.sidebar_dock.setWidget(self.sidebar_stack)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.sidebar_dock)

    def setup_central_workspace(self):
        self.central_stack = QStackedWidget()
        
        self.lbl_no_file = QLabel("Create or Load a project to begin.")
        self.lbl_no_file.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_file.setStyleSheet("color: #555555; font-size: 16px; font-weight: bold;")
        self.central_stack.addWidget(self.lbl_no_file)
        
        self.tabs = QTabWidget()
        self.hw_tab = QTextEdit()
        self.hw_tab.setReadOnly(True)
        self.code_tab = QTextEdit()
        self.code_tab.setStyleSheet("font-family: 'Consolas', 'Courier New', monospace; font-size: 14px; background: #1e1e1e; color: #d4d4d4;")
        self.tabs.addTab(self.hw_tab, "Hardware Map")
        self.tabs.addTab(self.code_tab, "Editor")
        
        self.central_stack.addWidget(self.tabs)
        self.setCentralWidget(self.central_stack)

    def setup_bottom_console(self):
        self.console_dock = QDockWidget("Integrated Terminal", self)
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
        
        self.console_dock.setWidget(console_widget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.console_dock)

    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.project_status = QLabel(" Project: None ")
        self.workflow_status = QLabel(" Configs: None ")
        self.emu_status = QLabel(" Emulator: IDLE ")
        
        self.status_bar.addPermanentWidget(self.project_status)
        self.status_bar.addPermanentWidget(self.workflow_status)
        self.status_bar.addPermanentWidget(self.emu_status)

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

    def log_to_console(self, module, message, level="info"):
        colors = {"info": "#4facf7", "warn": "#d7ba7d", "error": "#f44747", "emu": "#4caf50"}
        color = colors.get(level, "#ffffff")
        html_msg = f"<span style='color: {color}; font-weight: bold;'>[{module}]</span> <span style='color: #cccccc;'>{message}</span>"
        self.console_output.append(html_msg)
        self.console_output.verticalScrollBar().setValue(self.console_output.verticalScrollBar().maximum())

    def update_hardware_map_ui(self):
        if not self.current_dts_file or not os.path.exists(os.path.join(self.current_project_path, self.current_dts_file)):
            self.hw_tab.setHtml("<h2 style='color: #4facf7; font-family: sans-serif;'>Hardware Map</h2><p>No valid DTS file imported.</p>")
            return

        dts_full_path = os.path.join(self.current_project_path, self.current_dts_file)
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

    def on_file_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        
        if os.path.isfile(file_path):
            if file_path.endswith(".dts") or file_path.endswith(".c") or file_path.endswith(".S") or file_path.endswith(".ld") or file_path.endswith(".toml"):
                self.central_stack.setCurrentIndex(1)
                self.tabs.setCurrentIndex(1) 
                try:
                    with open(file_path, "r") as f:
                        self.code_tab.setPlainText(f.read())
                except Exception as e:
                    pass

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
        
        # Window Title & Menu Update
        self.setWindowTitle(f"{self.base_title} - {self.current_project_name}")
        self.close_action.setEnabled(True)
        self.save_action.setEnabled(True)
        self.save_as_action.setEnabled(True)

        # File Explorer Root & Header Update
        self.project_header_lbl.setText(f"▾ {self.current_project_name.upper()}")
        self.file_model.setRootPath(self.current_project_path)
        self.tree_view.setRootIndex(self.file_model.index(self.current_project_path))

        # Show workspace
        self.sidebar_stack.setCurrentIndex(1)
        self.central_stack.setCurrentIndex(1)
        self.tabs.setCurrentIndex(0) 
        
        self.update_hardware_map_ui()
        
        self.project_status.setText(f" Project: {p_name} ")
        self.workflow_status.setText(f" Configs: {len(configs)} active ")

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
            except Exception as e:
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
        except Exception as e:
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

        self.sidebar_stack.setCurrentIndex(0)
        self.central_stack.setCurrentIndex(0)
        
        self.project_status.setText(" Project: None ")
        self.workflow_status.setText(" Configs: None ")

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
                except Exception as e:
                    pass

    def action_about_us(self):
        QMessageBox.information(self, "About Us", "RISC-V Firmware Environment Builder\nAutomates Hardware-to-Software environments.")

    def mock_boot_action(self):
        if not self.current_project_path: return
        self.log_to_console("Toolchain", "Starting cross-compilation process...", "warn")

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
