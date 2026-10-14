"""
FlowPilot Floating Microphone HUD ("Flow Pill")
Frameless, always-on-top, translucent pill widget.
Equipped with WS_EX_NOACTIVATE to prevent stealing focus from active editors.
"""

import sys
import ctypes
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QGraphicsDropShadowEffect, QMenu
)
from PySide6.QtCore import Qt, QPoint, Signal, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QPen, QAction, QIcon

# Win32 Constants for Non-Activating Window
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008

class FloatingHUD(QWidget):
    toggle_requested = Signal()
    cancel_requested = Signal()
    recopy_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_pos = QPoint()
        self._current_state = "idle"
        self._idle_text = "Ready • Ctrl+Shift+Space"
        self._init_ui()

    def set_hotkey_info(self, hotkey_str: str, mode: str = "toggle"):
        clean_hk = hotkey_str.replace("<", "").replace(">", "").strip()
        if mode == "push_to_talk":
            self._idle_text = f"Ready • Hold {clean_hk}"
        else:
            self._idle_text = f"Ready • {clean_hk}"
        if self._current_state in ("idle", "IDLE"):
            self.status_label.setText(self._idle_text)

    def _init_ui(self):
        # Frameless, Always on Top, Tool Window (no taskbar item)
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(290, 52)

        # Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 12, 6)
        layout.setSpacing(10)

        # Microphone Toggle Button
        self.mic_btn = QPushButton("🎙", self)
        self.mic_btn.setFixedSize(38, 38)
        self.mic_btn.setCursor(Qt.PointingHandCursor)
        self.mic_btn.clicked.connect(self._on_mic_clicked)
        layout.addWidget(self.mic_btn)

        # Status & Context Info Label
        self.status_label = QLabel(self._idle_text, self)
        font = QFont("Segoe UI", 10, QFont.Medium)
        self.status_label.setFont(font)
        self.status_label.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(self.status_label, 1)

        # Audio Level Bar (visible when recording)
        self.level_bar = QProgressBar(self)
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedSize(45, 8)
        self.level_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.15);
                border-radius: 4px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 4px;
            }
        """)
        self.level_bar.hide()
        layout.addWidget(self.level_bar)

        # Subtle Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._update_style("idle")

    def showEvent(self, event):
        super().showEvent(event)
        # Apply Windows WS_EX_NOACTIVATE style natively
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE | WS_EX_TOPMOST)
            except Exception as e:
                print(f"[FloatingHUD Warning] Could not apply WS_EX_NOACTIVATE: {e}")

    def _on_mic_clicked(self):
        self.toggle_requested.emit()

    def update_state(self, state: str, extra: dict = None):
        self._current_state = state
        extra = extra or {}

        if extra.get("notice"):
            self.status_label.setText(extra["notice"])
            return

        st = state.lower()
        if st in ("idle",):
            self.level_bar.hide()
            self.status_label.setText(self._idle_text)
            self._update_style("idle")
        elif st in ("starting", "starting_recording"):
            self.level_bar.hide()
            self.status_label.setText("Starting mic...")
            self._update_style("starting")
        elif st in ("listening", "recording"):
            self.level_bar.setValue(0)
            self.level_bar.show()
            target = extra.get("target_app", "")
            target_str = f" ({target})" if target and target != "unknown" else ""
            self.status_label.setText(f"Listening...{target_str}")
            self._update_style("listening")
        elif st == "audio_level":
            lvl = int(extra.get("level", 0) * 100)
            self.level_bar.setValue(min(lvl, 100))
        elif st in ("stopping", "stopping_recording"):
            self.level_bar.hide()
            self.status_label.setText("Finalizing...")
            self._update_style("stopping")
        elif st in ("processing", "transcribing"):
            self.level_bar.hide()
            self.status_label.setText("Transcribing...")
            self._update_style("processing")
        elif st in ("formatting", "inserting_text"):
            self.level_bar.hide()
            self.status_label.setText("Pasting...")
            self._update_style("formatting")
        elif st in ("pasted", "success"):
            self.level_bar.hide()
            self.status_label.setText("Pasted!")
            self._update_style("pasted")
        elif st in ("cancelled",):
            self.level_bar.hide()
            self.status_label.setText("Cancelled")
            self._update_style("cancelled")
        elif st in ("error",):
            self.level_bar.hide()
            err_msg = extra.get("message", "Error")
            self.status_label.setText(f"Err: {err_msg[:20]}")
            self._update_style("error")

    def _update_style(self, state: str):
        if state == "idle":
            bg = "rgba(15, 23, 42, 0.90)"
            border = "rgba(255, 255, 255, 0.15)"
            btn_bg = "#334155"
            btn_color = "#F8FAFC"
        elif state == "starting":
            bg = "rgba(25, 23, 15, 0.95)"
            border = "#F59E0B"
            btn_bg = "#D97706"
            btn_color = "#FFFFFF"
        elif state == "listening":
            bg = "rgba(23, 15, 25, 0.95)"
            border = "#EF4444"
            btn_bg = "#DC2626"
            btn_color = "#FFFFFF"
        elif state == "stopping":
            bg = "rgba(28, 20, 15, 0.95)"
            border = "#F97316"
            btn_bg = "#EA580C"
            btn_color = "#FFFFFF"
        elif state in ("processing", "formatting"):
            bg = "rgba(24, 20, 15, 0.95)"
            border = "#F59E0B"
            btn_bg = "#D97706"
            btn_color = "#FFFFFF"
        elif state == "pasted":
            bg = "rgba(15, 28, 20, 0.95)"
            border = "#10B981"
            btn_bg = "#059669"
            btn_color = "#FFFFFF"
        elif state == "cancelled":
            bg = "rgba(30, 25, 20, 0.95)"
            border = "#F97316"
            btn_bg = "#EA580C"
            btn_color = "#FFFFFF"
        elif state == "error":
            bg = "rgba(35, 15, 15, 0.95)"
            border = "#EF4444"
            btn_bg = "#991B1B"
            btn_color = "#FFFFFF"
        else:
            bg = "rgba(15, 23, 42, 0.90)"
            border = "rgba(255, 255, 255, 0.15)"
            btn_bg = "#334155"
            btn_color = "#F8FAFC"

        self.setStyleSheet(f"""
            FloatingHUD {{
                background-color: {bg};
                border: 1.5px solid {border};
                border-radius: 26px;
            }}
            QPushButton {{
                background-color: {btn_bg};
                color: {btn_color};
                border: none;
                border-radius: 19px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """)

    # Draggable Pill (Left Click Drag)
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = QPoint()

    def _show_context_menu(self, global_pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1E293B;
                color: #F8FAFC;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #38BDF8;
                color: #0F172A;
            }
        """)

        if self._current_state == "listening":
            action_cancel = menu.addAction("Cancel Recording (Discard)")
            action_cancel.triggered.connect(self.cancel_requested.emit)
        else:
            action_toggle = menu.addAction("Start Dictation")
            action_toggle.triggered.connect(self.toggle_requested.emit)

        action_recopy = menu.addAction("Copy Last Dictation")
        action_recopy.triggered.connect(self.recopy_requested.emit)

        action_settings = menu.addAction("Settings & History")
        action_settings.triggered.connect(self.settings_requested.emit)
        
        menu.addSeparator()
        action_quit = menu.addAction("Exit FlowPilot")
        action_quit.triggered.connect(self.quit_requested.emit)

        menu.exec(global_pos)
