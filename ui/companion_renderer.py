"""
FlowPilot Unified Companion & Indicator Rendering Engine
Single source of truth for rendering all companion characters and visual indicators
across the Floating HUD and Companion Studio Preview.

Guarantees:
1. Pixel-for-pixel parity between Floating HUD and Companion Studio.
2. Complete reduced-motion enforcement (freezes all procedural loops into static states).
3. Frame-rate independent elapsed-time phase calculations.
4. Device-pixel snapping for crisp, unblurred pixel art across 100%-200% DPI scaling.
5. Strict audio-envelope realism (envelope expands only during genuine speech capture).
"""

import math
import sys
from typing import Dict, Any, Optional, Tuple

from PySide6.QtCore import Qt, QRectF, QPointF, QElapsedTimer
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont, QPixmap, QImage,
    QLinearGradient, QRadialGradient
)

try:
    import ui.pet_sprites as ps
except Exception:
    try:
        import pet_sprites as ps
    except Exception:
        ps = None


# ---------------------------------------------------------------------------
# Pilot Robot Courier: Original Pixel Matrix Definitions (24x24 grid)
# ---------------------------------------------------------------------------
# Legend: . empty | K dark chassis outline (#0F172A) | B armor (#1E293B)
#         H highlight (#334155) | V visor bg (#020617) | C visor cyan (#38BDF8)
#         E visor emerald (#10B981) | A visor amber (#F59E0B) | W white accent (#F8FAFC)
#         T tread/foot (#090D16) | L antenna light

PILOT_REST = [
    "..........KK............",
    ".........KLLK...........",
    "..........KK............",
    "..........KK............",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBHHHHHHHHHBBBK....",
    "...KBHHVVVVVVVVHHBBK...",
    "...KBHVVCCCCVVCCCCVHK...",
    "...KBHVVCCCCVVCCCCVHK...",
    "...KBHHVVVVVVVVHHBBK...",
    "....KBBHHHHHHHHHBBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBKHHHHHHHHKBBK....",
    "....KBBKCWCCCCWCKBBK....",
    "....KBBKHHHHHHHHKBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KTTTTK..KTTTTK.....",
    "....KTTTTTTKKTTTTTTK....",
    "....KTTTTTTKKTTTTTTK....",
    ".....KKKKKK..KKKKKK.....",
]

PILOT_BLINK = [
    "..........KK............",
    ".........KLLK...........",
    "..........KK............",
    "..........KK............",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBHHHHHHHHHBBBK....",
    "...KBHHVVVVVVVVHHBBK...",
    "...KBHVVVVVVVVVVVVVHK...",
    "...KBHVVCCCCVVCCCCVHK...",
    "...KBHHVVVVVVVVHHBBK...",
    "....KBBHHHHHHHHHBBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBKHHHHHHHHKBBK....",
    "....KBBKCWCCCCWCKBBK....",
    "....KBBKHHHHHHHHKBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KTTTTK..KTTTTK.....",
    "....KTTTTTTKKTTTTTTK....",
    "....KTTTTTTKKTTTTTTK....",
    ".....KKKKKK..KKKKKK.....",
]

PILOT_LISTEN = [
    "..........KK............",
    ".........KLLK...........",
    "..........KK............",
    "..........KK............",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBHHHHHHHHHBBBK....",
    "...KBHHVVVVVVVVHHBBK...",
    "...KBHV.C..C..C..VVHK...",
    "...KBHVCC.CCC.CC.VVHK...",
    "...KBHHVVVVVVVVHHBBK...",
    "....KBBHHHHHHHHHBBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBKHHHHHHHHKBBK....",
    "....KBBKCWCCCCWCKBBK....",
    "....KBBKHHHHHHHHKBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KTTTTK..KTTTTK.....",
    "....KTTTTTTKKTTTTTTK....",
    "....KTTTTTTKKTTTTTTK....",
    ".....KKKKKK..KKKKKK.....",
]

PILOT_WORKING = [
    "..........KK............",
    ".........KLLK...........",
    "..........KK............",
    "..........KK............",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBHHHHHHHHHBBBK....",
    "...KBHHVVVVVVVVHHBBK...",
    "...KBHV.A..A..A..VVHK...",
    "...KBHV..A..A..A.VVHK...",
    "...KBHHVVVVVVVVHHBBK...",
    "....KBBHHHHHHHHHBBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBKHHHHHHHHKBBK....",
    "....KBBKCWCCCCWCKBBK....",
    "....KBBKHHHHHHHHKBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KTTTTK..KTTTTK.....",
    "....KTTTTTTKKTTTTTTK....",
    "....KTTTTTTKKTTTTTTK....",
    ".....KKKKKK..KKKKKK.....",
]

PILOT_CONFIRMED = [
    "..........KK............",
    ".........KEEK...........",
    "..........KK............",
    "..........KK............",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBHHHHHHHHHBBBK....",
    "...KBHHVVVVVVVVHHBBK...",
    "...KBHVVEVVVVEVVVEEHK...",
    "...KBHVVEEEEVEEEEEVHK...",
    "...KBHHVVVVVVVVHHBBK...",
    "....KBBHHHHHHHHHBBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBKHHHHHHHHKBBK....",
    "....KBBKEWEEEEWCKBBK....",
    "....KBBKHHHHHHHHKBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KTTTTK..KTTTTK.....",
    "....KTTTTTTKKTTTTTTK....",
    "....KTTTTTTKKTTTTTTK....",
    ".....KKKKKK..KKKKKK.....",
]

