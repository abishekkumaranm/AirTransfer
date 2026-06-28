import os
import sys
import time
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
    QLabel, QProgressBar, QSplitter, QPushButton
)
from PyQt6.QtCore import Qt, QPoint, QSize
from PyQt6.QtGui import QImage, QPixmap, QColor

import config
from hand_tracker import HandTracker
from gesture import GestureRecognizer
from cursor import CursorController
from motion import SwipeDetector
from state_machine import FileTransferStateMachine, AppState
from file_explorer import FileExplorerWidget
from network_discovery import NetworkDiscoveryListener
from transfer import FileUploader
from overlay import HUDOverlay

class CursorWidget(QLabel):
    """Circular visual representation of the virtual cursor."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(24, 24)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Neon teal circle style sheet
        self.setStyleSheet(f"""
            background-color: rgba(0, 242, 254, 0.6);
            border: 2px solid #FFFFFF;
            border-radius: 12px;
        """)

class FloatingDragIcon(QLabel):
    """Floating folder/file icon that visualizes dragging motion."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 50)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"""
            background-color: rgba(79, 172, 254, 0.85);
            border: 2px solid {config.COLORS["accent_teal"]};
            border-radius: 10px;
            font-size: 24px;
        """)
        self.hide()

    def set_file(self, filepath):
        ext = os.path.splitext(filepath)[1].lower()
        # Choose emoji representation
        emoji = "📄"
        if os.path.isdir(filepath): emoji = "📁"
        elif ext == ".pdf": emoji = "📕"
        elif ext in [".png", ".jpg", ".jpeg", ".gif"]: emoji = "🖼️"
        elif ext in [".mp4", ".mkv", ".avi"]: emoji = "🎬"
        elif ext in [".zip", ".rar", ".tar"]: emoji = "📦"
        self.setText(emoji)

class AirTransferMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AirTransfer - Gestured File Sync")
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        
        # Initialize modules
        self.tracker = HandTracker()
        self.recognizer = GestureRecognizer()
        self.cursor_ctrl = CursorController()
        self.swipe_det = SwipeDetector()
        self.fsm = FileTransferStateMachine()
        self.discovery = NetworkDiscoveryListener()
        
        self.active_uploader = None
        self.device_info = {"ip": None, "port": None, "name": "None Detected"}
        
        # Configure layout styling
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {config.COLORS["background"]};
            }}
            QWidget#central {{
                background-color: {config.COLORS["background"]};
            }}
        """)
        
        self.init_ui()
        self.setup_connections()
        
        # Start background threads
        self.tracker.start()
        self.discovery.start()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("central")
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Splitter to allow resizing panels dynamically
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {config.COLORS["border"]};
                width: 1px;
            }}
        """)
        main_layout.addWidget(splitter)
        
        # LEFT PANEL: Webcam feed & connection status details
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Header layout with title and theme toggle option
        header_layout = QHBoxLayout()
        webcam_header = QLabel("GESTURE WEBCAM FEED")
        webcam_header.setStyleSheet(f"color: {config.COLORS['accent_teal']}; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        
        self.btn_theme = QPushButton("☀️ Light")
        self.btn_theme.setFixedSize(70, 26)
        self.btn_theme.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.COLORS["card_bg"]};
                border: 1px solid {config.COLORS["border"]};
                border-radius: 6px;
                color: {config.COLORS["text_primary"]};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 1px solid {config.COLORS["accent_teal"]};
            }}
        """)
        self.btn_theme.clicked.connect(self.toggle_application_theme)
        
        header_layout.addWidget(webcam_header)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_theme)
        left_layout.addLayout(header_layout)
        
        self.lbl_webcam = QLabel()
        self.lbl_webcam.setFixedSize(320, 240)
        self.lbl_webcam.setStyleSheet(f"""
            background-color: #08080E;
            border: 2px solid {config.COLORS["border"]};
            border-radius: 12px;
        """)
        self.lbl_webcam.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.lbl_webcam)
        
        # Network panel card
        self.net_card = QWidget()
        self.net_card.setStyleSheet(f"""
            QWidget#net_card {{
                background-color: {config.COLORS["card_bg"]};
                border: 1px solid {config.COLORS["border"]};
                border-radius: 12px;
            }}
        """)
        self.net_card.setObjectName("net_card")
        net_layout = QVBoxLayout(self.net_card)
        
        net_lbl = QLabel("NETWORK CONNECTIVITY")
        net_lbl.setStyleSheet(f"color: {config.COLORS['accent_blue']}; font-size: 10px; font-weight: bold; letter-spacing: 0.8px;")
        net_layout.addWidget(net_lbl)
        
        self.lbl_net_status = QLabel("● Scanning Local Network...")
        self.lbl_net_status.setStyleSheet(f"color: {config.COLORS['text_secondary']}; font-size: 13px; font-weight: bold;")
        net_layout.addWidget(self.lbl_net_status)
        
        self.lbl_net_device = QLabel("Device: None detected")
        self.lbl_net_device.setStyleSheet(f"color: {config.COLORS['text_secondary']}; font-size: 12px;")
        net_layout.addWidget(self.lbl_net_device)
        
        left_layout.addWidget(self.net_card)
        
        # Guide panel card
        self.guide_card = QWidget()
        self.guide_card.setStyleSheet(f"""
            QWidget#guide_card {{
                background-color: {config.COLORS["card_bg"]};
                border: 1px solid {config.COLORS["border"]};
                border-radius: 12px;
            }}
        """)
        self.guide_card.setObjectName("guide_card")
        guide_layout = QVBoxLayout(self.guide_card)
        
        guide_title = QLabel("📋 GESTURE GUIDE")
        guide_title.setStyleSheet(f"color: {config.COLORS['accent_teal']}; font-size: 10px; font-weight: bold; letter-spacing: 0.8px;")
        guide_layout.addWidget(guide_title)
        
        self.lbl_guide_step = QLabel("Step 1: Wake System")
        self.lbl_guide_step.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        guide_layout.addWidget(self.lbl_guide_step)
        
        self.lbl_guide_desc = QLabel("Show an Open Palm to activate the gesture cursor.")
        self.lbl_guide_desc.setStyleSheet(f"color: {config.COLORS['text_secondary']}; font-size: 11px;")
        self.lbl_guide_desc.setWordWrap(True)
        guide_layout.addWidget(self.lbl_guide_desc)
        
        left_layout.addWidget(self.guide_card)
        left_layout.addStretch()
        
        # CENTER PANEL: Main File Explorer
        self.file_explorer = FileExplorerWidget(self)
        
        # RIGHT PANEL: Virtual Phone & Drop Target area
        self.phone_widget = QWidget()
        self.phone_widget.setFixedWidth(280)
        self.phone_widget.setStyleSheet(f"""
            QWidget#phone_widget {{
                background-color: {config.COLORS["card_bg"]};
                border: 2px solid {config.COLORS["border"]};
                border-radius: 24px;
            }}
        """)
        self.phone_widget.setObjectName("phone_widget")
        phone_layout = QVBoxLayout(self.phone_widget)
        phone_layout.setContentsMargins(20, 25, 20, 25)
        phone_layout.setSpacing(15)
        
        # Phone header representation
        phone_header = QLabel("MOBILE DEVICE")
        phone_header.setStyleSheet(f"color: {config.COLORS['accent_blue']}; font-size: 11px; font-weight: bold; letter-spacing: 1px; qproperty-alignment: AlignCenter;")
        phone_layout.addWidget(phone_header)
        
        # Target Drop Zone Widget
        self.drop_zone = QWidget()
        self.drop_zone.setObjectName("drop_zone")
        self.set_drop_zone_style(active=False)
        
        drop_layout = QVBoxLayout(self.drop_zone)
        drop_layout.setContentsMargins(10, 10, 10, 10)
        drop_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.lbl_drop_icon = QLabel("📱")
        self.lbl_drop_icon.setStyleSheet("font-size: 48px;")
        self.lbl_drop_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_layout.addWidget(self.lbl_drop_icon)
        
        self.lbl_drop_status = QLabel("Drop files here")
        self.lbl_drop_status.setStyleSheet("font-size: 14px; font-weight: bold; qproperty-alignment: AlignCenter;")
        drop_layout.addWidget(self.lbl_drop_status)
        
        self.lbl_drop_hint = QLabel("Grab a file and hover here")
        self.lbl_drop_hint.setStyleSheet(f"color: {config.COLORS['text_secondary']}; font-size: 11px; qproperty-alignment: AlignCenter;")
        drop_layout.addWidget(self.lbl_drop_hint)
        
        # Transfer Progress Bars (Initially Hidden)
        self.progress_container = QWidget()
        progress_lay = QVBoxLayout(self.progress_container)
        progress_lay.setContentsMargins(0, 0, 0, 0)
        
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {config.COLORS["border"]};
                border-radius: 6px;
                text-align: center;
                height: 18px;
                color: white;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {config.COLORS["accent_teal"]};
                border-radius: 5px;
            }}
        """)
        progress_lay.addWidget(self.prog_bar)
        
        self.lbl_prog_stats = QLabel("Speed: 0 MB/s | ETA: 0s")
        self.lbl_prog_stats.setStyleSheet(f"color: {config.COLORS['text_secondary']}; font-size: 11px; qproperty-alignment: AlignCenter; margin-top: 5px;")
        progress_lay.addWidget(self.lbl_prog_stats)
        
        drop_layout.addWidget(self.progress_container)
        self.progress_container.hide()
        
        phone_layout.addWidget(self.drop_zone, stretch=1)
        
        # Add components to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(self.file_explorer)
        splitter.addWidget(self.phone_widget)
        
        # Set panel proportions
        splitter.setSizes([320, 680, 280])
        
        # Create virtual cursor widgets overlays
        self.cursor_overlay = CursorWidget(self)
        self.drag_icon_overlay = FloatingDragIcon(self)
        
        # 4. WAITING FOR HAND OVERLAY
        self.sleep_overlay = QWidget(self)
        self.sleep_overlay.setStyleSheet("background-color: rgba(10, 10, 20, 0.8);")
        sleep_lay = QVBoxLayout(self.sleep_overlay)
        sleep_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        sleep_icon = QLabel("👋")
        sleep_icon.setStyleSheet("font-size: 72px; qproperty-alignment: AlignCenter;")
        sleep_lay.addWidget(sleep_icon)
        
        sleep_text = QLabel("AirTransfer System Ready")
        sleep_text.setStyleSheet("font-size: 24px; font-weight: bold; color: white; qproperty-alignment: AlignCenter; margin-top: 10px;")
        sleep_lay.addWidget(sleep_text)
        
        sleep_hint = QLabel("Present your hand in front of the webcam to start")
        sleep_hint.setStyleSheet(f"font-size: 14px; color: {config.COLORS['accent_teal']}; qproperty-alignment: AlignCenter; margin-top: 5px;")
        sleep_lay.addWidget(sleep_hint)
        
        self.sleep_overlay.resize(self.size())
        self.sleep_overlay.show()
        
        # HUD overlay drawing instance
        self.hud = HUDOverlay()
        
        # Apply initial theme stylesheet colors
        self.apply_theme_stylesheet()

    def resizeEvent(self, event):
        """Scale overlays along with main window size adjustments."""
        super().resizeEvent(event)
        self.sleep_overlay.resize(self.size())

    def set_drop_zone_style(self, active=False, hover=False, success=False, error=False):
        """Configures styling sheets based on interactive drop states."""
        border_color = config.COLORS["border"]
        bg_color = "rgba(0, 0, 0, 0.2)"
        text_color = "white"
        
        if success:
            border_color = config.COLORS["success"]
            bg_color = "rgba(0, 255, 135, 0.1)"
        elif error:
            border_color = config.COLORS["error"]
            bg_color = "rgba(255, 65, 108, 0.1)"
        elif hover:
            border_color = config.COLORS["accent_teal"]
            bg_color = "rgba(0, 242, 254, 0.1)"
        elif active:
            border_color = config.COLORS["accent_blue"]
            bg_color = "rgba(79, 172, 254, 0.05)"
            
        self.drop_zone.setStyleSheet(f"""
            QWidget#drop_zone {{
                border: 2px dashed {border_color};
                border-radius: 16px;
                background-color: {bg_color};
                color: {text_color};
            }}
        """)

    def setup_connections(self):
        # Hand tracker background processing thread signal
        self.tracker.frame_processed.connect(self.process_webcam_frame)
        
        # Network discovery device detection signals
        self.discovery.device_found.connect(self.device_connected)
        self.discovery.device_lost.connect(self.device_disconnected)

    def process_webcam_frame(self, data):
        """Main update pipeline executing on every camera frame (60 FPS loop)."""
        frame = data["frame"]
        landmarks = data["landmarks"]
        smoothed_lm = data["smoothed_landmarks"]
        fps = data["fps"]
        confidence = data["confidence"]
        hand_side = data["hand_side"]

        # Show/Hide waiting cover screen dynamically when hand enters/leaves the webcam view
        if landmarks:
            self.sleep_overlay.hide()
        else:
            self.sleep_overlay.show()
            self.sleep_overlay.raise_()

        # 1. Update FSM gesture state & classification
        stable_g, raw_g = self.recognizer.update(landmarks)
        
        # Smooth scrolling with Victory gesture (Raise index + middle and move hand vertically)
        if stable_g == "Victory" or raw_g == "Victory":
            if landmarks:
                # Track middle finger MCP (landmark 9) y-coordinate
                current_y = smoothed_lm[9][1]
                if hasattr(self, 'prev_scroll_y') and self.prev_scroll_y is not None:
                    diff_y = current_y - self.prev_scroll_y
                    # Adjust vertical scroll triggers
                    if diff_y > 0.015:
                        self.file_explorer.scroll_content("down")
                        self.prev_scroll_y = current_y
                    elif diff_y < -0.015:
                        self.file_explorer.scroll_content("up")
                        self.prev_scroll_y = current_y
                else:
                    self.prev_scroll_y = current_y
        else:
            self.prev_scroll_y = None

        # Swipe gesture history checks (only Left/Right for folder history)
        swipe = self.swipe_det.update(landmarks)
        if swipe in ["Swipe Left", "Swipe Right"]:
            print(f"[Main] Detected swipe navigation: {swipe}")
            self.handle_swipe_action(swipe)

        # 2. Get local hovered items
        is_hovering_file = False
        hovered_path = None
        hovered_item = None
        
        # Move virtual cursor on Index Finger or Pinch (clicking)
        cx, cy = 0, 0
        if stable_g in ["Index Finger", "Pinch"] or raw_g in ["Index Finger", "Pinch"]:
            # Map coordinates
            cx, cy = self.cursor_ctrl.update(smoothed_lm, self.width(), self.height())
            
            self.cursor_overlay.move(cx - 12, cy - 12)
            self.cursor_overlay.show()
            self.cursor_overlay.raise_()
            
            # Highlight hovered explorer items
            hovered_path, hovered_item = self.file_explorer.get_file_under_coordinates(cx, cy)
            is_hovering_file = hovered_path is not None
        else:
            self.cursor_overlay.hide()

        # Update FSM drop target coordinates
        self.fsm.is_over_phone_zone = self.is_in_drop_zone(cx, cy)

        # Handle rising-edge (click) trigger for Pinch gesture
        fsm_gesture = stable_g
        if stable_g == "Pinch" or raw_g == "Pinch":
            if getattr(self, "pinch_active", False):
                # Already processed this pinch click, pass Index Finger to prevent state flapping
                fsm_gesture = "Index Finger"
            else:
                self.pinch_active = True
                fsm_gesture = "Pinch"
                # Inject mouse click at cursor position
                if cx > 0 and cy > 0:
                    self.inject_click(cx, cy)
        else:
            self.pinch_active = False

        # Handle FSM state state triggers
        state_changed = self.fsm.handle_gesture(fsm_gesture, is_hovering_file, hovered_path)

        # Get current state
        current_state = self.fsm.get_state()

        # Update visual display interfaces
        self.update_gui_by_state(current_state, stable_g, cx, cy)

        # 3. Draw HUD annotations onto OpenCV preview image
        conn_str = "CONNECTED" if self.device_info["ip"] else "OFFLINE"
        gesture_info = {
            "stable": stable_g,
            "raw": raw_g,
            "history_len": len(self.recognizer.history)
        }
        
        annotated_frame = self.hud.draw(
            frame, landmarks, smoothed_lm, current_state, 
            gesture_info, conn_str, fps
        )
        
        # 4. Convert OpenCV numpy frame to QImage for display
        rgb_image = QImage(
            annotated_frame.data, annotated_frame.shape[1], annotated_frame.shape[0], 
            annotated_frame.strides[0], QImage.Format.Format_BGR888
        )
        # Resize to label display size
        pixmap = QPixmap.fromImage(rgb_image).scaled(
            self.lbl_webcam.size(), 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
            Qt.TransformationMode.SmoothTransformation
        )
        self.lbl_webcam.setPixmap(pixmap)

    def handle_swipe_action(self, swipe):
        """Map swipe detections to system triggers."""
        # Up/Down scrolling
        if swipe == "Swipe Up":
            self.file_explorer.scroll_content("down")
        elif swipe == "Swipe Down":
            self.file_explorer.scroll_content("up")
        # Back/Forward folder history
        elif swipe == "Swipe Left":
            self.file_explorer.navigate_back()
        elif swipe == "Swipe Right":
            self.file_explorer.navigate_forward()

    def is_in_drop_zone(self, cx, cy):
        """Verify if target coordinates sit inside the phone drop zone boundary."""
        if not self.phone_widget.isVisible():
            return False
            
        # Map main window coordinate to drop zone widget space
        local_pos = self.drop_zone.mapFrom(self, QPoint(cx, cy))
        return self.drop_zone.rect().contains(local_pos)

    def update_gui_by_state(self, state, gesture, cx, cy):
        """Align layout panels, colors, and overlays based on state configurations."""
        # Update Guide Panel Step and Description dynamically
        # Update Guide Panel Step and Description dynamically
        if state == AppState.HOVER:
            self.lbl_guide_step.setText("Step 1: Point to Browse")
            self.lbl_guide_desc.setText("Point with your Index Finger to control the cursor. Hover over a file. Raise 2 fingers (Victory) and move your hand vertically to scroll.")
        elif state == AppState.DRAGGING:
            if self.fsm.is_over_phone_zone:
                self.lbl_guide_step.setText("Step 3: Tap to Drop")
                self.lbl_guide_desc.setText("Pinch again (touch thumb + index) to drop the file and start transferring wirelessly.")
            else:
                self.lbl_guide_step.setText("Step 2: Tap to Grab")
                self.lbl_guide_desc.setText("A file is attached to your cursor! Move your hand normally to position the file over the Mobile Device drop zone on the right.")
        elif state == AppState.TRANSFERRING:
            self.lbl_guide_step.setText("Step 4: Syncing File")
            self.lbl_guide_desc.setText("Uploading file over the local network. Please keep your hand steady.")
        elif state == AppState.CONFIRMING:
            self.lbl_guide_step.setText("Step 5: Sync Complete")
            self.lbl_guide_desc.setText("Transfer finished successfully! This notification will auto-dismiss in 3 seconds.")

        # Drag & Drop Floating Icon Representation
        if state == AppState.DRAGGING:
            filepath = self.fsm.dragged_file_path
            if filepath:
                self.drag_icon_overlay.set_file(filepath)
                # Align offset slightly below cursor
                self.drag_icon_overlay.move(cx + 15, cy + 15)
                self.drag_icon_overlay.show()
                self.drag_icon_overlay.raise_()
        else:
            self.drag_icon_overlay.hide()

        # Phone Drop Zone Panel Stylings
        if state == AppState.HOVER:
            self.set_drop_zone_style(active=False)
            self.lbl_drop_status.setText("Select a File")
            self.lbl_drop_hint.setText("Pinch (click) a file to pick up")
            self.progress_container.hide()
            self.lbl_drop_icon.setText("📱")
            
        elif state == AppState.DRAGGING:
            if self.fsm.is_over_phone_zone:
                self.set_drop_zone_style(hover=True)
                self.lbl_drop_status.setText("Ready to Transfer")
                self.lbl_drop_hint.setText("Pinch once to drop & upload")
                self.lbl_drop_icon.setText("📥")
            else:
                self.set_drop_zone_style(active=True)
                self.lbl_drop_status.setText("Carrying File")
                self.lbl_drop_hint.setText("Move file over phone area")
                self.lbl_drop_icon.setText("📦")
                
        elif state == AppState.TRANSFERRING:
            # Initiate upload thread on state entry
            if not self.active_uploader:
                filepath = self.fsm.dragged_file_path
                if filepath:
                    if self.device_info["ip"]:
                        self.lbl_drop_icon.setText("⏳")
                        self.lbl_drop_status.setText("Transferring...")
                        self.lbl_drop_hint.setText(os.path.basename(filepath))
                        self.prog_bar.setValue(0)
                        self.progress_container.show()
                        self.set_drop_zone_style(active=True)
                        
                        # Start transfer thread
                        self.active_uploader = FileUploader(
                            filepath, 
                            self.device_info["ip"], 
                            self.device_info["port"]
                        )
                        self.active_uploader.progress_updated.connect(self.upload_progress_updated)
                        self.active_uploader.finished.connect(self.upload_finished)
                        self.active_uploader.start()
                    else:
                        # Fail transfer if device is disconnected
                        self.upload_finished(False, "No receiver device detected on local Wi-Fi.")

        elif state == AppState.CONFIRMING:
            pass

    def upload_progress_updated(self, data):
        """Update metrics during file upload execution."""
        percent = data["percent"]
        speed = data["speed"]
        eta = data["eta"]
        elapsed = data.get("elapsed", 0)
        
        def format_time(sec):
            if sec < 60:
                return f"{sec}s"
            m = sec // 60
            s = sec % 60
            return f"{m}m {s}s"
            
        self.prog_bar.setValue(percent)
        self.lbl_prog_stats.setText(
            f"Speed: {speed} MB/s\n"
            f"Elapsed: {format_time(elapsed)} | Remaining: {format_time(eta)}"
        )

    def upload_finished(self, success, message):
        """Callback for file upload end states."""
        self.active_uploader = None
        self.progress_container.hide()
        
        if success:
            self.lbl_drop_icon.setText("✅")
            self.lbl_drop_status.setText("Transfer Success!")
            self.lbl_drop_hint.setText("Auto-dismissing in 3s...")
            self.set_drop_zone_style(success=True)
            self.fsm.state = AppState.CONFIRMING
            # Trigger auto-dismiss timer (3 seconds)
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(3000, self.auto_dismiss_confirm)
        else:
            self.lbl_drop_icon.setText("❌")
            self.lbl_drop_status.setText("Transfer Failed")
            self.lbl_drop_hint.setText(f"{message}\nPinch or Victory to clear")
            self.set_drop_zone_style(error=True)
            self.fsm.state = AppState.CONFIRMING

    def auto_dismiss_confirm(self):
        """Removes the success notification overlay automatically."""
        if self.fsm.state == AppState.CONFIRMING:
            self.fsm.state = AppState.HOVER
            self.fsm.dragged_file_path = None
            self.update_gui_by_state(AppState.HOVER, "None", 0, 0)

    def inject_click(self, cx, cy):
        """Finds the child widget at coordinates and programmatically dispatches Left Click Press & Release events."""
        from PyQt6.QtCore import QEvent, QPointF, QPoint
        from PyQt6.QtGui import QMouseEvent
        
        # Find innermost child widget under the virtual cursor coordinates
        target = self.childAt(QPoint(cx, cy))
        if target:
            # Map window coordinates to target widget's local coordinates
            local_pos = target.mapFrom(self, QPoint(cx, cy))
            
            # Create Mouse Press event
            press = QMouseEvent(
                QEvent.Type.MouseButtonPress,
                QPointF(local_pos.x(), local_pos.y()),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            # Create Mouse Release event
            release = QMouseEvent(
                QEvent.Type.MouseButtonRelease,
                QPointF(local_pos.x(), local_pos.y()),
                Qt.MouseButton.LeftButton,
                Qt.MouseButton.LeftButton,
                Qt.KeyboardModifier.NoModifier
            )
            
            # Post events to PyQt6 event loop
            QApplication.postEvent(target, press)
            QApplication.postEvent(target, release)
            print(f"[Virtual Mouse] Click injected on {target.__class__.__name__} at local ({local_pos.x()}, {local_pos.y()})")

    def toggle_application_theme(self):
        """Toggles the global style sheet between light and dark modes."""
        config.toggle_theme()
        if config.CURRENT_THEME == "dark":
            self.btn_theme.setText("☀️ Light")
        else:
            self.btn_theme.setText("🌙 Dark")
        self.apply_theme_stylesheet()

    def apply_theme_stylesheet(self):
        """Re-applies stylesheets dynamically when theme is switched between light and dark."""
        theme = config.THEMES[config.CURRENT_THEME]
        
        # Main Window stylesheet
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme["background"]};
            }}
            QWidget#central {{
                background-color: {theme["background"]};
            }}
        """)
        
        # Webcam label border
        self.lbl_webcam.setStyleSheet(f"""
            background-color: #08080E;
            border: 2px solid {theme["border"]};
            border-radius: 12px;
        """)
        
        # Connection card
        self.net_card.setStyleSheet(f"""
            QWidget#net_card {{
                background-color: {theme["card_bg"]};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
            }}
        """)
        
        # Guide card
        self.guide_card.setStyleSheet(f"""
            QWidget#guide_card {{
                background-color: {theme["card_bg"]};
                border: 1px solid {theme["border"]};
                border-radius: 12px;
            }}
        """)
        self.lbl_guide_step.setStyleSheet(f"color: {theme['text_primary']}; font-size: 14px; font-weight: bold;")
        self.lbl_guide_desc.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 11px;")
        
        # Phone widget
        self.phone_widget.setStyleSheet(f"""
            QWidget#phone_widget {{
                background-color: {theme["card_bg"]};
                border: 2px solid {theme["border"]};
                border-radius: 24px;
            }}
        """)
        
        # Labels and stats
        self.lbl_prog_stats.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 11px; qproperty-alignment: AlignCenter; margin-top: 5px;")
        self.lbl_net_status.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 13px; font-weight: bold;")
        self.lbl_net_device.setStyleSheet(f"color: {theme['text_secondary']}; font-size: 12px;")
        
        # Theme button itself
        self.btn_theme.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme["card_bg"]};
                border: 1px solid {theme["border"]};
                border-radius: 6px;
                color: {theme["text_primary"]};
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 1px solid {theme["accent_teal"]};
            }}
        """)
        
        # Refresh current drop style based on active FSM state
        self.update_gui_by_state(self.fsm.get_state(), "None", 0, 0)
        
        # Update child FileExplorerWidget
        self.file_explorer.update_theme()

    def device_connected(self, ip, port, name):
        """Device auto-discovery connection event."""
        self.device_info = {"ip": ip, "port": port, "name": name}
        self.lbl_net_status.setText("● Connected")
        self.lbl_net_status.setStyleSheet("color: #00FF87; font-size: 13px; font-weight: bold;")
        self.lbl_net_device.setText(f"Device: {name} ({ip}:{port})")

    def device_disconnected(self):
        """Device auto-discovery network drop event."""
        self.device_info = {"ip": None, "port": None, "name": "None Detected"}
        self.lbl_net_status.setText("● Scanning Network...")
        self.lbl_net_status.setStyleSheet("color: #B3B3CC; font-size: 13px; font-weight: bold;")
        self.lbl_net_device.setText("Device: None detected")
        
        # If transfer is currently running, cancel it
        if self.active_uploader:
            self.active_uploader.cancel()
            
        # Reset FSM state
        self.fsm.reset()

    def closeEvent(self, event):
        """Stop all background worker threads before shutting down application window."""
        self.tracker.stop()
        self.discovery.stop()
        if self.active_uploader:
            self.active_uploader.cancel()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = AirTransferMainWindow()
    window.show()
    sys.exit(app.exec())
