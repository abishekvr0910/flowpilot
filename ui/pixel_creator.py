"""
FlowPilot Interactive Pixel Art Companion Creator & Animation Studio
Allows users to:
- Draw custom pixel characters on a 16x16 grid with a retro color palette.
- Animate multiple frames (Frame 1: Idle, Frame 2: Action/Move, Frame 3: Celebrate).
- Onion skinning to trace previous frames effortlessly.
- Load pre-built expressive multi-frame animations (Kiki Courier, Oneko Cat, Shimeji Walker, Fox, Dino, Ghost, Bunny, Pup, Kitty).
- Preview animations in real-time with variable playback speed.
- Export to Animated GIF and Horizontal Spritesheet PNG.
- Import from existing Spritesheet PNG or Animated GIF.
- One-click save directly into FlowPilot's Companion Library and apply to desktop!
"""

import os
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QFrame, QButtonGroup, QMessageBox, QGridLayout,
    QCheckBox, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal, QRect
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QImage, QPixmap

try:
    from PIL import Image as PILImage, ImageSequence
except ImportError:
    PILImage = None
    ImageSequence = None

from engine.companion_assets import (
    build_default_frame_mappings, resolve_frame_for_state
)

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
MAX_IMPORT_FILE_SIZE = 5 * 1024 * 1024  # 5 MiB file size safety limit
MAX_IMPORT_DIMENSION = 2048            # 2048x2048 max resolution safety limit
MAX_SPRITE_FRAMES = 12                 # Maximum frames per animation pack


def _create_empty_grid() -> List[List[Optional[str]]]:
    return [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]


def _clone_grid(grid: List[List[Optional[str]]]) -> List[List[Optional[str]]]:
    return [row[:] for row in grid]


