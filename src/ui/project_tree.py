from PyQt6.QtWidgets import QDockWidget, QStackedWidget, QLabel, QWidget, QVBoxLayout, QTreeView, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFileSystemModel

class ProjectExplorerDock(QDockWidget):
    file_double_clicked = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Project Explorer", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        self.sidebar_stack = QStackedWidget()
        
        # Blank State
        self.lbl_no_project = QLabel("No active project.")
        self.lbl_no_project.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_no_project.setStyleSheet("color: #777777;")
        self.sidebar_stack.addWidget(self.lbl_no_project)
        
        # Explorer Widget
        explorer_widget = QWidget()
        explorer_layout = QVBoxLayout(explorer_widget)
        explorer_layout.setContentsMargins(0, 0, 0, 0)
        explorer_layout.setSpacing(0)
        
        self.project_header_lbl = QLabel("PROJECT")
        self.project_header_lbl.setStyleSheet("font-weight: bold; padding: 8px 10px; background-color: #2a2d2e; color: #cccccc; font-size: 11px; letter-spacing: 1px;")
        
        self.file_model = QFileSystemModel()
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(20)
        
        self.tree_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.tree_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_view.setAllColumnsShowFocus(True)
        self.tree_view.setStyleSheet("QTreeView { outline: none; border: none; } QTreeView::item { outline: none; }")
        
        for col in range(1, 4):
            self.tree_view.hideColumn(col)
            
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)
        
        explorer_layout.addWidget(self.project_header_lbl)
        explorer_layout.addWidget(self.tree_view)
        
        self.sidebar_stack.addWidget(explorer_widget)
        self.setWidget(self.sidebar_stack)

    def set_empty_state(self):
        self.sidebar_stack.setCurrentIndex(0)

    def load_project_folder(self, project_path, project_name):
        self.project_header_lbl.setText(f"▾ {project_name.upper()}")
        self.file_model.setRootPath(project_path)
        self.tree_view.setRootIndex(self.file_model.index(project_path))
        self.sidebar_stack.setCurrentIndex(1)

    def _on_item_double_clicked(self, index):
        file_path = self.file_model.filePath(index)
        self.file_double_clicked.emit(file_path)
