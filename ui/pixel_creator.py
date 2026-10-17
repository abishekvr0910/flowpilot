"""
FlowPilot Interactive Pixel Art Companion Creator & Animation Studio
Allows users to:
- Draw custom pixel characters on a 16x16 grid with a retro color palette.
- Animate multiple frames (Frame 1: Idle, Frame 2: Action/Move, Frame 3: Celebrate).
- Load pre-built Retro Companion (Fox, Dino, Ghost, Bunny) and Pet (Pup, Kitty) templates.
- Preview animations in real-time.
- One-click save directly into FlowPilot's Companion Library and apply to desktop!
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QButtonGroup, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPixmap

PALETTE_COLORS = [
    ("#18181B", "Black"),
    ("#FFFFFF", "White"),
    ("#64748B", "Slate"),
    ("#EF4444", "Crimson"),
    ("#FB923C", "Orange"),
    ("#FACC15", "Yellow"),
    ("#84CC16", "Lime"),
    ("#22C55E", "Green"),
    ("#14B8A6", "Teal"),
    ("#38BDF8", "Sky Blue"),
    ("#6366F1", "Indigo"),
    ("#A855F7", "Purple"),
    ("#F472B6", "Pink"),
    ("#B45309", "Brown"),
    ("#FDE68A", "Cream"),
    (None, "Eraser")
]

GRID_SIZE = 16

class PixelCanvasWidget(QWidget):
    pixel_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(288, 288)  # 16 cells * 18px = 288px
        self.cell_size = 18
        self._current_color: Optional[str] = "#FACC15"
        self._grid: List[List[Optional[str]]] = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self._is_drawing = False

    def set_color(self, hex_color: Optional[str]):
        self._current_color = hex_color

    def get_grid(self) -> List[List[Optional[str]]]:
        return [row[:] for row in self._grid]

    def set_grid(self, grid: List[List[Optional[str]]]):
        self._grid = [row[:] for row in grid]
        self.update()
        self.pixel_changed.emit()

    def clear(self):
        self._grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.update()
        self.pixel_changed.emit()

    def flip_horizontal(self):
        self._grid = [row[::-1] for row in self._grid]
        self.update()
        self.pixel_changed.emit()

    def mousePressEvent(self, event):
        if event.button() in (Qt.LeftButton, Qt.RightButton):
            self._is_drawing = True
            self._paint_at_pos(event.position().x(), event.position().y(), is_right=(event.button() == Qt.RightButton))

    def mouseMoveEvent(self, event):
        if self._is_drawing:
            is_right = bool(event.buttons() & Qt.RightButton)
            self._paint_at_pos(event.position().x(), event.position().y(), is_right=is_right)

    def mouseReleaseEvent(self, event):
        self._is_drawing = False

    def _paint_at_pos(self, x: float, y: float, is_right: bool = False):
        gx = int(x // self.cell_size)
        gy = int(y // self.cell_size)
        if 0 <= gx < GRID_SIZE and 0 <= gy < GRID_SIZE:
            col = None if is_right else self._current_color
            if self._grid[gy][gx] != col:
                self._grid[gy][gx] = col
                self.update()
                self.pixel_changed.emit()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Background checkerboard for transparent areas
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                x = c * self.cell_size
                y = r * self.cell_size
                bg = "#0F172A" if (r + c) % 2 == 0 else "#1E293B"
                painter.fillRect(x, y, self.cell_size, self.cell_size, QColor(bg))

                # Painted cell
                cell_val = self._grid[r][c]
                if cell_val:
                    painter.fillRect(x, y, self.cell_size, self.cell_size, QColor(cell_val))

        # Thin grid overlay
        painter.setPen(QPen(QColor("#334155"), 1))
        for i in range(GRID_SIZE + 1):
            p = i * self.cell_size
            painter.drawLine(p, 0, p, self.height())
            painter.drawLine(0, p, self.width(), p)

        painter.end()


class PixelAnimationPreview(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(96, 96)
        self._frames: List[List[List[Optional[str]]]] = [
            [[None]*GRID_SIZE for _ in range(GRID_SIZE)] for _ in range(3)
        ]
        self._current_frame_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)
        self._timer.start(250)  # 4 FPS default

    def set_fps(self, fps: int):
        interval = max(50, int(1000 / max(1, fps)))
        self._timer.setInterval(interval)

    def update_frame_data(self, frame_idx: int, grid: List[List[Optional[str]]]):
        if 0 <= frame_idx < len(self._frames):
            self._frames[frame_idx] = [row[:] for row in grid]
            self.update()

    def _next_frame(self):
        self._current_frame_idx = (self._current_frame_idx + 1) % len(self._frames)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor("#0B0F19"))

        grid = self._frames[self._current_frame_idx]
        px_scale = self.width() // GRID_SIZE
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                col = grid[r][c]
                if col:
                    painter.fillRect(c * px_scale, r * px_scale, px_scale, px_scale, QColor(col))

        painter.setPen(QPen(QColor("#38BDF8"), 1))
        painter.drawRect(0, 0, self.width() - 1, self.height() - 1)
        painter.end()

    def closeEvent(self, event):
        if hasattr(self, '_timer') and self._timer:
            self._timer.stop()
        super().closeEvent(event)

    def hideEvent(self, event):
        if hasattr(self, '_timer') and self._timer:
            self._timer.stop()
        super().hideEvent(event)


class PixelCreatorWidget(QWidget):
    companion_created = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frames: List[List[List[Optional[str]]]] = [
            [[None]*GRID_SIZE for _ in range(GRID_SIZE)] for _ in range(3)
        ]
        self._active_frame = 0
        self._init_ui()
        self._load_template("🦊 Pixel Fox")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Header with Template Picker
        top_bar = QHBoxLayout()
        lbl_title = QLabel("🎨 Pixel Art & Companion Creator")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        top_bar.addWidget(lbl_title)
        top_bar.addStretch()

        top_bar.addWidget(QLabel("Load Template:"))
        self.combo_template = QComboBox()
        self.combo_template.addItems([
            "🦊 Pixel Fox",
            "🦖 Pixel Dino",
            "👻 Pixel Ghost",
            "🐰 Pixel Bunny",
            "🐶 Pixel Pup",
            "🐾 Kitty",
            "✨ Blank Grid"
        ])
        top_bar.addWidget(self.combo_template)

        btn_load = QPushButton("Load")
        btn_load.clicked.connect(lambda: self._load_template(self.combo_template.currentText()))
        top_bar.addWidget(btn_load)
        layout.addLayout(top_bar)

        # Main Editor Split
        split_box = QHBoxLayout()

        # Left Column: Canvas and Palette
        left_col = QVBoxLayout()
        self.canvas = PixelCanvasWidget(self)
        self.canvas.pixel_changed.connect(self._on_pixel_changed)
        left_col.addWidget(self.canvas, alignment=Qt.AlignCenter)

        # Color Palette Grid
        palette_grid = QGridLayout()
        palette_grid.setSpacing(4)
        self.color_group = QButtonGroup(self)

        for i, (hex_code, name) in enumerate(PALETTE_COLORS):
            btn = QPushButton()
            btn.setFixedSize(26, 26)
            btn.setToolTip(name)
            btn.setCheckable(True)
            if hex_code:
                btn.setStyleSheet(f"background-color: {hex_code}; border: 1px solid #475569; border-radius: 4px;")
            else:
                btn.setText("✕")
                btn.setStyleSheet("background-color: #334155; color: #EF4444; font-weight: bold; border-radius: 4px;")

            btn.clicked.connect(lambda _, h=hex_code: self.canvas.set_color(h))
            self.color_group.addButton(btn, i)
            palette_grid.addWidget(btn, i // 8, i % 8)

        # Select first color by default
        if self.color_group.button(0):
            self.color_group.button(0).setChecked(True)

        left_col.addLayout(palette_grid)

        # Frame Canvas Tools
        tools_row = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy to Next Frame")
        btn_copy.clicked.connect(self._copy_to_next_frame)
        tools_row.addWidget(btn_copy)

        btn_flip = QPushButton("↔ Flip")
        btn_flip.clicked.connect(self.canvas.flip_horizontal)
        tools_row.addWidget(btn_flip)

        btn_clear = QPushButton("🗑 Clear")
        btn_clear.clicked.connect(self.canvas.clear)
        tools_row.addWidget(btn_clear)
        left_col.addLayout(tools_row)

        split_box.addLayout(left_col)

        # Right Column: Animation Frames & Live Preview
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        lbl_frames = QLabel("Animation Frames:")
        lbl_frames.setStyleSheet("font-weight: bold; color: #94A3B8;")
        right_col.addWidget(lbl_frames)

        frame_btn_row = QHBoxLayout()
        self.frame_btn_group = QButtonGroup(self)
        frame_names = ["1: Idle", "2: Action / Move", "3: Celebrate"]
        for idx, fname in enumerate(frame_names):
            fb = QPushButton(fname)
            fb.setCheckable(True)
            if idx == 0:
                fb.setChecked(True)
            fb.clicked.connect(lambda _, fidx=idx: self._select_frame(fidx))
            self.frame_btn_group.addButton(fb, idx)
            frame_btn_row.addWidget(fb)
        right_col.addLayout(frame_btn_row)

        # Live Animation Preview
        lbl_prev = QLabel("Live Animation Loop:")
        lbl_prev.setStyleSheet("font-weight: bold; color: #94A3B8; margin-top: 6px;")
        right_col.addWidget(lbl_prev)

        prev_box = QHBoxLayout()
        self.anim_preview = PixelAnimationPreview(self)
        prev_box.addWidget(self.anim_preview, alignment=Qt.AlignCenter)
        right_col.addLayout(prev_box)

        # Speed Dropdown
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["Slow (2 FPS)", "Normal (4 FPS)", "Fast (6 FPS)"])
        self.combo_speed.setCurrentIndex(1)
        self.combo_speed.currentIndexChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self.combo_speed)
        right_col.addLayout(speed_row)

        # Metadata & Save
        meta_row = QHBoxLayout()
        meta_row.addWidget(QLabel("Name:"))
        self.txt_name = QLineEdit("My Custom Companion")
        meta_row.addWidget(self.txt_name)
        right_col.addLayout(meta_row)

        motion_row = QHBoxLayout()
        motion_row.addWidget(QLabel("Motion:"))
        self.combo_motion = QComboBox()
        self.combo_motion.addItems(["Gentle Bob", "Tiny Tilt", "Breathe", "Audio Pulse", "Celebration"])
        motion_row.addWidget(self.combo_motion)
        right_col.addLayout(motion_row)

        btn_save = QPushButton("✨ Save & Use as Active Companion")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 13px;
                padding: 10px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
        """)
        btn_save.clicked.connect(self._save_companion)
        right_col.addWidget(btn_save)

        right_col.addStretch()
        split_box.addLayout(right_col)

        layout.addLayout(split_box)

    def _on_pixel_changed(self):
        curr = self.canvas.get_grid()
        self._frames[self._active_frame] = curr
        self.anim_preview.update_frame_data(self._active_frame, curr)

    def _select_frame(self, frame_idx: int):
        self._frames[self._active_frame] = self.canvas.get_grid()
        self._active_frame = frame_idx
        self.canvas.set_grid(self._frames[self._active_frame])

    def _copy_to_next_frame(self):
        curr = self.canvas.get_grid()
        next_idx = (self._active_frame + 1) % 3
        self._frames[next_idx] = [row[:] for row in curr]
        self.anim_preview.update_frame_data(next_idx, curr)
        # Switch to next frame button
        btn = self.frame_btn_group.button(next_idx)
        if btn:
            btn.setChecked(True)
        self._select_frame(next_idx)

    def _on_speed_changed(self, idx: int):
        fps = [2, 4, 6][idx]
        self.anim_preview.set_fps(fps)

    def _load_template(self, name: str):
        self.canvas.clear()
        grid = [[None]*GRID_SIZE for _ in range(GRID_SIZE)]

        if "Fox" in name or "Pikachu" in name:
            self.txt_name.setText("Pixel Fox")
            # Ears
            grid[1][3] = "#18181B"; grid[1][12] = "#18181B"
            grid[2][4] = "#FB923C"; grid[2][11] = "#FB923C"
            grid[3][4] = "#FB923C"; grid[3][11] = "#FB923C"
            # Head
            for r in range(4, 9):
                for c in range(4, 12):
                    grid[r][c] = "#FB923C"
            # Eyes & White Cheeks
            grid[6][5] = "#18181B"; grid[6][10] = "#18181B"
            grid[7][4] = "#FFFFFF"; grid[7][11] = "#FFFFFF"
            grid[7][7] = "#18181B"; grid[7][8] = "#18181B"  # nose
            # Body
            for r in range(9, 14):
                for c in range(5, 11):
                    grid[r][c] = "#FB923C"
            # Tail
            grid[9][12] = "#FB923C"; grid[8][13] = "#FB923C"; grid[7][13] = "#FFFFFF"
            # Feet
            grid[14][5] = "#18181B"; grid[14][10] = "#18181B"

        elif "Dino" in name or "Charmander" in name:
            self.txt_name.setText("Pixel Dino")
            for r in range(4, 9):
                for c in range(5, 11):
                    grid[r][c] = "#22C55E"
            # Cute eyes
            grid[5][6] = "#18181B"; grid[5][9] = "#18181B"
            # Body
            for r in range(9, 14):
                for c in range(5, 11):
                    grid[r][c] = "#22C55E"
            # Lime belly
            for r in range(10, 13):
                grid[r][7] = "#84CC16"; grid[r][8] = "#84CC16"
            # Tail
            grid[11][12] = "#22C55E"; grid[10][13] = "#22C55E"; grid[9][13] = "#84CC16"
            grid[14][5] = "#22C55E"; grid[14][10] = "#22C55E"

        elif "Ghost" in name or "Gengar" in name:
            self.txt_name.setText("Pixel Ghost")
            # Floating crown/spikes
            grid[2][4] = "#A855F7"; grid[2][11] = "#A855F7"
            for r in range(4, 13):
                for c in range(3, 13):
                    grid[r][c] = "#6366F1"
            # Glowing friendly eyes
            grid[6][5] = "#FACC15"; grid[6][10] = "#FACC15"
            # Cheerful mouth
            for c in range(6, 10):
                grid[9][c] = "#FFFFFF"
            grid[13][4] = "#6366F1"; grid[13][11] = "#6366F1"

        elif "Bunny" in name or "Eevee" in name:
            self.txt_name.setText("Pixel Bunny")
            # Long floppy ears
            grid[1][3] = "#B45309"; grid[1][12] = "#B45309"
            grid[2][3] = "#F472B6"; grid[2][12] = "#F472B6"
            grid[3][3] = "#F472B6"; grid[3][12] = "#F472B6"
            for r in range(4, 8):
                for c in range(5, 11):
                    grid[r][c] = "#B45309"
            grid[5][6] = "#18181B"; grid[5][9] = "#18181B"
            # Fluffy collar
            for r in range(8, 10):
                for c in range(4, 12):
                    grid[r][c] = "#FDE68A"
            for r in range(10, 14):
                for c in range(5, 11):
                    grid[r][c] = "#B45309"

        elif "Pixel Pup" in name:
            self.txt_name.setText("Shiba Pixel Pup")
            # Floppy ears
            grid[3][3] = "#B45309"; grid[3][12] = "#B45309"
            grid[4][4] = "#B45309"; grid[4][11] = "#B45309"
            for r in range(5, 9):
                for c in range(4, 12):
                    grid[r][c] = "#FB923C"
            # White muzzle & nose
            grid[6][5] = "#18181B"; grid[6][10] = "#18181B"
            grid[7][7] = "#FFFFFF"; grid[7][8] = "#FFFFFF"
            grid[7][7] = "#18181B"  # nose
            for r in range(9, 14):
                for c in range(5, 11):
                    grid[r][c] = "#FB923C"
            grid[10][12] = "#FB923C"  # wagging tail
            grid[14][5] = "#FFFFFF"; grid[14][10] = "#FFFFFF"

        # Populate all 3 frames from this base
        for f in range(3):
            self._frames[f] = [row[:] for row in grid]
            self.anim_preview.update_frame_data(f, grid)

        self.canvas.set_grid(grid)

    def _save_companion(self):
        name = self.txt_name.text().strip() or "Custom Pixel Companion"
        comp_id = f"custom_pixel_{uuid.uuid4().hex[:8]}"

        # Render 3 frames to 48x48 PNGs
        storage_dir = Path.home() / ".flowpilot" / "companions" / comp_id
        storage_dir.mkdir(parents=True, exist_ok=True)

        frame_files = []
        for idx, f_grid in enumerate(self._frames):
            img = QImage(GRID_SIZE * 3, GRID_SIZE * 3, QImage.Format_ARGB32)
            img.fill(0)
            painter = QPainter(img)
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    col = f_grid[r][c]
                    if col:
                        painter.fillRect(c * 3, r * 3, 3, 3, QColor(col))
            painter.end()
            fn = f"frame_{idx}.png"
            img.save(str(storage_dir / fn), "PNG")
            frame_files.append(fn)

        motion = self.combo_motion.currentText().lower().replace(" ", "_")
        manifest = {
            "schema_version": 1,
            "id": comp_id,
            "type": "spritesheet",
            "name": name,
            "image_file": frame_files[0],
            "frames": frame_files,
            "motion_preset": motion,
            "created_at": 0
        }

        with open(storage_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # Update companion store
        from engine.companion_store import get_companion_store
        store = get_companion_store()
        store.update({
            "selected_asset_id": comp_id,
            "motion_preset": motion
        })

        self.companion_created.emit(manifest)
        QMessageBox.information(
            self,
            "Companion Created!",
            f"'{name}' has been created and set as your active desktop companion!\nSaved to your library."
        )

    def closeEvent(self, event):
        if hasattr(self, 'anim_preview') and self.anim_preview:
            self.anim_preview.close()
        super().closeEvent(event)

    def hideEvent(self, event):
        if hasattr(self, 'anim_preview') and self.anim_preview:
            self.anim_preview.hide()
        super().hideEvent(event)

