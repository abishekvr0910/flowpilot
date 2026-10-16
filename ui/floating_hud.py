"""
FlowPilot Floating Microphone HUD ("Flow Pill")
Frameless, always-on-top, translucent pill widget.
Equipped with:
1. Wispr Flow-style animated audio waveform bars (replacing emoji mic).
2. "Pilot" — An adorable animated cartoon listening mascot companion.
3. Fluid sound-reactive animation matching PortAudio RMS volume.
4. Clean human-friendly typography (zero developer debugging clutter).
5. WS_EX_NOACTIVATE to prevent stealing focus from active editors.
"""

import sys
import math
import random
import ctypes
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QPushButton, QProgressBar,
    QGraphicsDropShadowEffect, QMenu, QStackedWidget
)
from PySide6.QtCore import Qt, QPoint, Signal, QSize, QTimer, QRectF
from PySide6.QtGui import (
    QColor, QFont, QPainter, QBrush, QPen, QLinearGradient,
    QRadialGradient, QAction, QIcon
)

# Win32 Constants for Non-Activating Window
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008


class WisprWaveWidget(QWidget):
    """
    Sleek, minimalist animated vertical soundwave visualizer inspired by Wispr Flow.
    5 dynamic equalizer bars that fluidly dance, expand, and oscillate with microphone audio levels.
    """
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 36)
        self.setCursor(Qt.PointingHandCursor)
        self._state = "idle"
        self._audio_level = 0.0
        self._phase = 0.0

        # Animation loop (60 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(16)

    def set_state(self, state: str):
        self._state = state.lower()
        self.update()

    def set_audio_level(self, level: float):
        self._audio_level = max(0.0, min(1.0, level))
        self.update()

    def _on_tick(self):
        self._phase += 0.12
        if self._phase > 1000.0:
            self._phase = 0.0
        # Decay audio level smoothly
        self._audio_level = max(0.0, self._audio_level * 0.92)
        if self._state in ("listening", "recording", "processing", "transcribing", "starting"):
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        elif event.button() == Qt.RightButton:
            event.ignore()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cy = h / 2.0

        num_bars = 5
        bar_w = 3.6
        spacing = 4.2
        total_w = num_bars * bar_w + (num_bars - 1) * spacing
        start_x = (w - total_w) / 2.0

        multipliers = [0.45, 0.85, 1.0, 0.85, 0.45]

        # Select color palette based on state
        if self._state in ("listening", "recording"):
            grad_c1 = QColor("#06B6D4")  # Electric Cyan
            grad_c2 = QColor("#A855F7")  # Neon Purple
        elif self._state in ("processing", "transcribing", "validating", "formatting"):
            grad_c1 = QColor("#F59E0B")  # Amber Glow
            grad_c2 = QColor("#EC4899")  # Pink
        elif self._state in ("pasted", "success"):
            grad_c1 = QColor("#10B981")  # Emerald
            grad_c2 = QColor("#34D399")  # Mint
        elif self._state in ("error",):
            grad_c1 = QColor("#EF4444")
            grad_c2 = QColor("#F87171")
        else:
            # Idle
            grad_c1 = QColor("#64748B")  # Slate
            grad_c2 = QColor("#38BDF8")  # Soft Cyan

        for i in range(num_bars):
            bx = start_x + i * (bar_w + spacing)

            if self._state in ("listening", "recording"):
                # Dynamic soundwave bounce based on real audio level + organic harmonic oscillation
                voice_boost = self._audio_level * 22.0 * multipliers[i]
                harmonic = math.sin(self._phase * 1.8 + i * 1.2) * (3.0 + self._audio_level * 5.0)
                bh = max(5.0, min(28.0, 6.0 + voice_boost + harmonic))
            elif self._state in ("processing", "transcribing", "validating"):
                # Sweeping shimmer wave left-to-right
                bh = 6.0 + math.sin(self._phase * 2.2 + i * 1.1) * 7.0
            elif self._state in ("pasted", "success"):
                bh = 10.0 + math.sin(i * 0.8) * 4.0
            else:
                # Idle resting line / gentle subtle breathing
                bh = 4.5 + math.sin(self._phase * 0.5 + i * 0.6) * 1.2

            by = cy - bh / 2.0

            grad = QLinearGradient(bx, by, bx, by + bh)
            grad.setColorAt(0.0, grad_c1)
            grad.setColorAt(1.0, grad_c2)

            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(grad))
            p.drawRoundedRect(QRectF(bx, by, bar_w, bh), bar_w / 2.0, bar_w / 2.0)

        p.end()