class PixelCanvasWidget(QWidget):
    pixel_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(288, 288)  # 16 cells * 18px = 288px
        self.cell_size = 18
        self._current_color: Optional[str] = "#FACC15"
        self._grid: List[List[Optional[str]]] = _create_empty_grid()
        self._onion_grid: Optional[List[List[Optional[str]]]] = None
        self._onion_enabled: bool = False
        self._is_drawing = False

    def set_color(self, hex_color: Optional[str]):
        self._current_color = hex_color

    def get_grid(self) -> List[List[Optional[str]]]:
        return _clone_grid(self._grid)

    def set_grid(self, grid: List[List[Optional[str]]]):
        self._grid = _clone_grid(grid)
        self.update()
        self.pixel_changed.emit()

    def set_onion_grid(self, grid: Optional[List[List[Optional[str]]]], enabled: bool = False):
        self._onion_grid = _clone_grid(grid) if grid else None
        self._onion_enabled = enabled
        self.update()

    def set_onion_enabled(self, enabled: bool):
        self._onion_enabled = enabled
        self.update()

    def clear(self):
        self._grid = _create_empty_grid()
        self.update()
        self.pixel_changed.emit()

    def flip_horizontal(self):
        self._grid = [row[::-1] for row in self._grid]
        self.update()
        self.pixel_changed.emit()

    def shift(self, dx: int, dy: int):
        new_grid = _create_empty_grid()
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                nr, nc = r + dy, c + dx
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                    new_grid[nr][nc] = self._grid[r][c]
        self._grid = new_grid
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

                # Onion skin underneath if cell is empty
                cell_val = self._grid[r][c]
                if cell_val is None and self._onion_enabled and self._onion_grid:
                    onion_val = self._onion_grid[r][c]
                    if onion_val:
                        o_col = QColor(onion_val)
                        o_col.setAlpha(80)
                        painter.fillRect(x, y, self.cell_size, self.cell_size, o_col)

                # Painted cell
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
            _create_empty_grid() for _ in range(3)
        ]
        self._current_frame_idx = 0
        self._tick = 0
        self._preview_state = "all"  # "all", "idle", "listening", "celebrate"
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)
        self._timer.start(250)  # 4 FPS default

    def set_fps(self, fps: int):
        interval = max(50, int(1000 / max(1, fps)))
        self._timer.setInterval(interval)

    def set_preview_state(self, state: str):
        self._preview_state = state
        self._tick = 0
        if self._preview_state != "all" and self._frames:
            self._current_frame_idx = resolve_frame_for_state(
                None, self._preview_state, tick=0, num_frames=len(self._frames)
            )
        self.update()

    def update_frame_data(self, frame_idx: int, grid: List[List[Optional[str]]]):
        if 0 <= frame_idx < len(self._frames):
            self._frames[frame_idx] = _clone_grid(grid)
            self.update()

    def set_all_frames(self, frames: List[List[List[Optional[str]]]]):
        self._frames = [_clone_grid(f) for f in frames]
        if self._preview_state != "all" and self._frames:
            self._current_frame_idx = resolve_frame_for_state(
                None, self._preview_state, tick=0, num_frames=len(self._frames)
            )
        self.update()

    def _next_frame(self):
        if not self._frames:
            return
        self._tick += 1
        n = len(self._frames)
        if self._preview_state == "all":
            self._current_frame_idx = (self._current_frame_idx + 1) % n
        else:
            self._current_frame_idx = resolve_frame_for_state(
                None, self._preview_state, tick=self._tick * 4, num_frames=n
            )
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(0, 0, self.width(), self.height(), QColor("#0B0F19"))

        if self._frames and 0 <= self._current_frame_idx < len(self._frames):
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
            _create_empty_grid() for _ in range(3)
        ]
        self._active_frame = 0
        self._init_ui()
        self._load_template("✉️ Kiki Courier")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Header with Template Picker
        top_bar = QHBoxLayout()
        lbl_title = QLabel("🎨 Pixel Art & Screen Animation Creator")
        lbl_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8;")
        top_bar.addWidget(lbl_title)
        top_bar.addStretch()

        top_bar.addWidget(QLabel("Template:"))
        self.combo_template = QComboBox()
        self.combo_template.addItems([
            "✉️ Kiki Courier",
            "🐈 Oneko Screen Cat",
            "⭐ Shimeji Desktop Walker",
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

        # Main Split
        split_box = QHBoxLayout()

        # Left Column: Canvas, Palette & Drawing Tools
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

        if self.color_group.button(0):
            self.color_group.button(0).setChecked(True)
        left_col.addLayout(palette_grid)

        # Frame Canvas Tools Row
        tools_row1 = QHBoxLayout()
        btn_copy = QPushButton("📋 Copy to Next")
        btn_copy.setToolTip("Copy current frame to the next frame")
        btn_copy.clicked.connect(self._copy_to_next_frame)
        tools_row1.addWidget(btn_copy)

        btn_flip = QPushButton("↔ Flip")
        btn_flip.setToolTip("Flip current frame horizontally")
        btn_flip.clicked.connect(self.canvas.flip_horizontal)
        tools_row1.addWidget(btn_flip)

        btn_clear = QPushButton("🗑 Clear")
        btn_clear.setToolTip("Clear current frame canvas")
        btn_clear.clicked.connect(self.canvas.clear)
        tools_row1.addWidget(btn_clear)
        left_col.addLayout(tools_row1)

        # Shift Tools & Onion Skinning Row
        tools_row2 = QHBoxLayout()
        self.chk_onion = QCheckBox("🧅 Onion Skin")
        self.chk_onion.setToolTip("Show faint outline of previous frame for smooth animation")
        self.chk_onion.stateChanged.connect(self._on_onion_toggle)
        tools_row2.addWidget(self.chk_onion)

        tools_row2.addStretch()
        lbl_shift = QLabel("Shift:")
        lbl_shift.setStyleSheet("color: #64748B; font-size: 11px;")
        tools_row2.addWidget(lbl_shift)

        for arrow, dx, dy in [("↑", 0, -1), ("↓", 0, 1), ("←", -1, 0), ("→", 1, 0)]:
            sbtn = QPushButton(arrow)
            sbtn.setFixedSize(24, 24)
            sbtn.clicked.connect(lambda _, x=dx, y=dy: self.canvas.shift(x, y))
            tools_row2.addWidget(sbtn)

        left_col.addLayout(tools_row2)
        split_box.addLayout(left_col)

        # Right Column: Animation Frames, Preview, Export & Save
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        lbl_frames = QLabel("Animation Frames:")
        lbl_frames.setStyleSheet("font-weight: bold; color: #94A3B8;")
        right_col.addWidget(lbl_frames)

        self.frame_btn_row = QHBoxLayout()
        right_col.addLayout(self.frame_btn_row)
        self._rebuild_frame_buttons()

        # Live Animation Preview
        lbl_prev = QLabel("Live Animation Loop:")
        lbl_prev.setStyleSheet("font-weight: bold; color: #94A3B8; margin-top: 4px;")
        right_col.addWidget(lbl_prev)

        prev_box = QHBoxLayout()
        self.anim_preview = PixelAnimationPreview(self)
        prev_box.addWidget(self.anim_preview, alignment=Qt.AlignCenter)
        right_col.addLayout(prev_box)

        # Speed Dropdown
        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed:"))
        self.combo_speed = QComboBox()
        self.combo_speed.addItems(["Slow (2 FPS)", "Normal (4 FPS)", "Fast (6 FPS)", "Expressive (8 FPS)"])
        self.combo_speed.setCurrentIndex(1)
        self.combo_speed.currentIndexChanged.connect(self._on_speed_changed)
        speed_row.addWidget(self.combo_speed)
        right_col.addLayout(speed_row)

        # Preview State Selector (Consistent with HUD Playback)
        prev_state_row = QHBoxLayout()
        prev_state_row.addWidget(QLabel("Preview State:"))
        self.combo_preview_state = QComboBox()
        self.combo_preview_state.addItems(["All Frames (Loop)", "Idle (Rest)", "Action (Listening)", "Celebrate (Delivered)"])
        self.combo_preview_state.currentIndexChanged.connect(self._on_preview_state_changed)
        prev_state_row.addWidget(self.combo_preview_state)
        right_col.addLayout(prev_state_row)

        # Import & Export Actions
        io_row = QHBoxLayout()
        btn_exp_gif = QPushButton("💾 Export GIF")
        btn_exp_gif.setToolTip("Export animation loop as an animated GIF")
        btn_exp_gif.clicked.connect(self._export_gif_dialog)
        io_row.addWidget(btn_exp_gif)

        btn_exp_sheet = QPushButton("🖼️ Export Sheet")
        btn_exp_sheet.setToolTip("Export all frames as a horizontal spritesheet PNG")
        btn_exp_sheet.clicked.connect(self._export_spritesheet_dialog)
        io_row.addWidget(btn_exp_sheet)

        btn_imp = QPushButton("📂 Import")
        btn_imp.setToolTip("Import frames from GIF or spritesheet PNG")
        btn_imp.clicked.connect(self._import_file_dialog)
        io_row.addWidget(btn_imp)
        right_col.addLayout(io_row)

        # Metadata & Save
        meta_row = QHBoxLayout()
        meta_row.addWidget(QLabel("Name:"))
        self.txt_name = QLineEdit("Kiki the Scarf Courier")
        meta_row.addWidget(self.txt_name)
        right_col.addLayout(meta_row)

        motion_row = QHBoxLayout()
        motion_row.addWidget(QLabel("Motion:"))
        self.combo_motion = QComboBox()
        self.combo_motion.addItems(["Gentle Bob", "Tiny Tilt", "Breathe", "Audio Pulse", "Celebration"])
        motion_row.addWidget(self.combo_motion)
        right_col.addLayout(motion_row)

        btn_save = QPushButton("✨ Save & Use as Active Desktop Companion")
        btn_save.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                font-weight: bold;
                font-size: 12px;
                padding: 8px;
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

    def _on_onion_toggle(self, state: int):
        prev_idx = (self._active_frame - 1) % len(self._frames)
        self.canvas.set_onion_grid(self._frames[prev_idx], enabled=self.chk_onion.isChecked())

    def _select_frame(self, frame_idx: int):
        self._frames[self._active_frame] = self.canvas.get_grid()
        self._active_frame = frame_idx
        self.canvas.set_grid(self._frames[self._active_frame])
        prev_idx = (self._active_frame - 1) % len(self._frames)
        self.canvas.set_onion_grid(self._frames[prev_idx], enabled=self.chk_onion.isChecked())

    def _copy_to_next_frame(self):
        curr = self.canvas.get_grid()
        next_idx = (self._active_frame + 1) % len(self._frames)
        self._frames[next_idx] = [row[:] for row in curr]
        self.anim_preview.update_frame_data(next_idx, curr)
        btn = self.frame_btn_group.button(next_idx)
        if btn:
            btn.setChecked(True)
        self._select_frame(next_idx)

    def _on_speed_changed(self, idx: int):
        fps = [2, 4, 6, 8][idx]
        self.anim_preview.set_fps(fps)

    def _on_preview_state_changed(self, idx: int):
        states = ["all", "idle", "listening", "celebrate"]
        st = states[idx] if 0 <= idx < len(states) else "all"
        self.anim_preview.set_preview_state(st)

    def _rebuild_frame_buttons(self):
        """Dynamically builds frame buttons based on explicit animation state mappings."""
        while self.frame_btn_row.count():
            item = self.frame_btn_row.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self.frame_btn_group = QButtonGroup(self)
        n = len(self._frames)
        mappings = build_default_frame_mappings(n)
        for idx in range(n):
            if idx in mappings.get("celebrate", []):
                name = f"{idx+1}: Celebrate"
            elif idx == 0:
                name = "1: Idle"
            elif idx in mappings.get("listening", []):
                listen_list = mappings.get("listening", [])
                if len(listen_list) > 1:
                    action_num = listen_list.index(idx) + 1
                    name = f"{idx+1}: Action {action_num}"
                else:
                    name = f"{idx+1}: Action"
            else:
                name = f"{idx+1}: Frame"

            fb = QPushButton(name)
            fb.setCheckable(True)
            if idx == self._active_frame:
                fb.setChecked(True)
            fb.clicked.connect(lambda _, fidx=idx: self._select_frame(fidx))
            self.frame_btn_group.addButton(fb, idx)
            self.frame_btn_row.addWidget(fb)

    # -----------------------------------------------------------------------
    # Template Generation (Lively Multi-Frame Animations)
    # -----------------------------------------------------------------------
    def _load_template(self, name: str):
        frames: List[List[List[Optional[str]]]] = [_create_empty_grid() for _ in range(3)]
        title = "Custom Pixel Companion"

        if "Kiki" in name or "Courier" in name:
            title = "Kiki the Scarf Courier"
            for f in range(3):
                g = frames[f]
                # Cap
                for c in range(5, 11):
                    g[1][c] = "#14B8A6"
                g[1][11] = "#FACC15"  # Badge
                # Hair
                for r in range(2, 5):
                    for c in range(4, 12):
                        g[r][c] = "#18181B"
                # Face
                for r in range(4, 7):
                    for c in range(5, 11):
                        g[r][c] = "#FDE68A"
                # Coat
                for r in range(8, 13):
                    for c in range(5, 10):
                        g[r][c] = "#6366F1"
                # Mailbag
                g[10][9] = "#B45309"; g[10][10] = "#B45309"
                g[11][9] = "#FDE68A"; g[11][10] = "#B45309"
                # Boots
                g[13][6] = "#18181B"; g[13][8] = "#18181B"

            # Frame 0: Idle
            frames[0][5][6] = "#18181B"; frames[0][5][9] = "#18181B"
            for c in range(4, 12):
                frames[0][7][c] = "#FB923C"
            frames[0][8][10] = "#FB923C"; frames[0][9][10] = "#FB923C"

            # Frame 1: Attentive listening / Scarf flutter
            frames[1][5][6] = "#38BDF8"; frames[1][5][9] = "#38BDF8"  # Attentive eyes
            for c in range(4, 11):
                frames[1][7][c] = "#FB923C"
            frames[1][7][11] = "#FB923C"; frames[1][7][12] = "#FB923C"  # Flying scarf
            frames[1][8][12] = "#FB923C"; frames[1][8][13] = "#FB923C"

            # Frame 2: Celebrate / Delivery
            frames[2][5][6] = "#18181B"; frames[2][5][7] = "#18181B"  # Happy closed crescents
            frames[2][5][9] = "#18181B"; frames[2][5][10] = "#18181B"
            for c in range(4, 12):
                frames[2][7][c] = "#FB923C"
            # Holding white letter high
            for r in range(4, 7):
                for c in range(11, 14):
                    frames[2][r][c] = "#FFFFFF"
            frames[2][5][12] = "#EF4444"  # Red heart seal
            frames[2][13][6] = None; frames[2][13][8] = None
            frames[2][12][6] = "#18181B"; frames[2][12][8] = "#18181B"  # Hop up

        elif "Oneko" in name or "Neko" in name:
            title = "Oneko Screen Cat"
            for f in range(3):
                g = frames[f]
                # Calico ears
                g[2][4] = "#FB923C"; g[2][11] = "#FB923C"
                g[3][5] = "#F472B6"; g[3][10] = "#F472B6"
                # Head
                for r in range(3, 8):
                    for c in range(5, 11):
                        g[r][c] = "#FFFFFF"
                # Eyes
                g[5][6] = "#22C55E"; g[5][9] = "#22C55E"
                # Nose
                g[6][7] = "#F472B6"; g[6][8] = "#F472B6"
                # Body
                for r in range(8, 13):
                    for c in range(5, 11):
                        g[r][c] = "#FFFFFF"
                g[9][6] = "#FB923C"; g[10][7] = "#FB923C"  # Calico patch

            # Frame 0: Sitting Alert
            frames[0][13][5] = "#FFFFFF"; frames[0][13][9] = "#FFFFFF"
            frames[0][10][12] = "#FB923C"; frames[0][11][12] = "#FB923C"; frames[0][12][12] = "#FB923C"

            # Frame 1: Prowl / Step
            frames[1][13][4] = "#FFFFFF"; frames[1][12][9] = "#FFFFFF"
            frames[1][8][13] = "#FB923C"; frames[1][9][12] = "#FB923C"  # High tail

            # Frame 2: Purr / Heart Cheer
            frames[2][5][6] = "#18181B"; frames[2][5][9] = "#18181B"
            frames[2][10][4] = "#F472B6"; frames[2][10][11] = "#F472B6"  # Raised pink paws
            frames[2][2][12] = "#F472B6"; frames[2][2][13] = "#F472B6"  # Floating heart
            frames[2][3][12] = "#F472B6"

        elif "Shimeji" in name or "Walker" in name:
            title = "Shimeji Desktop Walker"
            for f in range(3):
                g = frames[f]
                # Teal hair
                for r in range(2, 5):
                    for c in range(4, 12):
                        g[r][c] = "#14B8A6"
                # Skin
                for r in range(4, 7):
                    for c in range(5, 11):
                        g[r][c] = "#FDE68A"
                # Eyes
                g[5][5] = "#38BDF8"; g[5][9] = "#38BDF8"
                # Smile
                g[7][7] = "#EF4444"
                # Blue coat
                for r in range(8, 13):
                    for c in range(5, 11):
                        g[r][c] = "#6366F1"
                g[8][7] = "#FFFFFF"; g[9][7] = "#FFFFFF"  # White collar/tie

            # Frame 0: Idle
            frames[0][13][6] = "#18181B"; frames[0][13][9] = "#18181B"

            # Frame 1: Walk Step
            frames[1][12][4] = "#18181B"; frames[1][13][9] = "#18181B"
            frames[1][9][4] = "#FDE68A"  # Reaching hand

            # Frame 2: Cheer
            frames[2][5][3] = "#FDE68A"; frames[2][5][12] = "#FDE68A"  # Hands raised high!
            frames[2][6][4] = "#6366F1"; frames[2][6][11] = "#6366F1"
            frames[2][12][6] = "#18181B"; frames[2][12][9] = "#18181B"  # Hop

        elif "Fox" in name:
            title = "Pixel Fox"
            for f in range(3):
                g = frames[f]
                # Ears
                g[1][3] = "#18181B"; g[1][12] = "#18181B"
                g[2][4] = "#FB923C"; g[2][11] = "#FB923C"
                g[3][4] = "#FB923C"; g[3][11] = "#FB923C"
                # Head
                for r in range(4, 9):
                    for c in range(4, 12):
                        g[r][c] = "#FB923C"
                g[6][5] = "#18181B"; g[6][10] = "#18181B"  # Eyes
                g[7][4] = "#FFFFFF"; g[7][11] = "#FFFFFF"  # Cheeks
                g[7][7] = "#18181B"; g[7][8] = "#18181B"    # Nose
                for r in range(9, 14):
                    for c in range(5, 11):
                        g[r][c] = "#FB923C"

            # Frame 0: Idle
            frames[0][9][12] = "#FB923C"; frames[0][8][13] = "#FB923C"; frames[0][7][13] = "#FFFFFF"
            frames[0][14][5] = "#18181B"; frames[0][14][10] = "#18181B"

            # Frame 1: Wag
            frames[1][6][12] = "#FB923C"; frames[1][5][13] = "#FFFFFF"
            frames[1][14][5] = "#18181B"; frames[1][14][10] = "#18181B"

            # Frame 2: Joy Wink & Hop
            frames[2][6][5] = "#FB923C"
            frames[2][6][4] = "#18181B"; frames[2][5][5] = "#18181B"  # Wink ^
            frames[2][13][5] = "#18181B"; frames[2][13][10] = "#18181B"

        elif "Dino" in name:
            title = "Pixel Dino"
            for f in range(3):
                g = frames[f]
                for r in range(4, 9):
                    for c in range(5, 11):
                        g[r][c] = "#22C55E"
                g[5][6] = "#18181B"; g[5][9] = "#18181B"
                for r in range(9, 14):
                    for c in range(5, 11):
                        g[r][c] = "#22C55E"
                for r in range(10, 13):
                    g[r][7] = "#84CC16"; g[r][8] = "#84CC16"

            # Frame 0: Idle
            frames[0][11][12] = "#22C55E"; frames[0][10][13] = "#22C55E"; frames[0][9][13] = "#84CC16"
            frames[0][14][5] = "#22C55E"; frames[0][14][10] = "#22C55E"

            # Frame 1: Step
            frames[1][12][12] = "#22C55E"; frames[1][11][13] = "#84CC16"
            frames[1][13][5] = "#22C55E"; frames[1][14][10] = "#22C55E"

            # Frame 2: Roar / Celebrate
            frames[2][8][4] = "#84CC16"; frames[2][8][11] = "#84CC16"  # Arms up!
            frames[2][7][8] = "#FFFFFF"  # Tooth smile!
            frames[2][13][5] = "#22C55E"; frames[2][13][10] = "#22C55E"

        elif "Ghost" in name:
            title = "Pixel Ghost"
            for f in range(3):
                g = frames[f]
                g[2][4] = "#A855F7"; g[2][11] = "#A855F7"
                for r in range(4, 13):
                    for c in range(3, 13):
                        g[r][c] = "#6366F1"
                g[6][5] = "#FACC15"; g[6][10] = "#FACC15"
                for c in range(6, 10):
                    g[9][c] = "#FFFFFF"

            frames[0][13][4] = "#6366F1"; frames[0][13][11] = "#6366F1"
            # Frame 1: Hover up
            frames[1] = _clone_grid(frames[0])
            frames[1] = [[frames[0][min(15, r+1)][c] for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]
            # Frame 2: Boo sparkle
            frames[2][8][7] = "#FFFFFF"; frames[2][8][8] = "#FFFFFF"  # Big round mouth
            frames[2][3][2] = "#FACC15"; frames[2][3][13] = "#FACC15"  # Sparkles!

        elif "Bunny" in name:
            title = "Pixel Bunny"
            for f in range(3):
                g = frames[f]
                g[1][3] = "#B45309"; g[1][12] = "#B45309"
                g[2][3] = "#F472B6"; g[2][12] = "#F472B6"
                g[3][3] = "#F472B6"; g[3][12] = "#F472B6"
                for r in range(4, 8):
                    for c in range(5, 11):
                        g[r][c] = "#B45309"
                g[5][6] = "#18181B"; g[5][9] = "#18181B"
                for r in range(8, 10):
                    for c in range(4, 12):
                        g[r][c] = "#FDE68A"
                for r in range(10, 14):
                    for c in range(5, 11):
                        g[r][c] = "#B45309"

            # Frame 1: Ear twitch
            frames[1][2][2] = "#F472B6"; frames[1][3][2] = "#F472B6"
            # Frame 2: Hop
            frames[2][9][4] = "#FDE68A"; frames[2][9][11] = "#FDE68A"

        elif "Pup" in name:
            title = "Shiba Pixel Pup"
            for f in range(3):
                g = frames[f]
                g[3][3] = "#B45309"; g[3][12] = "#B45309"
                g[4][4] = "#B45309"; g[4][11] = "#B45309"
                for r in range(5, 9):
                    for c in range(4, 12):
                        g[r][c] = "#FB923C"
                g[6][5] = "#18181B"; g[6][10] = "#18181B"
                g[7][7] = "#18181B"; g[7][8] = "#FFFFFF"
                for r in range(9, 14):
                    for c in range(5, 11):
                        g[r][c] = "#FB923C"

            frames[0][10][12] = "#FB923C"
            frames[0][14][5] = "#FFFFFF"; frames[0][14][10] = "#FFFFFF"

            # Frame 1: Tail wag left & tongue
            frames[1][10][3] = "#FB923C"
            frames[1][8][7] = "#F472B6"  # Tongue
            frames[1][14][5] = "#FFFFFF"; frames[1][14][10] = "#FFFFFF"

            # Frame 2: Paws raised
            frames[2][11][4] = "#FFFFFF"; frames[2][11][11] = "#FFFFFF"

        elif "Kitty" in name:
            title = "Pixel Kitty"
            for f in range(3):
                g = frames[f]
                g[2][4] = "#18181B"; g[2][11] = "#18181B"
                for r in range(3, 8):
                    for c in range(4, 12):
                        g[r][c] = "#334155"
                g[5][5] = "#FACC15"; g[5][10] = "#FACC15"
                for r in range(8, 13):
                    for c in range(5, 11):
                        g[r][c] = "#334155"

            frames[0][13][5] = "#FFFFFF"; frames[0][13][10] = "#FFFFFF"
            frames[1][12][5] = "#FFFFFF"; frames[1][13][10] = "#FFFFFF"  # Knead
            frames[2][3][12] = "#F472B6"; frames[2][3][13] = "#F472B6"  # Hearts!

        # Blank Grid falls through to empty frames
        self.txt_name.setText(title)
        self._frames = frames
        self._active_frame = 0
        self._rebuild_frame_buttons()
        self.anim_preview.set_all_frames(self._frames)
        self.canvas.set_grid(self._frames[self._active_frame])
        prev_idx = (self._active_frame - 1) % len(self._frames)
        self.canvas.set_onion_grid(self._frames[prev_idx], enabled=self.chk_onion.isChecked())

    # -----------------------------------------------------------------------
    # Export & Import Capabilities (GIF / Spritesheet)
    # -----------------------------------------------------------------------
    def export_spritesheet(self, filepath: Path) -> bool:
        """Exports all frames side-by-side into a crisp 3x-scaled PNG spritesheet."""
        filepath = Path(filepath)
        n = len(self._frames)
        w, h = n * GRID_SIZE * 3, GRID_SIZE * 3
        img = QImage(w, h, QImage.Format_ARGB32)
        img.fill(0)
        painter = QPainter(img)

        for f_idx, grid in enumerate(self._frames):
            ox = f_idx * GRID_SIZE * 3
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    col = grid[r][c]
                    if col:
                        painter.fillRect(ox + c * 3, r * 3, 3, 3, QColor(col))
        painter.end()
        return img.save(str(filepath), "PNG")

    def export_gif(self, filepath: Path, fps: int = 4) -> bool:
        """Exports all frames into an animated GIF using PIL."""
        if not PILImage:
            return False
        filepath = Path(filepath)
        pil_frames = []
        for grid in self._frames:
            img = PILImage.new("RGBA", (GRID_SIZE * 3, GRID_SIZE * 3), (0, 0, 0, 0))
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    col = grid[r][c]
                    if col:
                        # Parse hex
                        qcol = QColor(col)
                        for dr in range(3):
                            for dc in range(3):
                                img.putpixel((c * 3 + dc, r * 3 + dr), (qcol.red(), qcol.green(), qcol.blue(), 255))
            pil_frames.append(img)

        duration = max(50, int(1000 / max(1, fps)))
        pil_frames[0].save(
            filepath,
            save_all=True,
            append_images=pil_frames[1:],
            duration=duration,
            loop=0,
            disposal=2
        )
        return filepath.exists()

    def import_file(self, filepath: Path) -> bool:
        """Imports frames from an animated GIF or horizontal spritesheet PNG with bounded safety checks."""
        if not PILImage:
            return False
        filepath = Path(filepath)
        if not filepath.exists():
            return False

        # 1. Enforce file size safety limit BEFORE decoding
        try:
            fsize = filepath.stat().st_size
            if fsize > MAX_IMPORT_FILE_SIZE or fsize == 0:
                print(f"[PixelCreator] File size {fsize} bytes exceeds limit ({MAX_IMPORT_FILE_SIZE} bytes).")
                return False
        except Exception:
            return False

        try:
            with PILImage.open(filepath) as img:
                # 2. Enforce dimension limits to prevent decompression bombs
                w, h = img.size
                if w > MAX_IMPORT_DIMENSION or h > MAX_IMPORT_DIMENSION or w == 0 or h == 0:
                    print(f"[PixelCreator] Image dimension {w}x{h} exceeds safe limit ({MAX_IMPORT_DIMENSION}).")
                    return False

                loaded_grids: List[List[List[Optional[str]]]] = []

                # Animated GIF
                if getattr(img, "is_animated", False):
                    for frame in ImageSequence.Iterator(img):
                        f_rgba = frame.convert("RGBA").resize((GRID_SIZE, GRID_SIZE), PILImage.Resampling.NEAREST)
                        grid = _create_empty_grid()
                        for r in range(GRID_SIZE):
                            for c in range(GRID_SIZE):
                                p = f_rgba.getpixel((c, r))
                                if p[3] >= 50:
                                    grid[r][c] = "#{:02X}{:02X}{:02X}".format(p[0], p[1], p[2])
                        loaded_grids.append(grid)
                        if len(loaded_grids) >= MAX_SPRITE_FRAMES:
                            break
                else:
                    # Spritesheet (horizontal strip: width is multiple of height)
                    n_frames = max(1, min(MAX_SPRITE_FRAMES, w // max(1, h)))
                    for i in range(n_frames):
                        crop = img.crop((i * h, 0, (i + 1) * h, h)).convert("RGBA").resize((GRID_SIZE, GRID_SIZE), PILImage.Resampling.NEAREST)
                        grid = _create_empty_grid()
                        for r in range(GRID_SIZE):
                            for c in range(GRID_SIZE):
                                p = crop.getpixel((c, r))
                                if p[3] >= 50:
                                    grid[r][c] = "#{:02X}{:02X}{:02X}".format(p[0], p[1], p[2])
                        loaded_grids.append(grid)

                if not loaded_grids:
                    return False

                # Ensure at least 3 frames for full Idle / Move / Celebrate lifecycle
                while len(loaded_grids) < 3:
                    loaded_grids.append(_clone_grid(loaded_grids[-1]))

                self._frames = loaded_grids[:MAX_SPRITE_FRAMES]
                self._active_frame = 0
                self._rebuild_frame_buttons()
                self.anim_preview.set_all_frames(self._frames)
                self.canvas.set_grid(self._frames[self._active_frame])
                prev_idx = (self._active_frame - 1) % len(self._frames)
                self.canvas.set_onion_grid(self._frames[prev_idx], enabled=self.chk_onion.isChecked())
                return True
        except Exception as e:
            print(f"[PixelCreator] Import failed: {e}")
            return False

    def _export_gif_dialog(self):
        fps_opts = [2, 4, 6, 8]
        fps = fps_opts[self.combo_speed.currentIndex()]
        fn, _ = QFileDialog.getSaveFileName(self, "Export Animated GIF", "companion_animation.gif", "GIF Files (*.gif)")
        if fn:
            ok = self.export_gif(Path(fn), fps=fps)
            if ok:
                QMessageBox.information(self, "Export Successful", f"Animated GIF saved:\n{fn}")
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to export animated GIF.")

    def _export_spritesheet_dialog(self):
        fn, _ = QFileDialog.getSaveFileName(self, "Export Spritesheet", "companion_spritesheet.png", "PNG Files (*.png)")
        if fn:
            ok = self.export_spritesheet(Path(fn))
            if ok:
                QMessageBox.information(self, "Export Successful", f"Spritesheet saved:\n{fn}")
            else:
                QMessageBox.warning(self, "Export Failed", "Failed to export spritesheet.")

    def _import_file_dialog(self):
        fn, _ = QFileDialog.getOpenFileName(self, "Import Animation / Spritesheet", "", "Image Files (*.gif *.png *.webp)")
        if fn:
            ok = self.import_file(Path(fn))
            if ok:
                QMessageBox.information(self, "Import Successful", f"Loaded frames from:\n{fn}")
            else:
                QMessageBox.warning(self, "Import Failed", "Failed to parse animation frames from file.")

    # -----------------------------------------------------------------------
    # Library Persistence & Activation
    # -----------------------------------------------------------------------
    def _save_companion(self):
        name = self.txt_name.text().strip() or "Custom Pixel Companion"
        comp_id = f"custom_pixel_{uuid.uuid4().hex[:8]}"

        from engine.companion_store import get_companion_store
        store = get_companion_store()
        storage_dir = store.storage_dir / "companions" / comp_id
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
        mappings = build_default_frame_mappings(len(self._frames))
        manifest = {
            "schema_version": 1,
            "id": comp_id,
            "type": "spritesheet",
            "name": name,
            "image_file": frame_files[0],
            "frames": frame_files,
            "frame_mappings": mappings,
            "motion_preset": motion,
            "created_at": 0
        }

        with open(storage_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

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
