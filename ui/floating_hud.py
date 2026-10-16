"""
FlowPilot Floating Robot Mascot Companion ("Pilot")
Standalone, draggable animated robot companion that sits anywhere on your desktop.

Features:
- Pure robot companion widget (no text clutter or "Ctrl+Shift+Space" labels).
- Fully moveable: Drag and drop to any corner or location on your screen.
- Auto-saves position across app restarts (hud_x, hud_y).
- Context menu with one-click "Snap to Corner" shortcuts.
- Real-time voice reactions:
  - Antennas radiate sound arcs with audio volume.
  - Expressive eyes with natural blinking and voice-reactive pupil dilation.
  - Thinking spirals during polishing/transcription.
  - Celebratory happy smile (^_^) upon pasting into the target window.
- Single-click to start/stop dictation.
- Win32 WS_EX_NOACTIVATE to prevent stealing editor focus.
"""

import sys
import math
import random
import ctypes
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QProgressBar, QMenu, QApplication
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QLinearGradient, QRadialGradient, QFont
)

# Win32 Constants for Non-Activating Window
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008


class FloatingHUD(QWidget):
    """
    "Pilot" — Desktop Robot Companion.
    Draggable, animated mascot that reacts to voice input and sits anywhere on the screen.
    """
    toggle_requested = Signal()
    cancel_requested = Signal()
    recopy_requested = Signal()
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_state = "idle"
        self._audio_level = 0.0
        self._tick = 0
        self._is_blinking = False
        self._blink_counter = 0

        # Load persisted visual style ("mascot", "edge_line", or "wave_bar")
        try:
            from engine.config import load_config
            cfg = load_config()
            self._visual_style = cfg.get("hud_style", "mascot")
        except Exception:
            self._visual_style = "mascot"

        # Mouse dragging tracking
        self._drag_start_pos = QPoint()
        self._drag_offset = QPoint()
        self._is_dragging = False

        self._init_ui()

        # Animation timer (30 FPS for fluid procedural animation)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)
        self._anim_timer.start(33)

    def _apply_style_dimensions(self):
        if self._visual_style == "edge_line":
            self.setFixedSize(14, 68)
        elif self._visual_style == "wave_bar":
            self.setFixedSize(58, 26)
        else:
            self._visual_style = "mascot"
            self.setFixedSize(72, 72)

    def _init_ui(self):
        # Frameless, Always on Top, Tool Window
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._apply_style_dimensions()
        self.setCursor(Qt.PointingHandCursor)

        # Audio level bar (maintained for backward test compatibility)
        self.level_bar = QProgressBar(self)
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.hide()

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE | WS_EX_TOPMOST)
            except Exception as e:
                print(f"[FloatingHUD Warning] Could not apply WS_EX_NOACTIVATE: {e}")

    def set_hotkey_info(self, hotkey_str: str, mode: str = "toggle"):
        # Tooltip with clean hotkey guidance
        clean_hk = hotkey_str.replace("<", "").replace(">", "").strip()
        tip = f"Pilot — Click or hold {clean_hk} to dictate"
        self.setToolTip(tip)

    def update_state(self, state: str, extra: Optional[Dict[str, Any]] = None):
        self._current_state = state.lower()
        extra = extra or {}

        if self._current_state == "audio_level":
            lvl = float(extra.get("level", 0.0))
            self._audio_level = max(0.0, min(1.0, lvl))
            self.level_bar.setValue(min(int(lvl * 100), 100))
            return

        if self._current_state in ("listening", "recording"):
            self.level_bar.setValue(0)
            self.level_bar.show()
        elif self._current_state in ("idle", "pasted", "success", "error", "cancelled"):
            self.level_bar.hide()

        self.update()

    def _on_anim_tick(self):
        self._tick += 1

        # Smooth audio decay
        self._audio_level = max(0.0, self._audio_level * 0.90)

        # Natural random eye blinking
        if self._current_state not in ("pasted", "success", "processing", "transcribing", "validating"):
            if not self._is_blinking:
                if random.random() < 0.018:
                    self._is_blinking = True
                    self._blink_counter = 4
            else:
                self._blink_counter -= 1
                if self._blink_counter <= 0:
                    self._is_blinking = False

        self.update()

    # -------------------------------------------------------------
    # Mouse Interaction: Draggable anywhere & Single-Click Dictate
    # -------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint()
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            curr_pos = event.globalPosition().toPoint()
            delta = (curr_pos - self._drag_start_pos).manhattanLength()
            if delta > 4:
                self._is_dragging = True
                self.move(curr_pos - self._drag_offset)
                event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._is_dragging:
                self._is_dragging = False
                self._save_position()
                event.accept()
            else:
                # It was a click! Toggle dictation
                self.toggle_requested.emit()
                event.accept()

    def set_visual_style(self, style: str):
        if style not in ("mascot", "edge_line", "wave_bar"):
            style = "mascot"
        self._visual_style = style
        self._apply_style_dimensions()
        self._save_position()
        self.update()

    def toggle_visual_style(self):
        """Cycles between Pilot Mascot, Wispr Docked Edge Line, and Wave Equalizer."""
        styles = ["mascot", "edge_line", "wave_bar"]
        try:
            idx = styles.index(self._visual_style)
        except ValueError:
            idx = 0
        next_style = styles[(idx + 1) % len(styles)]
        self.set_visual_style(next_style)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_visual_style()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def _save_position(self):
        try:
            from engine.config import load_config, save_config
            cfg = load_config()
            cfg["hud_x"] = self.pos().x()
            cfg["hud_y"] = self.pos().y()
            cfg["hud_style"] = self._visual_style
            save_config(cfg)
        except Exception:
            pass

    def snap_to_corner(self, corner: str):
        screen = self.screen() or QApplication.primaryScreen()
        if not screen:
            return
        geom = screen.availableGeometry()
        pad = 20

        if corner == "bottom_right":
            x = geom.right() - self.width() - pad
            y = geom.bottom() - self.height() - pad
        elif corner == "bottom_left":
            x = geom.left() + pad
            y = geom.bottom() - self.height() - pad
        elif corner == "top_right":
            x = geom.right() - self.width() - pad
            y = geom.top() + pad
        elif corner == "top_left":
            x = geom.left() + pad
            y = geom.top() + pad
        elif corner == "left_edge":
            x = geom.left() + 6
            y = geom.center().y() - (self.height() // 2)
        elif corner == "right_edge":
            x = geom.right() - self.width() - 6
            y = geom.center().y() - (self.height() // 2)
        else:  # bottom_center
            x = geom.center().x() - (self.width() // 2)
            y = geom.bottom() - self.height() - pad

        self.move(x, y)
        self._save_position()

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

        if self._current_state in ("listening", "recording"):
            action_cancel = menu.addAction("Cancel Dictation")
            action_cancel.triggered.connect(self.cancel_requested.emit)
        else:
            action_toggle = menu.addAction("Start Dictation")
            action_toggle.triggered.connect(self.toggle_requested.emit)

        action_recopy = menu.addAction("Copy Last Dictation")
        action_recopy.triggered.connect(self.recopy_requested.emit)

        menu.addSeparator()

        # Appearance style submenu
        style_menu = menu.addMenu("Appearance Style...")
        style_menu.setStyleSheet(menu.styleSheet())
        act_mascot = style_menu.addAction("🤖 Robot Mascot Companion ('Pilot')")
        act_mascot.triggered.connect(lambda: self.set_visual_style("mascot"))
        act_edge = style_menu.addAction("📏 Wispr Flow Docked Edge Line")
        act_edge.triggered.connect(lambda: self.set_visual_style("edge_line"))
        act_waves = style_menu.addAction("🌊 Wispr Wave Equalizer")
        act_waves.triggered.connect(lambda: self.set_visual_style("wave_bar"))

        menu.addSeparator()

        # Snap to Corner submenu
        corner_menu = menu.addMenu("Move Companion to...")
        corner_menu.setStyleSheet(menu.styleSheet())
        corner_menu.addAction("Bottom-Right Corner", lambda: self.snap_to_corner("bottom_right"))
        corner_menu.addAction("Bottom-Left Corner", lambda: self.snap_to_corner("bottom_left"))
        corner_menu.addAction("Top-Right Corner", lambda: self.snap_to_corner("top_right"))
        corner_menu.addAction("Top-Left Corner", lambda: self.snap_to_corner("top_left"))
        corner_menu.addAction("Left Edge (Middle)", lambda: self.snap_to_corner("left_edge"))
        corner_menu.addAction("Right Edge (Middle)", lambda: self.snap_to_corner("right_edge"))
        corner_menu.addAction("Bottom-Center", lambda: self.snap_to_corner("bottom_center"))

        menu.addSeparator()

        action_settings = menu.addAction("Settings & History")
        action_settings.triggered.connect(self.settings_requested.emit)

        action_quit = menu.addAction("Exit FlowPilot")
        action_quit.triggered.connect(self.quit_requested.emit)

        menu.exec(global_pos)

    # -------------------------------------------------------------
    # Procedural 60 FPS Mascot Rendering
    # -------------------------------------------------------------
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        st = self._current_state

        # Branch A: Wispr Flow Docked Edge Line (Minimalist sleek vertical bar)
        if self._visual_style == "edge_line":
            bar_w = 6.0 + (self._audio_level * 4.0 if st in ("listening", "recording") else 0.0)
            bar_h = 42.0 + (self._audio_level * 18.0 if st in ("listening", "recording") else 0.0)
            bx = (w - bar_w) / 2.0
            by = (h - bar_h) / 2.0

            if st in ("listening", "recording"):
                # Outer acoustic glow
                glow_rad = 14.0 + (self._audio_level * 6.0)
                glow_grad = QRadialGradient(w / 2.0, h / 2.0, glow_rad)
                glow_grad.setColorAt(0.0, QColor(56, 189, 248, 160))
                glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(glow_grad))
                p.drawEllipse(QPoint(int(w / 2.0), int(h / 2.0)), int(glow_rad), int(glow_rad))

                fill_grad = QLinearGradient(bx, by, bx, by + bar_h)
                fill_grad.setColorAt(0.0, QColor("#38BDF8"))
                fill_grad.setColorAt(1.0, QColor("#06B6D4"))
                p.setPen(QPen(QColor("#E0F2FE"), 1.0))
                p.setBrush(QBrush(fill_grad))
            elif st in ("processing", "transcribing", "validating"):
                fill_grad = QLinearGradient(bx, by, bx, by + bar_h)
                fill_grad.setColorAt(0.0, QColor("#F59E0B"))
                fill_grad.setColorAt(1.0, QColor("#D97706"))
                p.setPen(QPen(QColor("#FEF3C7"), 1.0))
                p.setBrush(QBrush(fill_grad))
            elif st in ("pasted", "success"):
                fill_grad = QLinearGradient(bx, by, bx, by + bar_h)
                fill_grad.setColorAt(0.0, QColor("#10B981"))
                fill_grad.setColorAt(1.0, QColor("#059669"))
                p.setPen(QPen(QColor("#D1FAE5"), 1.0))
                p.setBrush(QBrush(fill_grad))
            else:  # idle
                fill_grad = QLinearGradient(bx, by, bx, by + bar_h)
                fill_grad.setColorAt(0.0, QColor("#334155"))
                fill_grad.setColorAt(1.0, QColor("#1E293B"))
                p.setPen(QPen(QColor("#64748B"), 1.0))
                p.setBrush(QBrush(fill_grad))

            p.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)
            p.end()
            return

        # Branch B: Wispr Soundwave Equalizer (5 dancing wave bars)
        if self._visual_style == "wave_bar":
            p.setPen(QPen(QColor("#334155"), 1.2))
            p.setBrush(QBrush(QColor(15, 23, 42, 220)))
            p.drawRoundedRect(QRectF(2, 2, w - 4, h - 4), 10.0, 10.0)

            num_bars = 5
            bar_w = 4.0
            bar_gap = 4.5
            total_w = (num_bars * bar_w) + ((num_bars - 1) * bar_gap)
            start_x = (w - total_w) / 2.0
            cy = h / 2.0

            bar_color = QColor("#38BDF8") if st in ("listening", "recording") else QColor("#94A3B8")
            if st in ("processing", "transcribing", "validating"):
                bar_color = QColor("#F59E0B")
            elif st in ("pasted", "success"):
                bar_color = QColor("#10B981")

            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(bar_color))

            for i in range(num_bars):
                bx = start_x + (i * (bar_w + bar_gap))
                if st in ("listening", "recording"):
                    phase = (self._tick * 0.45) + (i * 0.95)
                    bh = 6.0 + (self._audio_level * 10.0) + math.sin(phase) * 3.0
                elif st in ("processing", "transcribing", "validating"):
                    bh = 5.0 + math.sin((self._tick * 0.35) + i) * 3.5
                else:
                    bh = 5.0
                bh = max(4.0, min(16.0, bh))
                by = cy - (bh / 2.0)
                p.drawRoundedRect(QRectF(bx, by, bar_w, bh), 2.0, 2.0)

            p.end()
            return

        # Branch C: Procedural 60 FPS Robot Mascot Companion ("Pilot")
        cx = w / 2.0
        cy = h / 2.0 + 4.0

        # 1. Reactive Halo Glow
        if st in ("listening", "recording"):
            pulse_rad = 28.0 + (self._audio_level * 6.5) + math.sin(self._tick * 0.4) * 2.0
            glow_grad = QRadialGradient(cx, cy, pulse_rad)
            glow_grad.setColorAt(0.0, QColor(6, 182, 212, 130))
            glow_grad.setColorAt(0.65, QColor(168, 85, 247, 45))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow_grad))
            p.drawEllipse(QPoint(int(cx), int(cy)), int(pulse_rad), int(pulse_rad))

            # Sound radiating arcs above head
            p.setPen(QPen(QColor(56, 189, 248, 210), 2.0, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            arc_offset = math.sin(self._tick * 0.5) * 2.0
            p.drawArc(int(cx - 16), int(cy - 29 + arc_offset), 32, 14, 45 * 16, 90 * 16)

        elif st in ("pasted", "success"):
            glow_grad = QRadialGradient(cx, cy, 28.0)
            glow_grad.setColorAt(0.0, QColor(16, 185, 129, 130))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow_grad))
            p.drawEllipse(QPoint(int(cx), int(cy)), 28, 28)

        elif st in ("processing", "transcribing", "validating"):
            glow_grad = QRadialGradient(cx, cy, 27.0)
            glow_grad.setColorAt(0.0, QColor(245, 158, 11, 110))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow_grad))
            p.drawEllipse(QPoint(int(cx), int(cy)), 27, 27)

        # 2. Cute Head Antenna
        antenna_h = 9.0 + (self._audio_level * 6.0 if st in ("listening", "recording") else 0.0)
        p.setPen(QPen(QColor(148, 163, 184), 2.2, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(cx), int(cy - 17), int(cx), int(cy - 17 - antenna_h))

        # Antenna Bulb (Tip)
        tip_color = QColor("#38BDF8") if st in ("listening", "recording") else QColor("#94A3B8")
        if st in ("processing", "transcribing", "validating"):
            tip_color = QColor("#F59E0B")
        elif st in ("pasted", "success"):
            tip_color = QColor("#10B981")

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(tip_color))
        tip_r = 4.0 + (self._audio_level * 1.8 if st in ("listening", "recording") else 0.0)
        p.drawEllipse(QPoint(int(cx), int(cy - 17 - antenna_h)), int(tip_r), int(tip_r))

        # 3. Mascot Body / Head (Cute rounded capsule robot)
        head_w = 44.0
        head_h = 34.0
        head_rect = QRectF(cx - head_w / 2.0, cy - head_h / 2.0, head_w, head_h)

        head_grad = QLinearGradient(cx, cy - head_h / 2.0, cx, cy + head_h / 2.0)
        head_grad.setColorAt(0.0, QColor("#1E293B"))  # Deep slate
        head_grad.setColorAt(1.0, QColor("#0F172A"))  # Dark midnight

        border_c = QColor("#38BDF8") if st in ("listening", "recording") else QColor("#475569")
        if st in ("pasted", "success"):
            border_c = QColor("#10B981")
        elif st in ("processing", "validating"):
            border_c = QColor("#F59E0B")

        p.setPen(QPen(border_c, 1.8))
        p.setBrush(QBrush(head_grad))
        p.drawRoundedRect(head_rect, 16.0, 16.0)

        # 4. Soft Rosy Cheeks
        blush_color = QColor(244, 114, 182, 115)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(blush_color))
        p.drawEllipse(QRectF(cx - 17.0, cy + 3.0, 6.0, 4.0))
        p.drawEllipse(QRectF(cx + 11.0, cy + 3.0, 6.0, 4.0))

        # 5. Expressive Eyes
        eye_y = cy - 2.5
        eye_spacing = 9.0
        eye_rad = 5.6

        if st in ("pasted", "success"):
            # Happy smiling closed eyes: ( ^ _ ^ )
            p.setPen(QPen(QColor("#10B981"), 2.2, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            p.drawArc(int(cx - eye_spacing - 5), int(eye_y - 4), 10, 8, 30 * 16, 120 * 16)
            p.drawArc(int(cx + eye_spacing - 5), int(eye_y - 4), 10, 8, 30 * 16, 120 * 16)
            # Happy smile mouth
            p.drawArc(int(cx - 4), int(cy + 4), 8, 5, 200 * 16, 140 * 16)

        elif self._is_blinking:
            # Cute sleepy closed lines: (- -)
            p.setPen(QPen(QColor("#E2E8F0"), 2.0, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(cx - eye_spacing - 4), int(eye_y), int(cx - eye_spacing + 4), int(eye_y))
            p.drawLine(int(cx + eye_spacing - 4), int(eye_y), int(cx + eye_spacing + 4), int(eye_y))

        elif st in ("processing", "transcribing", "validating"):
            # Thinking spiral / swivel eyes
            p.setPen(QPen(QColor("#F59E0B"), 2.0, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            spin_angle = (self._tick * 15) % 360
            p.drawArc(int(cx - eye_spacing - 4.5), int(eye_y - 4.5), 9, 9, spin_angle * 16, 270 * 16)
            p.drawArc(int(cx + eye_spacing - 4.5), int(eye_y - 4.5), 9, 9, -spin_angle * 16, 270 * 16)

        else:
            # Attentive, open glossy eyes (listening or idle)
            for side in (-1, 1):
                ex = cx + side * eye_spacing

                # White Sclera
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor("#FFFFFF")))
                p.drawEllipse(QPoint(int(ex), int(eye_y)), int(eye_rad), int(eye_rad))

                # Pupil (dilates dynamically with voice audio level)
                pupil_r = 2.6 + (self._audio_level * 2.2 if st in ("listening", "recording") else 0.0)
                pupil_color = QColor("#0284C7") if st in ("listening", "recording") else QColor("#0F172A")
                p.setBrush(QBrush(pupil_color))
                p.drawEllipse(QPoint(int(ex), int(eye_y)), int(pupil_r), int(pupil_r))

                # Specular Sparkle Highlight
                p.setBrush(QBrush(QColor("#FFFFFF")))
                p.drawEllipse(QPoint(int(ex + 1.2), int(eye_y - 1.2)), 1, 1)

        p.end()