PILOT_RECOVERY = [
    "..........KK............",
    ".........KAAK...........",
    "..........KK............",
    "..........KK............",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBHHHHHHHHHBBBK....",
    "...KBHHVVVVVVVVHHBBK...",
    "...KBHVVVAAAVVAAAVVHK...",
    "...KBHVVVVVAVVVVAVVHK...",
    "...KBHHVVVVVVVVHHBBK...",
    "....KBBHHHHHHHHHBBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KBBBBBBBBBBBBK.....",
    "....KBBKHHHHHHHHKBBK....",
    "....KBBKAWAAAAWCKBBK....",
    "....KBBKHHHHHHHHKBBK....",
    ".....KBBBBBBBBBBBBK.....",
    "......KKKKKKKKKKKK......",
    ".....KTTTTK..KTTTTK.....",
    "....KTTTTTTKKTTTTTTK....",
    "....KTTTTTTKKTTTTTTK....",
    ".....KKKKKK..KKKKKK.....",
]

PILOT_PALETTES = {
    "default": {
        "K": "#0A0F1D", "B": "#1E293B", "H": "#334155",
        "V": "#020617", "C": "#38BDF8", "E": "#10B981",
        "A": "#F59E0B", "W": "#F8FAFC", "T": "#0F172A", "L": "#38BDF8"
    },
    "emerald": {
        "K": "#022C22", "B": "#064E3B", "H": "#047857",
        "V": "#022C22", "C": "#34D399", "E": "#10B981",
        "A": "#F59E0B", "W": "#F0FDF4", "T": "#022C22", "L": "#34D399"
    },
    "amber": {
        "K": "#1C1917", "B": "#451A03", "H": "#78350F",
        "V": "#1C1917", "C": "#FBBF24", "E": "#10B981",
        "A": "#F59E0B", "W": "#FFFBEB", "T": "#292524", "L": "#FBBF24"
    }
}

# ---------------------------------------------------------------------------
# Seedling: Sleepy Seed Creature (24x24 grid)
# ---------------------------------------------------------------------------
# Legend: . empty | K dark outline (#14281D) | B acorn body (#78350F)
#         W warm cream belly (#FEF3C7) | S rich stem green (#15803D)
#         L vibrant leaf green (#22C55E) | E eye (#0F172A) | R blush (#F87171)
#         F bloom flower (#F43F5E)

SEED_REST = [
    "........................",
    "............SS..........",
    "...........SLL..........",
    "...........SLL..........",
    "............SS..........",
    ".........KKKKKKKK.......",
    ".......KKBBBBBBBBKK.....",
    "......KBBBBBBBBBBBBK....",
    ".....KBBBBBBBBBBBBBBK...",
    "....KBBBBBBBBBBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "...KBBW..WWWWWW..WBBBBK.",
    "...KBBWEEWWWWWWEEWBBBBK.",
    "...KBBWRRWWWWWRRWBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "....KBBWWWWWWWWWWBBBBK..",
    "....KBBBBWWWWWWBBBBBBK..",
    ".....KBBBBBBBBBBBBBBK...",
    "......KBBBBBBBBBBBBK....",
    ".......KKBBBBBBBBKK.....",
    "........KKKKKKKKKK......",
    "........................",
    "........................",
]

SEED_LISTEN = [
    "............LL..........",
    "...........LLLL.........",
    "..........LLLLLL........",
    "............SS..........",
    "............SS..........",
    ".........KKKKKKKK.......",
    ".......KKBBBBBBBBKK.....",
    "......KBBBBBBBBBBBBK....",
    ".....KBBBBBBBBBBBBBBK...",
    "....KBBBBBBBBBBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "...KBBW.EEWWWW.EEWBBBBK.",
    "...KBBWEEEWWWWEEEWBBBBK.",
    "...KBBWRRRWWWWRRRWBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "....KBBWWWWWWWWWWBBBBK..",
    "....KBBBBWWWWWWBBBBBBK..",
    ".....KBBBBBBBBBBBBBBK...",
    "......KBBBBBBBBBBBBK....",
    ".......KKBBBBBBBBKK.....",
    "........KKKKKKKKKK......",
    "........................",
    "........................",
]

SEED_WORKING = [
    ".............LL.........",
    "............LLLL........",
    "...........LLLL.........",
    "............SS..........",
    "............SS..........",
    ".........KKKKKKKK.......",
    ".......KKBBBBBBBBKK.....",
    "......KBBBBBBBBBBBBK....",
    ".....KBBBBBBBBBBBBBBK...",
    "....KBBBBBBBBBBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "...KBBW..WWWWWW..WBBBBK.",
    "...KBBWWEEWWWWEEWWBBBBK.",
    "...KBBWRRWWWWWRRWBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "....KBBWWWWWWWWWWBBBBK..",
    "....KBBBBWWWWWWBBBBBBK..",
    ".....KBBBBBBBBBBBBBBK...",
    "......KBBBBBBBBBBBBK....",
    ".......KKBBBBBBBBKK.....",
    "........KKKKKKKKKK......",
    "........................",
    "........................",
]

SEED_CONFIRMED = [
    "...........FFLL.........",
    "..........FFFFFF........",
    "...........FFLL.........",
    "............SS..........",
    "............SS..........",
    ".........KKKKKKKK.......",
    ".......KKBBBBBBBBKK.....",
    "......KBBBBBBBBBBBBK....",
    ".....KBBBBBBBBBBBBBBK...",
    "....KBBBBBBBBBBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "...KBBWEEWWWWWWEEWBBBBK.",
    "...KBBW..EWWWW..EWBBBBK.",
    "...KBBWRRWWWWWRRWBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "....KBBWWWWWWWWWWBBBBK..",
    "....KBBBBWWWWWWBBBBBBK..",
    ".....KBBBBBBBBBBBBBBK...",
    "......KBBBBBBBBBBBBK....",
    ".......KKBBBBBBBBKK.....",
    "........KKKKKKKKKK......",
    "........................",
    "........................",
]

