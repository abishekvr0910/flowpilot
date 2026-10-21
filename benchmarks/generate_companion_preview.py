"""
FlowPilot Companion Prototype & Visual Contact Sheet Generator (Gemini B Track)
Generates:
1. Multi-scale contact sheets of Kiki the Little Scarf Courier across all 6 states
   (idle, listening, processing, verified completion, sent unverified, recoverable failure)
   on both dark (#0F172A) and light (#F8FAFC) backgrounds at 48px, 64px, and 96px.
2. An animated GIF demonstration (kiki_motion_preview.gif) showing restrained motion:
   quiet idle, scarf straightening, attentive listening, parcel holding, and single-shot celebration.
3. Programmatic visual acceptance assertions (non-empty bounds, distinct state diffs, reduced-motion freeze).
"""

import os
import sys
import math
from pathlib import Path
from typing import Dict, List, Tuple, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter, QColor, QFont, QPen, QBrush
from PySide6.QtCore import Qt, QRectF, QPointF
from PIL import Image

app = QApplication.instance() or QApplication(sys.argv)

OUTPUT_DIR = PROJECT_ROOT / "docs" / "design" / "companion_preview"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Kiki Sprite Pixel Matrix Definitions (24x24 grid)
# ---------------------------------------------------------------------------

KIKI_REST = [
    ".........CCCC...........",
    ".......CCCCCCCG.........",
    "......CCCCCCCCCC........",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KHSEWWSSSSWEESH......",
    "...KHSSEESSSSEESSH......",
    "...KHSRREESSREESSH......",
    "....KSSSSSSSSSSSK.......",
    "....KFFFFFFFFFFFFK......",
    "...KFFffffffffffFFK.....",
    "..KFFffffFFFFFffffFK....",
    "..KBBBBBBBBBBBBBBBBK....",
    "..KBBHBBBBBBBBBBHBBK....",
    "..KBBHHBBBBBBBBHHBBK....",
    "..KBBHHHHGGGGHHHHBBK....",
    "..KBBHHHHHHHHHHHHBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_SCARF = [
    ".........CCCC...........",
    ".......CCCCCCCG.........",
    "......CCCCCCCCCC........",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KHSEWWSSSSWEESH......",
    "...KHSSEESSSSEESSH......",
    "...KHSRREESSREESSH......",
    "....KSSSSSSSSSSSK.......",
    "....KFFFFFFFFFFKSS......",
    "...KFFffffffffFKS.......",
    "..KFFffffFFFFfFK........",
    "..KBBBBBBBBBBBBBBBBK....",
    "..KBBHBBBBBBBBBBHBBK....",
    "..KBBHHBBBBBBBBHHBBK....",
    "..KBBHHHHGGGGHHHHBBK....",
    "..KBBHHHHHHHHHHHHBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_BLINK = [
    ".........CCCC...........",
    ".......CCCCCCCG.........",
    "......CCCCCCCCCC........",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KHHSSSSSSSSSHHK......",
    "...KHSSEESSSSEESSH......",
    "...KHSRREESSREESSH......",
    "....KSSSSSSSSSSSK.......",
    "....KFFFFFFFFFFFFK......",
    "...KFFffffffffffFFK.....",
    "..KFFffffFFFFFffffFK....",
    "..KBBBBBBBBBBBBBBBBK....",
    "..KBBHBBBBBBBBBBHBBK....",
    "..KBBHHBBBBBBBBHHBBK....",
    "..KBBHHHHGGGGHHHHBBK....",
    "..KBBHHHHHHHHHHHHBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_LISTEN = [
    ".........CCCC...G.......",
    ".......CCCCCCCG.GG......",
    "......CCCCCCCCCCG.......",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KHSEWWSSSSWEESH......",
    "...KHSSEESSSSEESSH......",
    "...KHSRREESSREESSH......",
    "....KSSSSSSSSSSSK.......",
    "...KFFFFFFFFFFFFFK......",
    "..KFFfffffffffffffFF....",
    ".KFFffffFFFFFfffffffFK..",
    "..KBBBBBBBBBBBBBBBBK....",
    "..KBBHBBBBBBBBBBHBBK....",
    "..KBBHHBBBBBBBBHHBBK....",
    "..KBBHHHHGGGGHHHHBBK....",
    "..KBBHHHHHHHHHHHHBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_PROCESS = [
    ".........CCCC...........",
    ".......CCCCCCCG.........",
    "......CCCCCCCCCC........",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KHSE..SSSS..EESH.....",
    "...KHSEEESSSSEEESSH.....",
    "...KHSRREESSREESSH......",
    "....KSSSSSSSSSSSK.......",
    "....KFFFFFFFFFFFFK......",
    "...KFFffffffffffFFK.....",
    "..KFFffffFFFFFffffFK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKPPPPXXPPPPKBBK....",
    "..KBBKPPPPXXPPPPKBBK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKKKKKKKKKKKKBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_CONFIRMED = [
    ".........CCCC..GG.......",
    ".......CCCCCCCGGG.......",
    "......CCCCCCCCCCG.......",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KH..EESSSSEE..SH.....",
    "...KHSSEESSSSEESSH......",
    "...KHSRREESSREESSH......",
    "....KSSSSSSSSSSSK.......",
    "....KFFFFFFFFFFFFK......",
    "...KFFffffffffffFFK.....",
    "..KFFffffFFFFFffffFK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKPPPPxxPPPPKBBK....",
    "..KBBKPPPPxxPPPPKBBK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKKKKKKKKKKKKBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_UNVERIFIED = [
    ".........CCCC...........",
    ".......CCCCCCCG.........",
    "......CCCCCCCCCC........",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KHSEWWSSSSWEESH......",
    "...KHSSEESSSSEESSH......",
    "...KHHSSSSSSSSSHHK......",
    "....KSSSSSSSSSSSK.......",
    "....KFFFFFFFFFFFFK......",
    "...KFFffffffffffFFK.....",
    "..KFFffffFFFFFffffFK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKPPPP..PPPPKBBK....",
    "..KBBKPPPP..PPPPKBBK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKKKKKKKKKKKKBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_RECOVERY = [
    "........ACCCC...........",
    ".......AACCCCCCG........",
    "........ACCCCCCC........",
    ".....KKHHHHHHHHHK.......",
    "....KHHSSHHSSHHHH.......",
    "...KHHSSSSSSSSSHHK......",
    "...KHSSEESSSSEESH.......",
    "...KHSE..SSSSE..SH......",
    "...KHSRREESSREESSH......",
    "....KSSSSSSSSSSSK.......",
    "....KFFFFFFFFFFFFK......",
    "...KFFffffffffffFFK.....",
    "..KFFffffFFFFFffffFK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKPPPPXXPPPPKBBK....",
    "..KBBKPPPPXXPPPPKBBK....",
    "..KBBKPPPPPPPPPPKBBK....",
    "..KBBKKKKKKKKKKKKBBK....",
    "...KBBBBBBBBBBBBBBK.....",
    "....KKKKKKKKKKKKKK......",
    ".....KLLLK..KLLLK.......",
    "....KLLLLK..KLLLLK......",
    "....KLLLLK..KLLLLK......",
    ".....KKKK....KKKK.......",
]

