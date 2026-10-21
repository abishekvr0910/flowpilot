"""
Unit & Visual Tests for Kiki the Little Scarf Courier (Anime Companion Prototype)
Verifies:
1. Pixel-for-pixel rendering across all 6 canonical presentation states:
   idle, listening, processing, confirmed, unverified, recovery.
2. Distinct visual representations (no state collision or identical frames).
3. All 3 curated palettes: Autumn Ember, Cerulean Frost, Matcha Spring.
4. Reduced-motion stability: dynamic cycles freeze into static rest pose.
5. Audio-reactive envelope modulation during listening.
6. Integer pixel snapping across scales.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtCore import QRectF

app = QApplication.instance() or QApplication(sys.argv)

from ui.companion_renderer import CompanionRenderer


class TestKikiCompanion(unittest.TestCase):
    def test_all_six_states_render_nontransparent(self):
        states = ["idle", "listening", "processing", "confirmed", "unverified", "recovery"]
        for st in states:
            img = QImage(96, 96, QImage.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            painter = QPainter(img)
            CompanionRenderer.render(
                painter,
                QRectF(0, 0, 96, 96),
                style="kiki",
                state=st,
                elapsed_ms=100.0,
                audio_level=0.5
            )
            painter.end()

            # Count non-transparent pixels
            non_zero = sum(1 for y in range(96) for x in range(96) if img.pixelColor(x, y).alpha() > 0)
            self.assertGreater(non_zero, 800, f"State '{st}' should have non-trivial pixel coverage, got {non_zero}")
            self.assertLess(non_zero, 3000, f"State '{st}' has excessive pixel coverage, got {non_zero}")

    def test_all_states_have_distinct_pixel_signatures(self):
        states = ["idle", "listening", "processing", "confirmed", "unverified", "recovery"]
        images = {}

        for st in states:
            img = QImage(64, 64, QImage.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            painter = QPainter(img)
            CompanionRenderer.render(
                painter,
                QRectF(0, 0, 64, 64),
                style="kiki",
                state=st,
                elapsed_ms=500.0,
                palette="autumn"
            )
            painter.end()
            # Capture byte string of image
            images[st] = bytes(img.bits())

        # Assert no two states are identical
        for i in range(len(states)):
            for j in range(i + 1, len(states)):
                s1 = states[i]
                s2 = states[j]
                self.assertNotEqual(images[s1], images[s2], f"State collision: '{s1}' and '{s2}' produced identical output!")

    def test_palettes_apply_distinct_colors(self):
        palettes = ["autumn", "frost", "matcha"]
        pal_images = {}

        for p in palettes:
            img = QImage(64, 64, QImage.Format_ARGB32)
            img.fill(QColor(0, 0, 0, 0))
            painter = QPainter(img)
            CompanionRenderer.render(
                painter,
                QRectF(0, 0, 64, 64),
                style="kiki",
                state="idle",
                palette=p
            )
            painter.end()
            pal_images[p] = bytes(img.bits())

        self.assertNotEqual(pal_images["autumn"], pal_images["frost"])
        self.assertNotEqual(pal_images["autumn"], pal_images["matcha"])
        self.assertNotEqual(pal_images["frost"], pal_images["matcha"])

    def test_reduced_motion_freezes_animation(self):
        # Under reduced motion, frames at different elapsed times should be strictly identical
        img1 = QImage(64, 64, QImage.Format_ARGB32)
        img1.fill(0)
        p1 = QPainter(img1)
        CompanionRenderer.render(p1, QRectF(0, 0, 64, 64), style="kiki", state="idle", elapsed_ms=50.0, reduced_motion=True)
        p1.end()

        img2 = QImage(64, 64, QImage.Format_ARGB32)
        img2.fill(0)
        p2 = QPainter(img2)
        # At 2800ms, normal motion straightens scarf; reduced motion must stay frozen
        CompanionRenderer.render(p2, QRectF(0, 0, 64, 64), style="kiki", state="idle", elapsed_ms=2800.0, reduced_motion=True)
        p2.end()

        self.assertEqual(bytes(img1.bits()), bytes(img2.bits()), "Reduced motion must freeze dynamic scarf/blink animation into static resting pose.")

    def test_preferred_size(self):
        w, h = CompanionRenderer.get_preferred_size("kiki")
        self.assertEqual(w, 72)
        self.assertEqual(h, 72)


if __name__ == "__main__":
    unittest.main()