SEED_RECOVERY = [
    "........................",
    "........................",
    ".............SS.........",
    "..............SSLL......",
    "...............SLL......",
    ".........KKKKKKKK.......",
    ".......KKBBBBBBBBKK.....",
    "......KBBBBBBBBBBBBK....",
    ".....KBBBBBBBBBBBBBBK...",
    "....KBBBBBBBBBBBBBBBBK..",
    "...KBBBBBBBBBBBBBBBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "...KBBW..WWWWWW..WBBBBK.",
    "...KBBW.EWWWWWW.EWBBBBK.",
    "...KBBW..WWWWWW..WBBBBK.",
    "...KBBWWWWWWWWWWWWBBBBK.",
    "....KBBWWWWWWWWWWBBBBK..",
    "....KBBBBWWWWWWBBBBBBK..",
    ".....KBBBBBBBBBBBBBBK...",
    "......KBBBBBBBBBBBBK....",
    ".......KKBBBBBBBBKK.....",
    "........KKKKKKKKKK......",
    "........................",
    "........................",
]

SEED_PALETTES = {
    "default": {
        "K": "#14281D", "B": "#78350F", "W": "#FEF3C7",
        "S": "#15803D", "L": "#22C55E", "E": "#0F172A",
        "R": "#F87171", "F": "#F43F5E"
    },
    "sage": {
        "K": "#0F281E", "B": "#4A7C59", "W": "#E8F5E9",
        "S": "#2D6A4F", "L": "#52B788", "E": "#0A1F16",
        "R": "#F48FB1", "F": "#FF4081"
    }
}

# ---------------------------------------------------------------------------
# Nimbus: Vapor Cloud Sprite (24x24 grid)
# ---------------------------------------------------------------------------
# Legend: . empty | K cloud outline (#1E293B) | B cloud body (#CBD5E1)
#         W cloud top puff (#F8FAFC) | C core glow (#38BDF8)
#         A core amber (#F59E0B) | E core emerald (#10B981)
#         P core purple (#A855F7) | F face eye (#0F172A)

NIMBUS_REST = [
    "........................",
    ".........KKKKKK.........",
    ".......KKWWWWWWKK.......",
    ".....KKWWWWWWWWWWKK.....",
    "...KKWWWWWWWWWWWWWWKK...",
    "..KWWWWWWWWWWWWWWWWWWK..",
    ".KBBWWWWWWWWWWWWWWWWBBK.",
    ".KBBBBWWWWWWWWWWWWBBBBK.",
    ".KBBBBBBPPPPPPPPBBBBBBK.",
    ".KBBBBBBPPPPPPPPBBBBBBK.",
    ".KBBBBBB..FFFF..BBBBBBK.",
    ".KBBBBBB..FFFF..BBBBBBK.",
    ".KBBBBBBPPPPPPPPBBBBBBK.",
    ".KBBBBBBPPPPPPPPBBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBK..",
    "...KKBBBBBBBBBBBBBBKK...",
    ".....KKKKBBBBBBKKKK.....",
    ".........KKKKKK.........",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
]

NIMBUS_LISTEN = [
    "........................",
    ".........KKKKKK.........",
    ".......KKWWWWWWKK.......",
    ".....KKWWWWWWWWWWKK.....",
    "...KKWWWWWWWWWWWWWWKK...",
    "..KWWWWWWWWWWWWWWWWWWK..",
    ".KBBWWWWWWWWWWWWWWWWBBK.",
    ".KBBBBWWWWWWWWWWWWBBBBK.",
    ".KBBBBBBCCCCCCCCBBBBBBK.",
    ".KBBBBBBCCCCCCCCBBBBBBK.",
    ".KBBBBBB.FF..FF.BBBBBBK.",
    ".KBBBBBB.FF..FF.BBBBBBK.",
    ".KBBBBBBCCCCCCCCBBBBBBK.",
    ".KBBBBBBCCCCCCCCBBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBK..",
    "...KKBBBBBBBBBBBBBBKK...",
    ".....KKKKBBBBBBKKKK.....",
    ".........KKKKKK.........",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
]

NIMBUS_WORKING = [
    "........................",
    ".........KKKKKK.........",
    ".......KKWWWWWWKK.......",
    ".....KKWWWWWWWWWWKK.....",
    "...KKWWWWWWWWWWWWWWKK...",
    "..KWWWWWWWWWWWWWWWWWWK..",
    ".KBBWWWWWWWWWWWWWWWWBBK.",
    ".KBBBBWWWWWWWWWWWWBBBBK.",
    ".KBBBBBBAAAAAAAABBBBBBK.",
    ".KBBBBBBAAAAAAAABBBBBBK.",
    ".KBBBBBB..FFFF..BBBBBBK.",
    ".KBBBBBB..FFFF..BBBBBBK.",
    ".KBBBBBBAAAAAAAABBBBBBK.",
    ".KBBBBBBAAAAAAAABBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBK..",
    "...KKBBBBBBBBBBBBBBKK...",
    ".....KKKKBBBBBBKKKK.....",
    ".........KKKKKK.........",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
]

