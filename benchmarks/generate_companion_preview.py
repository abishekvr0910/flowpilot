"""Render review sheets and a motion GIF through FlowPilot's production renderer.

No duplicate sprite definitions or independent animation implementation. These
are deterministic visual fixtures, not measurements of real microphone input.
"""
import io
import math
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtCore import QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QImage, QPainter
from PySide6.QtWidgets import QApplication
from PIL import Image
from ui.companion_renderer import CompanionRenderer

OUTPUT_DIR = PROJECT_ROOT / "docs/design/companion_preview"
STATES = ("idle", "listening", "processing", "confirmed", "unverified", "recovery")


def render_frame(state, elapsed_ms=500, level=0.6, palette="autumn", bg="#0F172A", dpr=1.0):
    image = QImage(round(96 * dpr), round(96 * dpr), QImage.Format_ARGB32)
    image.setDevicePixelRatio(dpr)
    image.fill(QColor(bg))
    painter = QPainter(image)
    try:
        CompanionRenderer.render(painter, QRectF(0, 0, 96, 96), "kiki", state,
            elapsed_ms=elapsed_ms, audio_level=level, palette=palette,
            device_pixel_ratio=dpr, state_elapsed_ms=elapsed_ms)
    finally:
        painter.end()
    return image


def generate_contact_sheet(bg, output_path):
    dark = QColor(bg).lightnessF() < 0.5
    canvas = QImage(780, 450, QImage.Format_ARGB32)
    canvas.fill(QColor(bg))
    painter = QPainter(canvas)
    try:
        painter.setPen(QColor("#E2E8F0" if dark else "#0F172A"))
        painter.setFont(QFont("Segoe UI", 11))
        painter.drawText(QRectF(16, 10, 748, 40), Qt.AlignCenter,
                         "Kiki prototype — production renderer, native logical size")
        for row, (palette, dpr) in enumerate((("autumn", 1.0), ("frost", 1.25), ("matcha", 2.0))):
            top = 62 + row * 124
            painter.setFont(QFont("Segoe UI", 8))
            painter.drawText(16, top, f"{palette.title()} · {int(dpr * 100)}% display scale")
            for col, state in enumerate(STATES):
                x = 18 + col * 128
                frame = render_frame(state, palette=palette, bg=bg, dpr=dpr)
                painter.drawImage(QRectF(x + 10, top + 4, 96, 96), frame)
                painter.drawText(QRectF(x, top + 98, 120, 20), Qt.AlignCenter, state)
    finally:
        painter.end()
    if not canvas.save(str(output_path), "PNG"):
        raise OSError(f"Unable to write preview: {output_path}")


def generate_animated_preview_gif(output_path):
    frames = []
    for state, duration in (("idle", 3500), ("listening", 2000), ("processing", 1500),
                            ("confirmed", 2000), ("unverified", 1500), ("recovery", 1500)):
        for elapsed in range(0, duration, 100):
            frame = render_frame(state, elapsed, level=(math.sin(elapsed / 180) + 1) / 2)
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            frame.save(buffer, "PNG")
            with Image.open(io.BytesIO(bytes(buffer.data()))) as image:
                frames.append(image.convert("RGB"))
            buffer.close()
    frames[0].save(str(output_path), save_all=True, append_images=frames[1:], duration=100, loop=0)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    # Qt's offscreen backend may not enumerate Windows system fonts.
    if not QFontDatabase.families():
        font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/segoeui.ttf"
        if QFontDatabase.addApplicationFont(str(font_path)) < 0:
            raise RuntimeError("No readable local font; refusing to export unreadable labels.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    generate_contact_sheet("#0F172A", OUTPUT_DIR / "kiki_contact_sheet_dark.png")
    generate_contact_sheet("#F8FAFC", OUTPUT_DIR / "kiki_contact_sheet_light.png")
    generate_animated_preview_gif(OUTPUT_DIR / "kiki_motion_preview.gif")
    print("Production-renderer preview sheets and simulated-audio GIF generated.")
