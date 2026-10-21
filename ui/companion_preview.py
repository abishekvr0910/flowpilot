"""
FlowPilot Companion Preview Widget
Provides an isolated, sandboxed preview of any built-in or custom companion.
Simulates all states (idle, listening, processing, success, error) and motion presets
using QPainter transformations without starting live microphone capture or injecting text.
"""

import sys
import math
from pathlib import Path
from typing import Dict, Any, Optional

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QElapsedTimer
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QPixmap, QImage, QLinearGradient, QRadialGradient
)

from ui.companion_renderer import CompanionRenderer

try:
    import ui.pet_sprites as ps
except Exception:
    try:
        import pet_sprites as ps
    except Exception:
        ps = None

class CompanionPreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(140, 140)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._companion_data: Dict[str, Any] = {"id": "kitty", "type": "builtin"}
        self._palette: str = "orange tabby"
        self._preview_state: str = "idle"
        self._motion_preset: str = "gentle_bob"
        self._reduced_motion: bool = False
        self._tick: int = 0
        self._audio_sim: float = 0.0

        # High-precision elapsed timer for frame-rate-independent animation
        self._elapsed_timer = QElapsedTimer()
        self._elapsed_timer.start()
        self._state_timer = QElapsedTimer()
        self._state_timer.start()

        # Animation timer (30 FPS)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_tick)
        self._anim_timer.start(33)

    def set_companion(self, companion_data: Dict[str, Any], palette: str = "orange tabby", motion_preset: str = "gentle_bob", reduced_motion: bool = False):
        self._companion_data = dict(companion_data)
        self._palette = palette
        self._motion_preset = motion_preset
        self._reduced_motion = reduced_motion
        self.update()

    def set_preview_state(self, state: str):
        if CompanionRenderer.normalize_state(self._preview_state) != CompanionRenderer.normalize_state(state):
            self._state_timer.restart()
        self._preview_state = state.lower()
        self.update()

    def set_motion_preset(self, preset: str, reduced_motion: bool = False):
        self._motion_preset = preset
        self._reduced_motion = reduced_motion
        self.update()

    def set_palette(self, palette: str):
        self._palette = palette
        self.update()

    def _on_tick(self):
        self._tick += 1
        if self._preview_state == "listening":
            # Simulate natural breathing audio envelope
            self._audio_sim = 0.40 + 0.35 * math.sin(self._tick * 0.18)
        else:
            self._audio_sim = 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        center_x = self.width() / 2.0
        center_y = self.height() / 2.0

        painter.save()
        painter.translate(center_x, center_y)

        # Apply motion presets (strictly suppressed if reduced_motion is true)
        if not self._reduced_motion and self._companion_data.get("id") not in ("kiki", "courier"):
            t = self._tick * 0.08
            preset = self._motion_preset

            if preset == "gentle_bob":
                dy = 4.0 * math.sin(t)
                painter.translate(0, dy)
            elif preset == "tiny_tilt":
                deg = 5.0 * math.sin(t)
                painter.rotate(deg)
            elif preset == "breathe":
                scale = 1.0 + 0.04 * math.sin(t)
                painter.scale(scale, scale)
            elif preset == "audio_pulse":
                scale = 1.0 + (self._audio_sim * 0.12)
                painter.scale(scale, scale)
            elif preset == "celebration":
                jump = -abs(8.0 * math.sin(t * 1.5))
                painter.translate(0, jump)

        comp_type = self._companion_data.get("type", "builtin")
        comp_id = self._companion_data.get("id", "kitty")

        elapsed_ms = self._elapsed_timer.elapsed() if hasattr(self, "_elapsed_timer") else (self._tick * 33.0)
        bounds = QRectF(-36, -36, 72, 72)
        dpr = self.devicePixelRatioF() if hasattr(self, "devicePixelRatioF") else 1.0

        CompanionRenderer.render(
            painter=painter,
            bounds=bounds,
            style=comp_id,
            state=self._preview_state,
            elapsed_ms=elapsed_ms,
            audio_level=self._audio_sim,
            palette=self._palette,
            reduced_motion=self._reduced_motion,
            device_pixel_ratio=dpr,
            is_preview=True,
            custom_data=self._companion_data if comp_type != "builtin" else None,
            state_elapsed_ms=self._state_timer.elapsed()
        )

        painter.restore()

        # Draw miniature state badge in bottom corner
        self._draw_state_badge(painter)
        painter.end()

    def _draw_builtin(self, painter: QPainter, comp_id: str):
        elapsed_ms = self._elapsed_timer.elapsed() if hasattr(self, "_elapsed_timer") else (self._tick * 33.0)
        CompanionRenderer.render(painter, QRectF(-36, -36, 72, 72), comp_id, self._preview_state, elapsed_ms, self._audio_sim, self._palette, self._reduced_motion)
        if comp_id == "kitty":
            self._draw_kitty(painter)
        elif comp_id == "dog":
            self._draw_dog(painter)
        elif comp_id in ("fox", "dino", "ghost", "bunny", "pikachu", "charmander", "gengar", "eevee"):
            self._draw_retro_companion(painter, comp_id)
        elif comp_id == "mascot":
            self._draw_robot(painter)
        elif comp_id == "edge_line":
            self._draw_edge_line(painter)
        elif comp_id == "wave_bar":
            self._draw_wave_bar(painter)
        else:
            self._draw_kitty(painter)

    def _draw_dog(self, painter: QPainter):
        if not ps:
            self._draw_fallback_text(painter, "🐶 Pup")
            return
        frame = "dog_sit_b" if self._preview_state in ("listening", "success") else "dog_sit_a"
        pal = self._palette if self._palette in ("shiba inu", "golden retriever", "corgi", "husky") else "shiba inu"
        pix = ps.render_pup_pixmap(frame, palette_name=pal, scale=2)
        if pix and not pix.isNull():
            w = pix.width()
            h = pix.height()
            painter.drawPixmap(int(-w / 2), int(-h / 2), pix)
        else:
            self._draw_fallback_text(painter, "🐶")

    def _draw_retro_companion(self, painter: QPainter, comp_name: str):
        if not ps:
            self._draw_fallback_text(painter, comp_name.capitalize())
            return
        frame = "wag" if self._preview_state in ("listening", "success") else "idle"
        pix = ps.render_retro_companion_pixmap(comp_name, frame=frame, scale=2)
        if pix and not pix.isNull():
            w = pix.width()
            h = pix.height()
            painter.drawPixmap(int(-w / 2), int(-h / 2), pix)
        else:
            self._draw_fallback_text(painter, comp_name.capitalize())

    def _draw_pokemon(self, painter: QPainter, pkmn_name: str):
        self._draw_retro_companion(painter, pkmn_name)

    def _draw_kitty(self, painter: QPainter):
        if not ps:
            self._draw_fallback_text(painter, "🐾 Kitty")
            return

        frame = "sit_a"
        if self._preview_state == "listening":
            step = (self._tick // 4) % 4
            frame = ["type_a", "type_b", "knead_a", "knead_b"][step]
        elif self._preview_state in ("processing", "transcribing"):
            frame = "sit_b"
        elif self._preview_state == "success":
            frame = "stretch"
        elif self._preview_state == "error":
            frame = "sit_a"

        pix = ps.render_kitty_pixmap(frame, palette_name=self._palette, scale=2)
        if pix and not pix.isNull():
            w = pix.width()
            h = pix.height()
            painter.drawPixmap(int(-w / 2), int(-h / 2), pix)
        else:
            self._draw_fallback_text(painter, "🐾")

    def _draw_robot(self, painter: QPainter):
        # Draw Pilot robot head
        box_rect = QRectF(-32, -30, 64, 58)
        grad = QLinearGradient(box_rect.topLeft(), box_rect.bottomLeft())
        grad.setColorAt(0.0, QColor("#1E293B"))
        grad.setColorAt(1.0, QColor("#0F172A"))
        painter.setBrush(QBrush(grad))
        painter.setPen(QPen(QColor("#38BDF8"), 2.0))
        painter.drawRoundedRect(box_rect, 14, 14)

        # Antenna
        painter.setPen(QPen(QColor("#0284C7"), 2.0))
        painter.drawLine(0, -30, 0, -42)
        orb_color = QColor("#EF4444") if self._preview_state == "listening" else QColor("#38BDF8")
        painter.setBrush(QBrush(orb_color))
        painter.drawEllipse(QRectF(-4, -48, 8, 8))

        # Eyes
        eye_color = QColor("#22C55E") if self._preview_state == "success" else QColor("#38BDF8")
        painter.setBrush(QBrush(eye_color))
        painter.setPen(Qt.NoPen)
        if self._preview_state == "processing":
            # Thinking spirals/bars
            painter.drawRoundedRect(QRectF(-20, -10, 14, 4), 2, 2)
            painter.drawRoundedRect(QRectF(6, -10, 14, 4), 2, 2)
        else:
            painter.drawEllipse(QRectF(-20, -14, 12, 12))
            painter.drawEllipse(QRectF(8, -14, 12, 12))

        # Smile / Mouth
        painter.setPen(QPen(QColor("#94A3B8"), 1.8))
        if self._preview_state == "success":
            painter.drawArc(QRectF(-12, 4, 24, 14), 0, -180 * 16)
        else:
            painter.drawLine(-8, 12, 8, 12)

    def _draw_edge_line(self, painter: QPainter):
        rect = QRectF(-6, -40, 12, 80)
        color = QColor("#EF4444") if self._preview_state == "listening" else QColor("#0284C7")
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(rect, 6, 6)

    def _draw_wave_bar(self, painter: QPainter):
        bar_count = 5
        bar_w = 6
        spacing = 5
        total_w = (bar_count * bar_w) + ((bar_count - 1) * spacing)
        start_x = -total_w / 2.0

        color = QColor("#EF4444") if self._preview_state == "listening" else QColor("#38BDF8")
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)

        for i in range(bar_count):
            h = 10 + 20 * abs(math.sin(self._tick * 0.15 + i * 0.8))
            bx = start_x + (i * (bar_w + spacing))
            by = -h / 2.0
            painter.drawRoundedRect(QRectF(bx, by, bar_w, h), 3, 3)

    def _draw_emoji(self, painter: QPainter):
        emoji_char = self._companion_data.get("emoji", "🌟")
        font = QFont("Segoe UI Emoji", 46)
        font.setStyleStrategy(QFont.PreferAntialias)
        painter.setFont(font)
        painter.setPen(QColor("#FFFFFF"))
        rect = QRectF(-50, -50, 100, 100)
        painter.drawText(rect, Qt.AlignCenter, emoji_char)

    def _draw_custom_image(self, painter: QPainter):
        comp_dir = self._companion_data.get("directory")
        img_name = self._companion_data.get("image_file", "sprite.png")
        if comp_dir:
            img_path = Path(comp_dir) / img_name
            if img_path.exists():
                pix = QPixmap(str(img_path))
                if not pix.isNull():
                    scaled = pix.scaled(84, 84, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    painter.drawPixmap(int(-scaled.width() / 2), int(-scaled.height() / 2), scaled)
                    return
        self._draw_fallback_text(painter, "🖼️")

    def _draw_fallback_text(self, painter: QPainter, text: str):
        font = QFont("Segoe UI", 16, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QColor("#94A3B8"))
        painter.drawText(QRectF(-60, -20, 120, 40), Qt.AlignCenter, text)

    def _draw_state_badge(self, painter: QPainter):
        # Draw state indicator pill in bottom-right corner
        st = self._preview_state
        color_map = {
            "idle": ("#475569", "IDLE"),
            "listening": ("#DC2626", "REC"),
            "processing": ("#D97706", "STT"),
            "success": ("#16A34A", "PASTED"),
            "error": ("#E11D48", "ERROR")
        }
        color_hex, label = color_map.get(st, ("#475569", st.upper()))

        badge_rect = QRectF(self.width() - 56, self.height() - 22, 50, 18)
        painter.setBrush(QBrush(QColor(color_hex)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(badge_rect, 9, 9)

        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI", 7, QFont.Bold)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignCenter, label)

    def closeEvent(self, event):
        if hasattr(self, "_anim_timer") and self._anim_timer.isActive():
            self._anim_timer.stop()
        super().closeEvent(event)