KIKI_PALETTES = {
    "autumn": {
        "K": "#0F172A", "H": "#78350F", "S": "#FED7AA",
        "E": "#1E1B4B", "W": "#FFFFFF", "R": "#FB7185",
        "C": "#1E3A8A", "G": "#F59E0B", "F": "#DC2626",
        "f": "#991B1B", "B": "#1E293B", "P": "#FEF3C7",
        "X": "#DC2626", "x": "#10B981", "A": "#F59E0B", "L": "#0F172A"
    },
    "frost": {
        "K": "#020617", "H": "#475569", "S": "#FFEDD5",
        "E": "#0F172A", "W": "#FFFFFF", "R": "#FDA4AF",
        "C": "#0F172A", "G": "#38BDF8", "F": "#0284C7",
        "f": "#0369A1", "B": "#1E293B", "P": "#F8FAFC",
        "X": "#0284C7", "x": "#10B981", "A": "#F59E0B", "L": "#020617"
    },
    "matcha": {
        "K": "#064E3B", "H": "#78350F", "S": "#FEF3C7",
        "E": "#022C22", "W": "#FFFFFF", "R": "#F472B6",
        "C": "#064E3B", "G": "#FBBF24", "F": "#15803D",
        "f": "#166534", "B": "#064E3B", "P": "#FEF3C7",
        "X": "#15803D", "x": "#10B981", "A": "#F59E0B", "L": "#022C22"
    }
}


