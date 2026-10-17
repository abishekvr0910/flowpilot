"""
Unit tests for Pokemon Pixel Companions and Interactive Pixel Art Creator
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

import ui.pet_sprites as ps
from engine.companion_assets import BUILTIN_COMPANIONS, CompanionAssetManager
from ui.pixel_creator import PixelCanvasWidget, PixelAnimationPreview, PixelCreatorWidget

class TestPokemonAndPixelCreator(unittest.TestCase):
    def test_builtin_companions_include_pokemon_and_pup(self):
        comp_ids = [c["id"] for c in BUILTIN_COMPANIONS]
        self.assertIn("dog", comp_ids)
        self.assertIn("kitty", comp_ids)
        self.assertIn("pikachu", comp_ids)
        self.assertIn("charmander", comp_ids)
        self.assertIn("gengar", comp_ids)
        self.assertIn("eevee", comp_ids)

    def test_pokemon_palettes_exist(self):
        for pkmn in ("pikachu", "charmander", "gengar", "eevee"):
            self.assertIn(pkmn, ps.PALETTES)
            pal = ps.PALETTES[pkmn]
            self.assertIn("B", pal)
            self.assertIn("K", pal)
            self.assertIn("E", pal)

    def test_pokemon_pixmaps_render(self):
        for pkmn in ("pikachu", "charmander", "gengar", "eevee"):
            idle_pix = ps.render_pokemon_pixmap(pkmn, frame="idle", scale=2)
            self.assertFalse(idle_pix.isNull())
            self.assertEqual(idle_pix.width(), 52)
            self.assertEqual(idle_pix.height(), 56)

            action_pix = ps.render_pokemon_pixmap(pkmn, frame="wag", scale=2)
            self.assertFalse(action_pix.isNull())
            self.assertEqual(action_pix.width(), 52)
            self.assertEqual(action_pix.height(), 56)

    def test_pup_pixmap_renders(self):
        pup_pix = ps.render_pup_pixmap(frame="dog_sit_a", palette_name="shiba inu", scale=2)
        self.assertFalse(pup_pix.isNull())
        self.assertEqual(pup_pix.width(), 52)
        self.assertEqual(pup_pix.height(), 56)

    def test_pixel_canvas_painting_and_flipping(self):
        canvas = PixelCanvasWidget()
        self.assertEqual(len(canvas.get_grid()), 16)
        self.assertEqual(len(canvas.get_grid()[0]), 16)

        # Set pixel
        canvas.set_color("#FACC15")
        canvas._paint_at_pos(18, 18)  # Cell (1, 1)
        grid = canvas.get_grid()
        self.assertEqual(grid[1][1], "#FACC15")

        # Flip horizontal
        canvas.flip_horizontal()
        grid_flipped = canvas.get_grid()
        self.assertEqual(grid_flipped[1][14], "#FACC15")
        self.assertIsNone(grid_flipped[1][1])

        # Clear
        canvas.clear()
        self.assertIsNone(canvas.get_grid()[1][14])

    def test_pixel_creator_template_loading(self):
        creator = PixelCreatorWidget()
        creator._load_template("⚡ Pikachu")
        self.assertIn("Pikachu", creator.txt_name.text())
        grid = creator.canvas.get_grid()
        # Head of Pikachu should be yellow
        self.assertEqual(grid[5][5], "#FACC15")

        # Load Charmander
        creator._load_template("🔥 Charmander")
        self.assertIn("Charmander", creator.txt_name.text())
        c_grid = creator.canvas.get_grid()
        self.assertEqual(c_grid[5][5], "#FB923C")

if __name__ == "__main__":
    unittest.main()