class CartoonMascotWidget(QWidget):
    """
    "Pilot" — An expressive, animated cartoon listening companion.
    Features:
    - Glowing listening antennae that perk up and radiate sound waves when you speak.
    - Big expressive procedural eyes with natural randomized blinking and voice dilation.
    - Thinking tilts and sparkle states during Whisper transcription.
    - Happy (^_^) celebration when text is pasted!
    """
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(44, 40)
        self.setCursor(Qt.PointingHandCursor)
        self._state = "idle"
        self._audio_level = 0.0
        self._tick = 0
        self._is_blinking = False
        self._blink_counter = 0

        # Animation timer (30 FPS)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(33)

    def set_state(self, state: str):
        self._state = state.lower()
        self.update()

    def set_audio_level(self, level: float):
        self._audio_level = max(0.0, min(1.0, level))
        self.update()

    def _on_tick(self):
        self._tick += 1

        # Smooth audio decay
        self._audio_level = max(0.0, self._audio_level * 0.90)

        # Natural random eye blink logic
        if self._state not in ("pasted", "processing"):
            if not self._is_blinking:
                if random.random() < 0.015:  # Trigger blink
                    self._is_blinking = True
                    self._blink_counter = 4
            else:
                self._blink_counter -= 1
                if self._blink_counter <= 0:
                    self._is_blinking = False

        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
        elif event.button() == Qt.RightButton:
            event.ignore()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0 + 3.0

        # 1. Sound Waves / Glow effect when listening
        if self._state in ("listening", "recording"):
            pulse_rad = 18.0 + (self._audio_level * 6.0) + math.sin(self._tick * 0.4) * 2.0
            glow_grad = QRadialGradient(cx, cy, pulse_rad)
            glow_grad.setColorAt(0.0, QColor(6, 182, 212, 110))
            glow_grad.setColorAt(0.7, QColor(168, 85, 247, 40))
            glow_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
            p.setPen(Qt.NoPen)
            p.setBrush(QBrush(glow_grad))
            p.drawEllipse(QPoint(int(cx), int(cy)), int(pulse_rad), int(pulse_rad))

            # Sound radiating arcs above head
            p.setPen(QPen(QColor(56, 189, 248, 160), 1.5, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            arc_offset = math.sin(self._tick * 0.5) * 2.0
            p.drawArc(int(cx - 14), int(cy - 22 + arc_offset), 28, 12, 45 * 16, 90 * 16)

        # 2. Cute Head Antenna
        antenna_h = 7.0 + (self._audio_level * 5.0 if self._state in ("listening", "recording") else 0.0)
        p.setPen(QPen(QColor(100, 116, 139), 1.8, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(cx), int(cy - 14), int(cx), int(cy - 14 - antenna_h))

        # Antenna Bulb (Tip)
        tip_color = QColor("#38BDF8") if self._state in ("listening", "recording") else QColor("#94A3B8")
        if self._state in ("processing", "transcribing"):
            tip_color = QColor("#F59E0B")
        elif self._state in ("pasted", "success"):
            tip_color = QColor("#10B981")

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(tip_color))
        tip_r = 3.2 + (self._audio_level * 1.5 if self._state in ("listening", "recording") else 0.0)
        p.drawEllipse(QPoint(int(cx), int(cy - 14 - antenna_h)), int(tip_r), int(tip_r))

        # 3. Mascot Body / Head (Cute rounded capsule robot)
        head_w = 32.0
        head_h = 24.0
        head_rect = QRectF(cx - head_w / 2.0, cy - head_h / 2.0, head_w, head_h)

        head_grad = QLinearGradient(cx, cy - head_h / 2.0, cx, cy + head_h / 2.0)
        head_grad.setColorAt(0.0, QColor("#1E293B"))  # Deep slate
        head_grad.setColorAt(1.0, QColor("#0F172A"))  # Dark midnight

        p.setPen(QPen(QColor("#334155"), 1.5))
        p.setBrush(QBrush(head_grad))
        p.drawRoundedRect(head_rect, 12.0, 12.0)

        # 4. Soft Rosy Cheeks
        blush_color = QColor(244, 114, 182, 85)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(blush_color))
        p.drawEllipse(QRectF(cx - 12.5, cy + 2.5, 4.5, 3.0))
        p.drawEllipse(QRectF(cx + 8.0, cy + 2.5, 4.5, 3.0))

        # 5. Expressive Eyes
        eye_y = cy - 2.0
        eye_spacing = 6.5
        eye_rad = 4.2

        if self._state in ("pasted", "success"):
            # Happy smiling closed eyes: ( ^ _ ^ )
            p.setPen(QPen(QColor("#10B981"), 2.0, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            # Left arc
            p.drawArc(int(cx - eye_spacing - 4), int(eye_y - 3), 8, 7, 30 * 16, 120 * 16)
            # Right arc
            p.drawArc(int(cx + eye_spacing - 4), int(eye_y - 3), 8, 7, 30 * 16, 120 * 16)
            # Smile
            p.drawArc(int(cx - 3), int(cy + 2), 6, 4, 200 * 16, 140 * 16)

        elif self._is_blinking:
            # Cute sleepy closed lines: (- -)
            p.setPen(QPen(QColor("#E2E8F0"), 1.8, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(int(cx - eye_spacing - 3), int(eye_y), int(cx - eye_spacing + 3), int(eye_y))
            p.drawLine(int(cx + eye_spacing - 3), int(eye_y), int(cx + eye_spacing + 3), int(eye_y))

        elif self._state in ("processing", "transcribing", "validating"):
            # Thinking spiral / swivel eyes
            p.setPen(QPen(QColor("#F59E0B"), 1.8, Qt.SolidLine, Qt.RoundCap))
            p.setBrush(Qt.NoBrush)
            spin_angle = (self._tick * 15) % 360
            p.drawArc(int(cx - eye_spacing - 3.5), int(eye_y - 3.5), 7, 7, spin_angle * 16, 270 * 16)
            p.drawArc(int(cx + eye_spacing - 3.5), int(eye_y - 3.5), 7, 7, -spin_angle * 16, 270 * 16)

        else:
            # Attentive, open glossy eyes (listening or idle)
            for side in (-1, 1):
                ex = cx + side * eye_spacing

                # White Sclera
                p.setPen(Qt.NoPen)
                p.setBrush(QBrush(QColor("#FFFFFF")))
                p.drawEllipse(QPoint(int(ex), int(eye_y)), int(eye_rad), int(eye_rad))

                # Pupil (dilates dynamically with voice audio level)
                pupil_r = 2.0 + (self._audio_level * 1.6 if self._state in ("listening", "recording") else 0.0)
                pupil_color = QColor("#0284C7") if self._state in ("listening", "recording") else QColor("#0F172A")
                p.setBrush(QBrush(pupil_color))
                p.drawEllipse(QPoint(int(ex), int(eye_y)), int(pupil_r), int(pupil_r))

                # Specular Sparkle Highlight
                p.setBrush(QBrush(QColor("#FFFFFF")))
                p.drawEllipse(QPoint(int(ex + 1), int(eye_y - 1)), 1, 1)

        p.end()


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
        try:
            from engine.config import load_config
            cfg = load_config()
            self._hud_style = cfg.get("hud_style", "mascot")
        except Exception:
            self._hud_style = "mascot"  # "mascot" (Cartoon companion Pilot) or "wave" (Wispr dynamic bars)
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
        # Frameless, Always on Top, Tool Window
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(320, 52)

        # Main Layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 18, 6)
        layout.setSpacing(12)

        # 1. Dual-Mode Visual Indicator Stack (Wispr Wave Bars OR Cartoon Mascot)
        self.visual_stack = QStackedWidget(self)
        self.visual_stack.setFixedSize(44, 38)

        self.wave_widget = WisprWaveWidget(self)
        self.wave_widget.clicked.connect(self._on_action_clicked)
        self.visual_stack.addWidget(self.wave_widget)

        self.mascot_widget = CartoonMascotWidget(self)
        self.mascot_widget.clicked.connect(self._on_action_clicked)
        self.visual_stack.addWidget(self.mascot_widget)

        layout.addWidget(self.visual_stack)

        # 2. Clean Human-Friendly Status Label
        self.status_label = QLabel(self._idle_text, self)
        font = QFont("Segoe UI", 10, QFont.DemiBold)
        self.status_label.setFont(font)
        self.status_label.setStyleSheet("color: #F1F5F9;")
        self.status_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        layout.addWidget(self.status_label, 1)

        # 3. Compact Audio Level Bar (preserved for backward compatibility with tests)
        self.level_bar = QProgressBar(self)
        self.level_bar.setRange(0, 100)
        self.level_bar.setValue(0)
        self.level_bar.setTextVisible(False)
        self.level_bar.setFixedSize(36, 6)
        self.level_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.12);
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #38BDF8;
                border-radius: 3px;
            }
        """)
        self.level_bar.hide()
        layout.addWidget(self.level_bar)

        # Subtle Drop Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._apply_hud_style()
        self._update_style("idle")

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

    def _on_action_clicked(self):
        self.toggle_requested.emit()

    def toggle_visual_style(self):
        new_style = "wave" if self._hud_style == "mascot" else "mascot"
        self.set_visual_style(new_style)

    def set_visual_style(self, style: str):
        """Switches between 'wave' (Wispr Waveform Bars) and 'mascot' (Cartoon Character)."""
        self._hud_style = "mascot" if style == "mascot" else "wave"
        self._apply_hud_style()
        try:
            from engine.config import load_config, save_config
            cfg = load_config()
            if cfg.get("hud_style") != self._hud_style:
                cfg["hud_style"] = self._hud_style
                save_config(cfg)
        except Exception:
            pass
        if self._current_state in ("idle", "IDLE"):
            msg = "Cartoon Mascot Active" if self._hud_style == "mascot" else "Wispr Wave Active"
            self.status_label.setText(msg)
            QTimer.singleShot(1400, lambda: self.status_label.setText(self._idle_text) if self._current_state in ("idle", "IDLE") else None)

    def _apply_hud_style(self):
        if self._hud_style == "mascot":
            self.visual_stack.setCurrentWidget(self.mascot_widget)
        else:
            self.visual_stack.setCurrentWidget(self.wave_widget)

    def update_state(self, state: str, extra: dict = None):
        self._current_state = state
        extra = extra or {}

        # Forward state to visualizers
        self.wave_widget.set_state(state)
        self.mascot_widget.set_state(state)

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
            self.status_label.setText("Listening...")
            self._update_style("starting")
        elif st in ("listening", "recording"):
            self.level_bar.setValue(0)
            self.level_bar.show()
            self.status_label.setText("Listening...")
            self._update_style("listening")
        elif st == "audio_level":
            lvl = float(extra.get("level", 0))
            self.level_bar.setValue(min(int(lvl * 100), 100))
            self.wave_widget.set_audio_level(lvl)
            self.mascot_widget.set_audio_level(lvl)
        elif st in ("stopping", "stopping_recording"):
            self.level_bar.hide()
            self.status_label.setText("Processing...")
            self._update_style("stopping")
        elif st in ("processing", "transcribing"):
            self.level_bar.hide()
            self.status_label.setText("Transcribing...")
            self._update_style("processing")
        elif st in ("validating",):
            self.level_bar.hide()
            self.status_label.setText("Polishing...")
            self._update_style("validating")
        elif st in ("formatting", "inserting_text"):
            self.level_bar.hide()
            self.status_label.setText("Pasting...")
            self._update_style("formatting")
        elif st in ("pasted", "success"):
            self.level_bar.hide()
            self.status_label.setText("Done ✓")
            self._update_style("pasted")
        elif st in ("cancelled",):
            self.level_bar.hide()
            self.status_label.setText("Cancelled")
            self._update_style("cancelled")
        elif st in ("error",):
            self.level_bar.hide()
            self.status_label.setText("Error")
            self._update_style("error")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(1.0, 1.0, self.width() - 2.0, self.height() - 2.0)

        st = self._current_state.lower()
        if st in ("listening", "recording"):
            bg = QColor(15, 23, 42, 246)
            border = QColor(6, 182, 212, 210)      # Glowing Cyan
        elif st in ("processing", "transcribing", "validating"):
            bg = QColor(15, 23, 42, 246)
            border = QColor(245, 158, 11, 200)     # Amber glow
        elif st in ("formatting", "inserting_text"):
            bg = QColor(15, 23, 42, 246)
            border = QColor(14, 165, 233, 200)     # Sky blue
        elif st in ("pasted", "success"):
            bg = QColor(15, 28, 20, 246)
            border = QColor(16, 185, 129, 210)     # Emerald
        elif st == "cancelled":
            bg = QColor(28, 20, 15, 246)
            border = QColor(249, 115, 22, 180)     # Orange
        elif st == "error":
            bg = QColor(35, 15, 15, 246)
            border = QColor(239, 68, 68, 210)      # Crimson
        else:
            bg = QColor(15, 23, 42, 240)           # Midnight glass
            border = QColor(255, 255, 255, 38)

        p.setPen(QPen(border, 1.6))
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(rect, 25.0, 25.0)
        p.end()

    def _update_style(self, state: str):
        st = state.lower()
        if st in ("listening", "recording"):
            self.status_label.setStyleSheet("color: #38BDF8; font-weight: 600;")
        elif st in ("processing", "transcribing", "validating"):
            self.status_label.setStyleSheet("color: #FCD34D; font-weight: 600;")
        elif st in ("pasted", "success"):
            self.status_label.setStyleSheet("color: #34D399; font-weight: 600;")
        elif st in ("error",):
            self.status_label.setStyleSheet("color: #F87171; font-weight: 600;")
        else:
            self.status_label.setStyleSheet("color: #F1F5F9; font-weight: 500;")
        self.update()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_visual_style()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

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

        # Style Toggle Action
        if self._hud_style == "wave":
            action_style = menu.addAction("Switch Visual: Cartoon Mascot ('Pilot')")
            action_style.triggered.connect(lambda: self.set_visual_style("mascot"))
        else:
            action_style = menu.addAction("Switch Visual: Wispr Wave Bars")
            action_style.triggered.connect(lambda: self.set_visual_style("wave"))

        menu.addSeparator()

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