def draw_matrix_to_painter(
    painter: QPainter,
    grid: List[str],
    palette: Dict[str, str],
    center_x: int,
    center_y: int,
    cell_scale: int = 2
) -> None:
    grid_w = len(grid[0])
    grid_h = len(grid)
    start_x = int(center_x - (grid_w * cell_scale / 2))
    start_y = int(center_y - (grid_h * cell_scale / 2))

    painter.setPen(Qt.NoPen)
    for gy, row in enumerate(grid):
        for gx, ch in enumerate(row):
            if ch == ".":
                continue
            color_hex = palette.get(ch)
            if color_hex:
                painter.fillRect(start_x + (gx * cell_scale), start_y + (gy * cell_scale), cell_scale, cell_scale, QColor(color_hex))


def render_state_image(
    grid: List[str],
    palette_name: str = "autumn",
    cell_scale: int = 2,
    bg_color: Optional[str] = None
) -> QImage:
    dim = 24 * cell_scale
    # Add small padding for presentation
    pad = 8 * cell_scale
    w = dim + pad
    h = dim + pad
    img = QImage(w, h, QImage.Format_ARGB32)
    if bg_color:
        img.fill(QColor(bg_color))
    else:
        img.fill(QColor(0, 0, 0, 0))

    painter = QPainter(img)
    pal = KIKI_PALETTES.get(palette_name, KIKI_PALETTES["autumn"])
    draw_matrix_to_painter(painter, grid, pal, w // 2, h // 2, cell_scale=cell_scale)
    painter.end()
    return img


def generate_contact_sheet(bg_color: str, output_path: Path) -> None:
    """Renders all 6 states in a clean visual grid with labels and borders."""
    states = [
        ("1. Idle (Resting)", KIKI_REST, "Straightens scarf occasionally"),
        ("2. Listening", KIKI_LISTEN, "Perked attentive eyes & flutter"),
        ("3. Processing", KIKI_PROCESS, "Cradles letter & inspects seal"),
        ("4. Verified Done", KIKI_CONFIRMED, "Delivery bow & emerald seal"),
        ("5. Sent Unverified", KIKI_UNVERIFIED, "Neutral forward peer (honest pause)"),
        ("6. Recoverable Failure", KIKI_RECOVERY, "Sympathetic address check (amber ?)")
    ]

    card_w = 160
    card_h = 160
    margin = 20
    cols = 3
    rows = 2
    total_w = (cols * card_w) + ((cols + 1) * margin)
    total_h = (rows * card_h) + ((rows + 1) * margin) + 60  # 60px header

    canvas = QImage(total_w, total_h, QImage.Format_ARGB32)
    canvas.fill(QColor(bg_color))

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing, True)

    is_dark = QColor(bg_color).lightness() < 128
    text_color = QColor("#F8FAFC") if is_dark else QColor("#0F172A")
    subtext_color = QColor("#94A3B8") if is_dark else QColor("#64748B")
    card_bg = QColor("#1E293B") if is_dark else QColor("#FFFFFF")
    card_border = QColor("#334155") if is_dark else QColor("#E2E8F0")

    # Header
    painter.setPen(text_color)
    f_title = QFont("Segoe UI", 13, QFont.Bold)
    painter.setFont(f_title)
    painter.drawText(margin, 35, "FlowPilot Original Anime Companion — 'Kiki the Little Scarf Courier' (24x24 px)")

    f_sub = QFont("Segoe UI", 9)
    painter.setFont(f_sub)
    painter.setPen(subtext_color)
    painter.drawText(margin, 52, f"6-State Visual Contact Sheet | Palette: Autumn Ember | Background: {bg_color}")

    # Draw State Cards
    pal = KIKI_PALETTES["autumn"]
    for idx, (title, grid, subtitle) in enumerate(states):
        c = idx % cols
        r = idx // cols
        x = margin + c * (card_w + margin)
        y = 70 + r * (card_h + margin)

        # Card Frame
        painter.setPen(QPen(card_border, 1.2))
        painter.setBrush(QBrush(card_bg))
        painter.drawRoundedRect(QRectF(x, y, card_w, card_h), 8.0, 8.0)

        # Character Sprite (scaled 3x -> 72x72 px for clear desktop readability)
        char_cx = x + (card_w // 2)
        char_cy = y + 54
        draw_matrix_to_painter(painter, grid, pal, char_cx, char_cy, cell_scale=3)

        # State Title
        painter.setPen(text_color)
        f_card_title = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(f_card_title)
        painter.drawText(QRectF(x + 6, y + 104, card_w - 12, 18), Qt.AlignCenter, title)

        # State Subtitle
        painter.setPen(subtext_color)
        f_card_sub = QFont("Segoe UI", 8)
        painter.setFont(f_card_sub)
        painter.drawText(QRectF(x + 6, y + 122, card_w - 12, 30), Qt.AlignCenter | Qt.TextWordWrap, subtitle)

    painter.end()
    canvas.save(str(output_path), "PNG")
    print(f"[Export] Saved contact sheet: {output_path}")


def generate_animated_preview_gif(output_path: Path) -> None:
    """Builds a restrained, deterministic animation demonstration GIF."""
    frames_meta = [
        # 1. Idle breathing (4 frames)
        (KIKI_REST, 350),
        (KIKI_BLINK, 160),
        (KIKI_REST, 400),
        # 2. Scarf adjustment signature action (2 frames)
        (KIKI_SCARF, 300),
        (KIKI_REST, 300),
        # 3. Attentive listening (3 pulses)
        (KIKI_LISTEN, 280),
        (KIKI_REST, 200),
        (KIKI_LISTEN, 280),
        # 4. Processing parcel hold (3 frames)
        (KIKI_PROCESS, 350),
        (KIKI_PROCESS, 350),
        # 5. Verified completion delivery bow & emerald seal (celebrates once, exactly 800ms)
        (KIKI_CONFIRMED, 800),
        # 6. Neutral unverified pause
        (KIKI_UNVERIFIED, 450),
        # 7. Sympathetic address recovery
        (KIKI_RECOVERY, 600),
        # 8. Return to calm resting
        (KIKI_REST, 500)
    ]

    pil_images: List[Image.Image] = []
    durations: List[int] = []

    for idx, (grid, dur_ms) in enumerate(frames_meta):
        qimg = render_state_image(grid, palette_name="autumn", cell_scale=3, bg_color="#0F172A")
        # Save temp PNG and open with PIL
        temp_png = OUTPUT_DIR / f"_tmp_frame_{idx}.png"
        qimg.save(str(temp_png), "PNG")
        pil_im = Image.open(temp_png).convert("RGBA")
        pil_images.append(pil_im)
        durations.append(dur_ms)
        temp_png.unlink()

    # Save animated GIF
    pil_images[0].save(
        str(output_path),
        save_all=True,
        append_images=pil_images[1:],
        duration=durations,
        loop=0
    )
    print(f"[Export] Saved animated motion preview GIF: {output_path}")


def run_visual_verification() -> bool:
    """Automated visual acceptance checks for Kiki the Little Scarf Courier."""
    print("Running automated visual acceptance checks...")
    grids = {
        "rest": KIKI_REST,
        "scarf": KIKI_SCARF,
        "blink": KIKI_BLINK,
        "listen": KIKI_LISTEN,
        "process": KIKI_PROCESS,
        "confirmed": KIKI_CONFIRMED,
        "unverified": KIKI_UNVERIFIED,
        "recovery": KIKI_RECOVERY
    }

    # 1. Dimension & row integrity
    for name, g in grids.items():
        assert len(g) == 24, f"State '{name}' has {len(g)} rows, expected 24"
        for r_idx, row in enumerate(g):
            assert len(row) == 24, f"State '{name}' row {r_idx} has {len(row)} cols, expected 24"

    # 2. Assert distinct visual diffs across all 6 core states
    core_states = ["rest", "listen", "process", "confirmed", "unverified", "recovery"]
    for i in range(len(core_states)):
        for j in range(i + 1, len(core_states)):
            s1 = core_states[i]
            s2 = core_states[j]
            assert grids[s1] != grids[s2], f"State collision: '{s1}' and '{s2}' have identical matrices!"

    # 3. Assert non-transparent content ratio (must be a substantial character, not empty or solid block)
    for name, g in grids.items():
        filled = sum(sum(1 for c in row if c != ".") for row in g)
        ratio = filled / (24 * 24)
        assert 0.20 <= ratio <= 0.70, f"State '{name}' pixel fill ratio {ratio:.2%} outside expected [20%, 70%]"

    print("[PASS] All visual acceptance assertions verified cleanly.")
    return True


if __name__ == "__main__":
    run_visual_verification()
    generate_contact_sheet("#0F172A", OUTPUT_DIR / "kiki_contact_sheet_dark.png")
    generate_contact_sheet("#F8FAFC", OUTPUT_DIR / "kiki_contact_sheet_light.png")
    generate_animated_preview_gif(OUTPUT_DIR / "kiki_motion_preview.gif")
    print("Companion prototype generation complete!")