NIMBUS_CONFIRMED = [
    "........................",
    ".........KKKKKK.........",
    ".......KKWWWWWWKK.......",
    ".....KKWWWWWWWWWWKK.....",
    "...KKWWWWWWWWWWWWWWKK...",
    "..KWWWWWWWWWWWWWWWWWWK..",
    ".KBBWWWWWWWWWWWWWWWWBBK.",
    ".KBBBBWWWWWWWWWWWWBBBBK.",
    ".KBBBBBBEEEEEEEEBBBBBBK.",
    ".KBBBBBBEEEEEEEEBBBBBBK.",
    ".KBBBBBBFF....FFBBBBBBK.",
    ".KBBBBBB.FFFFFF.BBBBBBK.",
    ".KBBBBBBEEEEEEEEBBBBBBK.",
    ".KBBBBBBEEEEEEEEBBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBK..",
    "...KKBBBBBBBBBBBBBBKK...",
    ".....KKKKBBBBBBKKKK.....",
    ".........KKKKKK.........",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
]

NIMBUS_RECOVERY = [
    "........................",
    ".........KKKKKK.........",
    ".......KKWWWWWWKK.......",
    ".....KKWWWWWWWWWWKK.....",
    "...KKWWWWWWWWWWWWWWKK...",
    "..KWWWWWWWWWWWWWWWWWWK..",
    ".KBBWWWWWWWWWWWWWWWWBBK.",
    ".KBBBBWWWWWWWWWWWWBBBBK.",
    ".KBBBBBB.AAAAAA.BBBBBBK.",
    ".KBBBBBB.AAAAAA.BBBBBBK.",
    ".KBBBBBB..FFFF..BBBBBBK.",
    ".KBBBBBB..F..F..BBBBBBK.",
    ".KBBBBBB.AAAAAA.BBBBBBK.",
    ".KBBBBBB.AAAAAA.BBBBBBK.",
    "..KBBBBBBBBBBBBBBBBBBK..",
    "...KKBBBBBBBBBBBBBBKK...",
    ".....KKKKBBBBBBKKKK.....",
    ".........KKKKKK.........",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
    "........................",
]

NIMBUS_PALETTES = {
    "default": {
        "K": "#1E293B", "B": "#94A3B8", "W": "#F8FAFC",
        "C": "#38BDF8", "A": "#F59E0B", "E": "#10B981",
        "P": "#A855F7", "F": "#0F172A"
    },
    "sunset": {
        "K": "#4A0E17", "B": "#F472B6", "W": "#FDF2F8",
        "C": "#FB923C", "A": "#F59E0B", "E": "#34D399",
        "P": "#E879F9", "F": "#374151"
    }
}

# ---------------------------------------------------------------------------
# Kiki: The Little Scarf Courier (Original Anime-Inspired Companion, 24x24)
# ---------------------------------------------------------------------------
# Legend: . empty | K dark silhouette outline (#0F172A) | H chestnut hair (#78350F)
#         S warm peach skin (#FED7AA) | E anime eye (#1E1B4B) | W eye shine white (#FFFFFF)
#         R blush pink (#FB7185) | C postal navy beret (#1E3A8A) | G gold badge/star (#F59E0B)
#         F crimson scarf (#DC2626) | f scarf shade (#991B1B) | B courier coat (#1E293B)
#         P parchment envelope (#FEF3C7) | X red wax seal (#DC2626) | x emerald seal (#10B981)
#         A amber question mark (#F59E0B) | L dark leather boots (#0F172A)

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
    "default": {
        "K": "#0F172A", "H": "#78350F", "S": "#FED7AA",
        "E": "#1E1B4B", "W": "#FFFFFF", "R": "#FB7185",
        "C": "#1E3A8A", "G": "#F59E0B", "F": "#DC2626",
        "f": "#991B1B", "B": "#1E293B", "P": "#FEF3C7",
        "X": "#DC2626", "x": "#10B981", "A": "#F59E0B", "L": "#0F172A"
    },
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

