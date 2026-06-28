import os
import math
import datetime
import string
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QListWidget, QListWidgetItem, QListView, QScrollBar, QPushButton
)
from PyQt6.QtCore import Qt, QSize, QPoint
from PyQt6.QtGui import QIcon, QFont, QColor
import config

class FileExplorerWidget(QWidget):
    def __init__(self, main_window=None):
        super().__init__()
        self.main_window = main_window
        
        # Dynamically search and add all active storage drives (C:\, D:\, etc.)
        self.favorites = list(config.USER_FOLDERS.keys())
        for letter in string.ascii_uppercase:
            drive_path = f"{letter}:\\"
            if os.path.exists(drive_path):
                drive_name = f"Drive ({letter}:)"
                if drive_name not in self.favorites:
                    self.favorites.append(drive_name)
                    config.USER_FOLDERS[drive_name] = drive_path

        self.current_path = config.USER_FOLDERS["Documents"]
        if not os.path.exists(self.current_path):
            self.current_path = "C:\\" if os.path.exists("C:\\") else os.path.expanduser("~")
            
        self.history_back = []
        self.history_forward = []
        self.recent_files = []
        
        self.init_ui()
        self.load_directory(self.current_path)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        # 1. Top Panel: Navigation & Search Bar
        top_panel = QHBoxLayout()
        
        self.btn_back = QPushButton("◀")
        self.btn_back.setFixedSize(36, 36)
        self.btn_back.clicked.connect(self.navigate_back)
        
        self.btn_forward = QPushButton("▶")
        self.btn_forward.setFixedSize(36, 36)
        self.btn_forward.clicked.connect(self.navigate_forward)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍 Search files in current folder...")
        self.search_bar.textChanged.connect(self.filter_files)

        self.btn_view_mode = QPushButton("Grid")
        self.btn_view_mode.setFixedSize(60, 36)
        self.btn_view_mode.clicked.connect(self.toggle_view_mode)
        
        top_panel.addWidget(self.btn_back)
        top_panel.addWidget(self.btn_forward)
        top_panel.addWidget(self.search_bar)
        top_panel.addWidget(self.btn_view_mode)
        layout.addLayout(top_panel)

        # 2. Breadcrumb bar
        self.lbl_breadcrumb = QLabel(self.current_path)
        layout.addWidget(self.lbl_breadcrumb)

        # 3. Main contents layout (Favorites left, File viewer center)
        main_content = QHBoxLayout()
        main_content.setSpacing(15)

        # Favorites Panel
        fav_panel = QVBoxLayout()
        self.fav_label = QLabel("FAVORITES")
        fav_panel.addWidget(self.fav_label)

        self.fav_list = QListWidget()
        self.fav_list.setFixedWidth(150)
        for fav in self.favorites:
            self.fav_list.addItem(fav)
        self.fav_list.itemClicked.connect(self.favorite_clicked)
        fav_panel.addWidget(self.fav_list)
        
        main_content.addLayout(fav_panel, stretch=1)

        # Files list/grid widget
        self.file_list = QListWidget()
        self.file_list.setIconSize(QSize(48, 48))
        self.file_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.file_list.itemDoubleClicked.connect(self.file_double_clicked)
        
        main_content.addWidget(self.file_list, stretch=5)
        layout.addLayout(main_content)

        self.view_mode = "list" # Default list view
        
        # Apply themes to layout elements
        self.update_theme()

    def get_button_style(self):
        return f"""
            QPushButton {{
                background-color: {config.COLORS["card_bg"]};
                border: 1px solid {config.COLORS["border"]};
                border-radius: 8px;
                color: {config.COLORS["text_primary"]};
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 1px solid {config.COLORS["accent_teal"]};
                background-color: rgba(255, 255, 255, 0.05);
            }}
        """

    def update_theme(self):
        """Re-applies stylesheets dynamically when theme is switched between light and dark."""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: {config.COLORS["text_primary"]};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QLineEdit {{
                background-color: {config.COLORS["card_bg"]};
                border: 1px solid {config.COLORS["border"]};
                border-radius: 8px;
                padding: 8px 12px;
                color: {config.COLORS["text_primary"]};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {config.COLORS["accent_teal"]};
            }}
            QListWidget {{
                background-color: {config.COLORS["card_bg"]};
                border: 1px solid {config.COLORS["border"]};
                border-radius: 12px;
                padding: 8px;
                color: {config.COLORS["text_primary"]};
            }}
            QScrollBar:vertical {{
                background: rgba(0, 0, 0, 0.05);
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: {config.COLORS["accent_teal"]};
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
            }}
        """)
        
        self.lbl_breadcrumb.setStyleSheet(f"color: {config.COLORS['text_secondary']}; font-size: 13px; font-weight: bold; padding-left: 5px;")
        self.fav_label.setStyleSheet(f"color: {config.COLORS['accent_blue']}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        
        self.fav_list.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                border: none;
                color: {config.COLORS['text_primary']};
            }}
            QListWidget::item {{
                padding: 10px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.08);
            }}
            QListWidget::item:selected {{
                background-color: rgba(79, 172, 254, 0.2);
                color: {config.COLORS['accent_teal']};
            }}
        """)
        
        self.file_list.setStyleSheet(f"""
            QListWidget::item {{
                background-color: {config.COLORS['card_bg']};
                border: 1px solid {config.COLORS['border']};
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 6px;
                color: {config.COLORS['text_primary']};
            }}
            QListWidget::item:hover {{
                background-color: rgba(0, 242, 254, 0.1);
                border: 1px solid {config.COLORS['accent_teal']};
            }}
            QListWidget::item:selected {{
                background-color: rgba(79, 172, 254, 0.25);
                border: 1px solid {config.COLORS['accent_blue']};
                color: {config.COLORS['text_primary']};
            }}
        """)
        
        self.btn_back.setStyleSheet(self.get_button_style())
        self.btn_forward.setStyleSheet(self.get_button_style())
        self.btn_view_mode.setStyleSheet(self.get_button_style())

    def load_directory(self, path):
        """Populates file_list with files & subfolders from target directory path."""
        self.current_path = path
        self.lbl_breadcrumb.setText(path)
        self.file_list.clear()

        try:
            items = os.listdir(path)
        except PermissionError:
            self.file_list.addItem("⚠️ Permission Denied")
            return
        except FileNotFoundError:
            self.file_list.addItem("⚠️ Folder Not Found")
            return

        # Add "Go to Parent" option if not at the filesystem root
        parent_dir = os.path.dirname(path)
        # Check if parent is actually different from current (handles drives root like C:\)
        if parent_dir and parent_dir != path:
            parent_item = QListWidgetItem(".. [Up to Parent]")
            parent_item.setData(Qt.ItemDataRole.UserRole, parent_dir)
            
            # Use basic emoji indicators to support standard system fonts
            parent_item.setText("📁  .. [Up to Parent]")
            self.file_list.addItem(parent_item)

        # Sort: directories first, then files
        dirs = []
        files = []
        for x in items:
            full = os.path.join(path, x)
            # Skip hidden files
            if x.startswith('.'):
                continue
            if os.path.isdir(full):
                dirs.append(x)
            else:
                files.append(x)
                
        dirs.sort()
        files.sort()

        # Add directories
        for d in dirs:
            full = os.path.join(path, d)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, full)
            
            # Format text representation with details
            try:
                mod_time = os.path.getmtime(full)
                date_str = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
            except Exception:
                date_str = "Unknown"
                
            item.setText(f"📁  {d}\nType: Folder | Modified: {date_str}")
            self.file_list.addItem(item)

        # Add files
        for f in files:
            full = os.path.join(path, f)
            ext = os.path.splitext(f)[1].lower()
            file_type = config.SUPPORTED_EXTENSIONS.get(ext, "File")

            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, full)

            try:
                size_bytes = os.path.getsize(full)
                size_str = self.format_size(size_bytes)
                mod_time = os.path.getmtime(full)
                date_str = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M')
            except Exception:
                size_str = "Unknown"
                date_str = "Unknown"

            # Emoji mapper based on extension type
            emoji = "📄"
            if file_type == "Image":
                emoji = "🖼️"
            elif file_type == "Video":
                emoji = "🎬"
            elif file_type == "PDF Document":
                emoji = "📕"
            elif file_type in ["Word Document", "Excel Sheet", "PowerPoint Presentation"]:
                emoji = "📝"
            elif file_type == "ZIP Archive":
                emoji = "📦"

            item.setText(f"{emoji}  {f}\nSize: {size_str} | Type: {file_type} | Modified: {date_str}")
            self.file_list.addItem(item)

    def format_size(self, size_bytes):
        """Converts bytes size to human-readable format."""
        if size_bytes == 0:
            return "0 B"
        size_name = ("B", "KB", "MB", "GB", "TB")
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

    def toggle_view_mode(self):
        """Switches between List and Grid layout views."""
        if self.view_mode == "list":
            self.file_list.setViewMode(QListView.ViewMode.IconMode)
            self.file_list.setGridSize(QSize(130, 110))
            self.btn_view_mode.setText("List")
            self.view_mode = "grid"
        else:
            self.file_list.setViewMode(QListView.ViewMode.ListMode)
            self.file_list.setGridSize(QSize(-1, -1)) # Reset grid sizing
            self.btn_view_mode.setText("Grid")
            self.view_mode = "list"
        self.load_directory(self.current_path)

    def favorite_clicked(self, item):
        """Navigate straight to a preset user folder."""
        folder_name = item.text()
        target_path = config.USER_FOLDERS.get(folder_name)
        if target_path and os.path.exists(target_path):
            self.history_back.append(self.current_path)
            self.history_forward.clear()
            self.load_directory(target_path)

    def file_double_clicked(self, item):
        """Open directories or select files."""
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            self.history_back.append(self.current_path)
            self.history_forward.clear()
            self.load_directory(path)

    def navigate_back(self):
        """Navigate to previously browsed folder."""
        if self.history_back:
            self.history_forward.append(self.current_path)
            prev = self.history_back.pop()
            self.load_directory(prev)

    def navigate_forward(self):
        """Navigate forward in history."""
        if self.history_forward:
            self.history_back.append(self.current_path)
            nxt = self.history_forward.pop()
            self.load_directory(nxt)

    def filter_files(self, query):
        """Filters files in the current view based on search box input."""
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            item.setHidden(query.lower() not in item.text().lower())

    def get_file_under_coordinates(self, global_x, global_y):
        """Translates window-space coordinates to local and returns item path under cursor."""
        if not self.isVisible() or self.file_list.count() == 0:
            return None, None

        # Map global window coordinate to local QListWidget coordinate
        local_point = self.file_list.mapFrom(self.window(), QPoint(global_x, global_y))
        item = self.file_list.itemAt(local_point)
        
        if item:
            # Highlight item programmatically
            self.file_list.setCurrentItem(item)
            path = item.data(Qt.ItemDataRole.UserRole)
            
            # Exclude parent folder jump item from dragging actions
            if ".. [Up to Parent]" in item.text():
                return None, None
                
            return path, item
        return None, None

    def scroll_content(self, direction):
        """Scrolls the file list using gesture command triggers."""
        v_bar = self.file_list.verticalScrollBar()
        if not v_bar.isVisible():
            return
            
        step = 60 # Sizable scroll chunk
        if direction == "up":
            v_bar.setValue(max(v_bar.minimum(), v_bar.value() - step))
        elif direction == "down":
            v_bar.setValue(min(v_bar.maximum(), v_bar.value() + step))