class CompanionRenderer:
    """
    Centralized rendering engine providing authoritative rendering for:
    - 'signal': Modern calm adaptive capsule indicator (5-bar envelope / processing dots)
    - 'pilot' / 'mascot': Original FlowPilot pixel courier robot
    - 'kitty': SondeR-Cat pixel companion
    - 'dog': Pixel pup companion
    - 'edge_line': Docked vertical accent indicator
    - 'wave_bar': Soundwave equalizer
    - 'retro' / 'emoji' / custom images
    """

    _pixmap_cache: Dict[str, QPixmap] = {}
    _MAX_CACHE_ENTRIES = 128

    @classmethod
    def normalize_state(cls, raw_state: str) -> str:
        """Map raw application or engine states into canonical rendering states."""
        s = (raw_state or "").lower().strip()
        if s in ("listening", "recording", "voice_active"):
            return "listening"
        if s in ("processing", "transcribing", "validating", "thinking"):
            return "processing"
        if s in ("confirmed", "success", "pasted", "inserted"):
            return "confirmed"
        if s in ("unverified", "sent_unverified"):
            return "unverified"
        if s in ("recovery", "failed_recovery", "error", "cancelled"):
            return "recovery"
        return "idle"

    @classmethod
    def get_preferred_size(cls, style: str) -> Tuple[int, int]:
        """Return default width and height for a visual style."""
        st = (style or "").lower().strip()
        if st in ("signal", "wave_bar"):
            return (68, 28)
        if st in ("edge_line", "signal_edge"):
            return (14, 68)
        if st in ("mascot", "pilot", "seedling", "nimbus", "kiki", "courier"):
            return (72, 72)
        if st in ("kitty", "dog", "fox", "dino", "ghost", "bunny", "pikachu", "charmander", "gengar", "eevee"):
            return (78, 84)
        return (84, 84)

    @classmethod
    def render(
        cls,
        painter: QPainter,
        bounds: QRectF,
        style: str,
        state: str,
        elapsed_ms: float = 0.0,
        audio_level: float = 0.0,
        palette: str = "default",
        reduced_motion: bool = False,
        device_pixel_ratio: float = 1.0,
        is_preview: bool = False,
        custom_data: Optional[Dict[str, Any]] = None,
        state_elapsed_ms: Optional[float] = None
    ) -> None:
        """
        Main rendering entrypoint.
        """
        canonical_state = cls.normalize_state(state)
        style_key = (style or "signal").lower().strip()

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        cx = bounds.center().x()
        cy = bounds.center().y()

        # 1. Signal (Quiet Default Capsule Indicator)
        if style_key in ("signal", "wave_bar"):
            cls._draw_signal(painter, bounds, canonical_state, elapsed_ms, audio_level, reduced_motion)

        # 2. Docked Edge Line
        elif style_key in ("edge_line", "signal_edge"):
            cls._draw_edge_line(painter, bounds, canonical_state, elapsed_ms, audio_level, reduced_motion)

        # 3. Pilot (Original Pixel Courier Robot)
        elif style_key in ("pilot", "mascot"):
            cls._draw_pilot(painter, cx, cy, canonical_state, elapsed_ms, audio_level, palette, reduced_motion, device_pixel_ratio)

        # 3b. Seedling (Sleepy Seed Creature - Concept 2)
        elif style_key == "seedling":
            cls._draw_seedling(painter, cx, cy, canonical_state, elapsed_ms, audio_level, palette, reduced_motion, device_pixel_ratio)

        # 3c. Nimbus (Vapor Cloud Sprite - Concept 3)
        elif style_key == "nimbus":
            cls._draw_nimbus(painter, cx, cy, canonical_state, elapsed_ms, audio_level, palette, reduced_motion, device_pixel_ratio)

        # 3d. Kiki (The Little Scarf Courier - Original Anime Companion)
        elif style_key in ("kiki", "courier"):
            age = elapsed_ms if state_elapsed_ms is None else state_elapsed_ms
            cls._draw_kiki(painter, cx, cy, canonical_state, age, audio_level, palette, reduced_motion, device_pixel_ratio)

        # 4. SondeR-Cat Pixel Kitty
        elif style_key == "kitty":
            cls._draw_kitty(painter, cx, cy, canonical_state, elapsed_ms, audio_level, palette, reduced_motion)

        # 5. Pixel Dog / Pup
        elif style_key == "dog":
            cls._draw_dog(painter, cx, cy, canonical_state, palette, reduced_motion)

        # 6. Retro Companions
        elif style_key in ("fox", "dino", "ghost", "bunny", "pikachu", "charmander", "gengar", "eevee"):
            cls._draw_retro(painter, cx, cy, style_key, canonical_state, reduced_motion)

        # 7. Custom Image / Emoji / Spritesheet
        elif custom_data:
            cls._draw_custom(painter, bounds, custom_data, canonical_state, elapsed_ms, audio_level, reduced_motion)

        else:
            # Fallback to Pilot
            cls._draw_pilot(painter, cx, cy, canonical_state, elapsed_ms, audio_level, palette, reduced_motion, device_pixel_ratio)

        painter.restore()

    # -----------------------------------------------------------------------
    # 1. Signal: Quiet Neutral Capsule Indicator
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_signal(
        cls,
        painter: QPainter,
        bounds: QRectF,
        state: str,
        elapsed_ms: float,
        audio_level: float,
        reduced_motion: bool
    ) -> None:
        """
        Draws the Signal quiet capsule:
        - Resting idle: single steady accent marker.
        - Listening: 5-bar audio-driven envelope (driven by real audio_level).
        - Processing: 3 calm, moving dots (static if reduced_motion).
        - Confirmed: serene check/emerald marker.
        - Recovery: distinct amber/coral recovery indicator.
        """
        w = bounds.width()
        h = bounds.height()
        cx = bounds.center().x()
        cy = bounds.center().y()

        # Capsule geometry: centered pill
        cap_w = min(w - 4, 62.0)
        cap_h = min(h - 4, 24.0)
        cap_rect = QRectF(cx - (cap_w / 2.0), cy - (cap_h / 2.0), cap_w, cap_h)
        radius = cap_h / 2.0

        # Background: dark adaptive slate with subtle border
        bg_color = QColor(15, 23, 42, 235)       # #0F172A slate-900
        border_color = QColor(51, 65, 85, 200)   # #334155 slate-700
        painter.setBrush(QBrush(bg_color))
        painter.setPen(QPen(border_color, 1.2))
        painter.drawRoundedRect(cap_rect, radius, radius)

        # State Contents
        if state == "listening":
            # 5-bar audio-driven envelope
            num_bars = 5
            bar_w = 3.5
            bar_gap = 4.0
            total_w = (num_bars * bar_w) + ((num_bars - 1) * bar_gap)
            start_x = cx - (total_w / 2.0)

            # Audio level scaled smoothly
            lvl = max(0.0, min(1.0, audio_level))
            accent = QColor("#38BDF8")  # Sky-400
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(accent))

            for i in range(num_bars):
                bx = start_x + (i * (bar_w + bar_gap))
                if reduced_motion:
                    # Pure envelope without ornamental flutter
                    center_bias = 1.0 - (abs(i - 2) * 0.22)
                    bh = 4.0 + (lvl * 12.0 * center_bias)
                else:
                    phase = (elapsed_ms * 0.008) + (i * 0.95)
                    flutter = math.sin(phase) * 1.5 if lvl > 0.05 else 0.0
                    center_bias = 1.0 - (abs(i - 2) * 0.2)
                    bh = 4.0 + (lvl * 11.0 * center_bias) + flutter
                bh = max(3.5, min(cap_h - 6.0, bh))
                by = cy - (bh / 2.0)
                painter.drawRoundedRect(QRectF(bx, by, bar_w, bh), 1.75, 1.75)

        elif state == "processing":
            # 3 calm processing dots
            num_dots = 3
            dot_r = 2.2
            spacing = 8.0
            start_x = cx - ((num_dots - 1) * spacing / 2.0)
            dot_color = QColor("#F59E0B")  # Amber-500

            for i in range(num_dots):
                dx = start_x + (i * spacing)
                if reduced_motion:
                    alpha = 230
                else:
                    t = (elapsed_ms * 0.005) - (i * 0.45)
                    alpha = int(120 + 135 * (0.5 + 0.5 * math.sin(t)))
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(dot_color.red(), dot_color.green(), dot_color.blue(), alpha)))
                painter.drawEllipse(QPointF(dx, cy), dot_r, dot_r)

        elif state == "confirmed":
            # Serene confirmed emerald accent
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#10B981")))
            painter.drawRoundedRect(QRectF(cx - 10, cy - 2.5, 20, 5), 2.5, 2.5)

        elif state == "unverified":
            # Subtle neutral waiting indicator (does not imply confirmed paste)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#94A3B8")))
            painter.drawEllipse(QPointF(cx, cy), 3.0, 3.0)

        elif state == "recovery":
            # Amber recovery indicator
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#F59E0B")))
            painter.drawRoundedRect(QRectF(cx - 7, cy - 3, 14, 6), 3.0, 3.0)

        else:  # idle
            # Quiet steady resting accent
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#475569")))
            painter.drawEllipse(QPointF(cx, cy), 2.5, 2.5)

    # -----------------------------------------------------------------------
    # 2. Docked Edge Line
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_edge_line(
        cls,
        painter: QPainter,
        bounds: QRectF,
        state: str,
        elapsed_ms: float,
        audio_level: float,
        reduced_motion: bool
    ) -> None:
        cx = bounds.center().x()
        cy = bounds.center().y()

        bar_w = 6.0 + (audio_level * 3.0 if state == "listening" else 0.0)
        bar_h = min(bounds.height() - 6.0, 48.0 + (audio_level * 14.0 if state == "listening" else 0.0))
        bx = cx - (bar_w / 2.0)
        by = cy - (bar_h / 2.0)

        if state == "listening":
            fill_col = QColor("#38BDF8")
        elif state == "processing":
            fill_col = QColor("#F59E0B")
        elif state == "confirmed":
            fill_col = QColor("#10B981")
        elif state in ("recovery", "unverified"):
            fill_col = QColor("#F59E0B")
        else:
            fill_col = QColor("#334155")

        painter.setPen(QPen(QColor(fill_col.red(), fill_col.green(), fill_col.blue(), 100), 1.0))
        painter.setBrush(QBrush(fill_col))
        painter.drawRoundedRect(QRectF(bx, by, bar_w, bar_h), bar_w / 2.0, bar_w / 2.0)

    # -----------------------------------------------------------------------
    # 3. Pilot: Original Pixel Courier Robot
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_pilot(
        cls,
        painter: QPainter,
        cx: float,
        cy: float,
        state: str,
        elapsed_ms: float,
        audio_level: float,
        palette_name: str,
        reduced_motion: bool,
        device_pixel_ratio: float
    ) -> None:
        """
        Renders the original FlowPilot Pilot robot character with integer pixel snapping.
        """
        # Determine pose based on canonical state and elapsed time
        if state == "listening":
            grid = PILOT_LISTEN
        elif state == "processing":
            grid = PILOT_WORKING
        elif state == "confirmed":
            grid = PILOT_CONFIRMED
        elif state in ("recovery", "unverified"):
            grid = PILOT_RECOVERY
        else:  # idle
            # Resting pose with occasional blink
            if not reduced_motion:
                # Blink for 180ms every 3.5 seconds
                cycle = int(elapsed_ms) % 3500
                grid = PILOT_BLINK if cycle < 180 else PILOT_REST
            else:
                grid = PILOT_REST

        pal = PILOT_PALETTES.get(palette_name, PILOT_PALETTES["default"])
        grid_w = len(grid[0])
        grid_h = len(grid)
        scale = 2  # Each pixel cell is 2x2 px

        total_w = grid_w * scale
        total_h = grid_h * scale

        # Device-pixel snapping: align top-left to exact integer pixels
        start_x = int(math.floor(cx - (total_w / 2.0)))
        start_y = int(math.floor(cy - (total_h / 2.0)))

        # Render matrix cells
        painter.setPen(Qt.NoPen)
        for gy, row in enumerate(grid):
            for gx, ch in enumerate(row):
                if ch == ".":
                    continue
                color_hex = pal.get(ch)
                if not color_hex:
                    continue
                col = QColor(color_hex)
                # Dynamic antenna light modulation during listening
                if ch == "L" and state == "listening" and not reduced_motion:
                    pulse = 0.5 + 0.5 * math.sin(elapsed_ms * 0.012)
                    col = QColor(col.red(), col.green(), col.blue(), int(150 + 105 * pulse))
                painter.fillRect(start_x + (gx * scale), start_y + (gy * scale), scale, scale, col)

    # -----------------------------------------------------------------------
    # 3b. Seedling: Sleepy Seed Creature (Concept 2)
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_seedling(
        cls,
        painter: QPainter,
        cx: float,
        cy: float,
        state: str,
        elapsed_ms: float,
        audio_level: float,
        palette_name: str,
        reduced_motion: bool,
        device_pixel_ratio: float
    ) -> None:
        if state == "listening":
            grid = SEED_LISTEN
        elif state == "processing":
            grid = SEED_WORKING
        elif state == "confirmed":
            grid = SEED_CONFIRMED
        elif state in ("recovery", "unverified"):
            grid = SEED_RECOVERY
        else:
            grid = SEED_REST

        pal = SEED_PALETTES.get(palette_name, SEED_PALETTES["default"])
        grid_w = len(grid[0])
        grid_h = len(grid)
        scale = 2

        total_w = grid_w * scale
        total_h = grid_h * scale
        start_x = int(math.floor(cx - (total_w / 2.0)))
        start_y = int(math.floor(cy - (total_h / 2.0)))

        painter.setPen(Qt.NoPen)
        for gy, row in enumerate(grid):
            for gx, ch in enumerate(row):
                if ch == ".":
                    continue
                color_hex = pal.get(ch)
                if not color_hex:
                    continue
                col = QColor(color_hex)
                painter.fillRect(start_x + (gx * scale), start_y + (gy * scale), scale, scale, col)

    # -----------------------------------------------------------------------
    # 3c. Nimbus: Vapor Cloud Sprite (Concept 3)
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_nimbus(
        cls,
        painter: QPainter,
        cx: float,
        cy: float,
        state: str,
        elapsed_ms: float,
        audio_level: float,
        palette_name: str,
        reduced_motion: bool,
        device_pixel_ratio: float
    ) -> None:
        if state == "listening":
            grid = NIMBUS_LISTEN
        elif state == "processing":
            grid = NIMBUS_WORKING
        elif state == "confirmed":
            grid = NIMBUS_CONFIRMED
        elif state in ("recovery", "unverified"):
            grid = NIMBUS_RECOVERY
        else:
            grid = NIMBUS_REST

        pal = NIMBUS_PALETTES.get(palette_name, NIMBUS_PALETTES["default"])
        grid_w = len(grid[0])
        grid_h = len(grid)
        scale = 2

        total_w = grid_w * scale
        total_h = grid_h * scale
        start_x = int(math.floor(cx - (total_w / 2.0)))
        start_y = int(math.floor(cy - (total_h / 2.0)))

        painter.setPen(Qt.NoPen)
        for gy, row in enumerate(grid):
            for gx, ch in enumerate(row):
                if ch == ".":
                    continue
                color_hex = pal.get(ch)
                if not color_hex:
                    continue
                col = QColor(color_hex)
                # Subtle internal core glow during voice capture
                if ch in ("C", "P") and state == "listening" and not reduced_motion:
                    pulse = 0.5 + 0.5 * math.sin(elapsed_ms * 0.01)
                    col = QColor(col.red(), col.green(), col.blue(), int(160 + 95 * pulse))
                painter.fillRect(start_x + (gx * scale), start_y + (gy * scale), scale, scale, col)

    # -----------------------------------------------------------------------
    # 3d. Kiki: The Little Scarf Courier (Original Anime-Inspired Companion)
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_kiki(
        cls,
        painter: QPainter,
        cx: float,
        cy: float,
        state: str,
        elapsed_ms: float,
        audio_level: float,
        palette_name: str,
        reduced_motion: bool,
        device_pixel_ratio: float
    ) -> None:
        """
        Renders Kiki the Little Scarf Courier with integer pixel snapping.
        - Idle: Restrained, quiet pose; occasional scarf adjust or blink (never endless bouncing).
        - Listening: Attentive pose with reactive scarf flutter.
        - Processing: Cradles letter envelope close, inspecting seal.
        - Confirmed: Single-shot delivery bow with emerald wax seal.
        - Unverified: Neutral forward peer (honest pause).
        - Recovery: Sympathetic address check with amber question mark.
        """
        if state == "listening":
            grid = KIKI_LISTEN
        elif state == "processing":
            grid = KIKI_PROCESS
        elif state == "confirmed":
            grid = KIKI_CONFIRMED if reduced_motion or elapsed_ms < 1200 else KIKI_REST
        elif state == "unverified":
            grid = KIKI_UNVERIFIED
        elif state == "recovery":
            grid = KIKI_RECOVERY
        else:  # idle
            if not reduced_motion:
                cycle = int(elapsed_ms) % 3500
                if cycle < 180:
                    grid = KIKI_BLINK
                elif 2600 <= cycle < 3100:
                    grid = KIKI_SCARF
                else:
                    grid = KIKI_REST
            else:
                grid = KIKI_REST

        pal = KIKI_PALETTES.get(palette_name, KIKI_PALETTES["default"])
        grid_w = len(grid[0])
        grid_h = len(grid)
        dpr = max(1.0, device_pixel_ratio)
        scale = max(1, round(2 * dpr)) / dpr

        total_w = grid_w * scale
        total_h = grid_h * scale
        start_x = round((cx - total_w / 2.0) * dpr) / dpr
        start_y = round((cy - total_h / 2.0) * dpr) / dpr

        painter.setPen(Qt.NoPen)
        for gy, row in enumerate(grid):
            for gx, ch in enumerate(row):
                if ch == ".":
                    continue
                color_hex = pal.get(ch)
                if not color_hex:
                    continue
                col = QColor(color_hex)
                # Dynamic audio-reactive glow on gold badge / scarf tip during listening
                if ch == "G" and state == "listening" and not reduced_motion:
                    pulse = max(0.0, min(1.0, audio_level))
                    col = QColor(col.red(), col.green(), col.blue(), int(170 + 85 * pulse))
                painter.fillRect(QRectF(start_x + gx * scale, start_y + gy * scale, scale, scale), col)

    # -----------------------------------------------------------------------
    # 4. SondeR-Cat Pixel Kitty
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_kitty(
        cls,
        painter: QPainter,
        cx: float,
        cy: float,
        state: str,
        elapsed_ms: float,
        audio_level: float,
        palette_name: str,
        reduced_motion: bool
    ) -> None:
        if not ps:
            cls._draw_fallback_glyph(painter, cx, cy, "🐾")
            return

        if reduced_motion:
            # Strictly static sitting pose under reduced motion
            frame = "sit_a"
        else:
            if state == "listening":
                step = int(elapsed_ms / 140.0) % 4
                frame = ["type_a", "type_b", "knead_a", "knead_b"][step]
            elif state == "processing":
                frame = "sit_b"
            elif state == "confirmed":
                frame = "stretch"
            elif state in ("recovery", "unverified"):
                frame = "sit_a"
            else:
                # Idle: periodic tail flick
                cycle = int(elapsed_ms) % 4000
                frame = "sit_b" if cycle < 300 else "sit_a"

        pal = palette_name if palette_name in ps.PALETTES else "orange tabby"
        pix = ps.render_kitty_pixmap(frame, palette_name=pal, scale=2)
        if pix and not pix.isNull():
            w = pix.width()
            h = pix.height()
            x = int(math.floor(cx - (w / 2.0)))
            y = int(math.floor(cy - (h / 2.0)))
            painter.drawPixmap(x, y, pix)
        else:
            cls._draw_fallback_glyph(painter, cx, cy, "🐾")

    # -----------------------------------------------------------------------
    # 5. Pixel Dog / Pup
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_dog(
        cls,
        painter: QPainter,
        cx: float,
        cy: float,
        state: str,
        palette_name: str,
        reduced_motion: bool
    ) -> None:
        if not ps:
            cls._draw_fallback_glyph(painter, cx, cy, "🐶")
            return

        frame = "dog_sit_b" if state in ("listening", "confirmed") and not reduced_motion else "dog_sit_a"
        pal = palette_name if palette_name in ("shiba inu", "golden retriever", "corgi", "husky") else "shiba inu"
        pix = ps.render_pup_pixmap(frame, palette_name=pal, scale=2)
        if pix and not pix.isNull():
            w = pix.width()
            h = pix.height()
            x = int(math.floor(cx - (w / 2.0)))
            y = int(math.floor(cy - (h / 2.0)))
            painter.drawPixmap(x, y, pix)
        else:
            cls._draw_fallback_glyph(painter, cx, cy, "🐶")

    # -----------------------------------------------------------------------
    # 6. Retro Companions
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_retro(
        cls,
        painter: QPainter,
        cx: float,
        cy: float,
        comp_name: str,
        state: str,
        reduced_motion: bool
    ) -> None:
        if not ps:
            cls._draw_fallback_glyph(painter, cx, cy, comp_name.capitalize())
            return

        frame = "wag" if state in ("listening", "confirmed") and not reduced_motion else "idle"
        pix = ps.render_retro_companion_pixmap(comp_name, frame=frame, scale=2)
        if pix and not pix.isNull():
            w = pix.width()
            h = pix.height()
            x = int(math.floor(cx - (w / 2.0)))
            y = int(math.floor(cy - (h / 2.0)))
            painter.drawPixmap(x, y, pix)
        else:
            cls._draw_fallback_glyph(painter, cx, cy, comp_name.capitalize())

    # -----------------------------------------------------------------------
    # 7. Custom Data / Emoji
    # -----------------------------------------------------------------------
    @classmethod
    def _draw_custom(
        cls,
        painter: QPainter,
        bounds: QRectF,
        custom_data: Dict[str, Any],
        state: str,
        elapsed_ms: float,
        audio_level: float,
        reduced_motion: bool
    ) -> None:
        cx = bounds.center().x()
        cy = bounds.center().y()
        c_type = custom_data.get("type", "emoji")

        if c_type == "emoji":
            emoji_char = custom_data.get("emoji", "🤖")
            font = QFont("Segoe UI Emoji", 26)
            painter.setFont(font)
            painter.setPen(QColor("#F8FAFC"))
            painter.drawText(bounds, Qt.AlignCenter, emoji_char)
        elif c_type in ("image", "spritesheet"):
            comp_dir = custom_data.get("directory")
            frames = custom_data.get("frames", [])
            if frames and isinstance(frames, list) and len(frames) > 0:
                if reduced_motion:
                    # Strict reduced motion invariant: freeze on rest frame 0
                    frame_idx = 0
                elif state in ("pasted", "success", "confirmed"):
                    frame_idx = min(len(frames) - 1, 2)
                elif state in ("listening", "recording"):
                    listen_count = max(1, min(2, len(frames) - 1))
                    frame_idx = int((elapsed_ms / 250.0)) % (listen_count + 1)
                    if frame_idx >= 2 and len(frames) >= 3:
                        frame_idx = 1
                else:
                    frame_idx = 0
                img_name = frames[frame_idx]
            else:
                img_name = custom_data.get("image_file", "sprite.png")

            if comp_dir:
                from pathlib import Path
                img_path = Path(comp_dir) / img_name
                if img_path.exists():
                    pix = QPixmap(str(img_path))
                    if not pix.isNull():
                        scaled = pix.scaled(int(bounds.width()), int(bounds.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        painter.drawPixmap(int(cx - scaled.width() / 2), int(cy - scaled.height() / 2), scaled)
                        return

            cls._draw_fallback_glyph(painter, cx, cy, "🤖")
        else:
            cls._draw_fallback_glyph(painter, cx, cy, "🤖")

    @classmethod
    def _draw_fallback_glyph(cls, painter: QPainter, cx: float, cy: float, glyph: str) -> None:
        font = QFont("Segoe UI Emoji", 22)
        painter.setFont(font)
        painter.setPen(QColor("#E2E8F0"))
        painter.drawText(QRectF(cx - 24, cy - 24, 48, 48), Qt.AlignCenter, glyph)
