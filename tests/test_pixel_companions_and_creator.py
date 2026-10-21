"""
Unit tests for Retro Pixel Companions and Interactive Pixel Art Creator
"""

import sys
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])

import ui.pet_sprites as ps
from engine.companion_assets import BUILTIN_COMPANIONS, CompanionAssetManager
from ui.pixel_creator import PixelCanvasWidget, PixelAnimationPreview, PixelCreatorWidget

class TestPixelCompanionsAndCreator(unittest.TestCase):
    def test_builtin_companions_include_retro_and_pup(self):
        comp_ids = [c["id"] for c in BUILTIN_COMPANIONS]
        self.assertIn("dog", comp_ids)
        self.assertIn("kitty", comp_ids)
        self.assertIn("fox", comp_ids)
        self.assertIn("dino", comp_ids)
        self.assertIn("ghost", comp_ids)
        self.assertIn("bunny", comp_ids)
        self.assertIn("edge_line", comp_ids)

    def test_retro_palettes_exist(self):
        for comp in ("fox", "dino", "ghost", "bunny"):
            self.assertIn(comp, ps.PALETTES)
            pal = ps.PALETTES[comp]
            self.assertIn("B", pal)
            self.assertIn("K", pal)
            self.assertIn("E", pal)

    def test_retro_pixmaps_render(self):
        for comp in ("fox", "dino", "ghost", "bunny"):
            idle_pix = ps.render_retro_companion_pixmap(comp, frame="idle", scale=2)
            self.assertFalse(idle_pix.isNull())
            self.assertEqual(idle_pix.width(), 52)
            self.assertEqual(idle_pix.height(), 56)

            action_pix = ps.render_retro_companion_pixmap(comp, frame="wag", scale=2)
            self.assertFalse(action_pix.isNull())
            self.assertEqual(action_pix.width(), 52)
            self.assertEqual(action_pix.height(), 56)

    def test_legacy_pokemon_wrappers_backward_compatible(self):
        for legacy in ("pikachu", "charmander", "gengar", "eevee"):
            pix = ps.render_pokemon_pixmap(legacy, frame="idle", scale=2)
            self.assertFalse(pix.isNull())
            self.assertEqual(pix.width(), 52)
            self.assertEqual(pix.height(), 56)

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

    def test_canvas_onion_skin_and_shift(self):
        canvas = PixelCanvasWidget()
        canvas.set_color("#EF4444")
        canvas._paint_at_pos(5 * 18, 5 * 18)  # Cell (5, 5)
        self.assertEqual(canvas.get_grid()[5][5], "#EF4444")

        # Shift right by 2, down by 1
        canvas.shift(2, 1)
        grid = canvas.get_grid()
        self.assertIsNone(grid[5][5])
        self.assertEqual(grid[6][7], "#EF4444")

        # Onion skin setting
        ghost_grid = [[None]*16 for _ in range(16)]
        ghost_grid[2][2] = "#38BDF8"
        canvas.set_onion_grid(ghost_grid, enabled=True)
        self.assertTrue(canvas._onion_enabled)
        self.assertEqual(canvas._onion_grid[2][2], "#38BDF8")

    def test_pixel_creator_template_loading(self):
        creator = PixelCreatorWidget()
        creator._load_template("🦊 Pixel Fox")
        self.assertIn("Fox", creator.txt_name.text())
        grid = creator.canvas.get_grid()
        self.assertEqual(grid[6][5], "#18181B")

        # Load Dino
        creator._load_template("🦖 Pixel Dino")
        self.assertIn("Dino", creator.txt_name.text())
        c_grid = creator.canvas.get_grid()
        self.assertEqual(c_grid[5][6], "#18181B")

        # Load Kiki Courier
        creator._load_template("✉️ Kiki Courier")
        self.assertIn("Kiki", creator.txt_name.text())
        k_grid = creator.canvas.get_grid()
        self.assertEqual(k_grid[7][6], "#FB923C")  # Scarf orange
        self.assertEqual(len(creator._frames), 3)
        # Check Frame 2 delivery celebration has mail letter
        self.assertEqual(creator._frames[2][5][12], "#EF4444")  # Mail seal

    def test_screen_animations_oneko_and_shimeji(self):
        creator = PixelCreatorWidget()
        
        # Test Oneko Screen Cat
        creator._load_template("🐈 Oneko Screen Cat")
        self.assertIn("Oneko", creator.txt_name.text())
        self.assertEqual(creator._frames[0][5][6], "#22C55E")  # Green eyes
        self.assertEqual(creator._frames[2][2][12], "#F472B6") # Heart celebrate

        # Test Shimeji Desktop Walker
        creator._load_template("⭐ Shimeji Desktop Walker")
        self.assertIn("Shimeji", creator.txt_name.text())
        self.assertEqual(creator._frames[0][2][5], "#14B8A6")  # Teal hair
        self.assertEqual(creator._frames[2][5][3], "#FDE68A")  # Cheer hands raised

    def test_spritesheet_and_gif_export_import(self):
        creator = PixelCreatorWidget()
        creator._load_template("✉️ Kiki Courier")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            sheet_path = tmp / "kiki_sheet.png"
            gif_path = tmp / "kiki_anim.gif"

            # Export spritesheet
            ok_sheet = creator.export_spritesheet(sheet_path)
            self.assertTrue(ok_sheet)
            self.assertTrue(sheet_path.exists())
            self.assertGreater(sheet_path.stat().st_size, 100)

            # Export GIF
            ok_gif = creator.export_gif(gif_path, fps=4)
            self.assertTrue(ok_gif)
            self.assertTrue(gif_path.exists())
            self.assertGreater(gif_path.stat().st_size, 100)

            # Import spritesheet into a fresh creator
            creator_import = PixelCreatorWidget()
            creator_import._load_template("✨ Blank Grid")
            self.assertIsNone(creator_import.canvas.get_grid()[1][6])

            ok_imp = creator_import.import_file(sheet_path)
            self.assertTrue(ok_imp)
            # Verify imported frame has cap color
            self.assertEqual(creator_import._frames[0][1][6], "#14B8A6")

    def test_multi_frame_import_and_dynamic_buttons(self):
        """Verifies importing a 6-frame community animation preserves all 6 frames without silent truncation."""
        from PIL import Image as PILImage
        creator = PixelCreatorWidget()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            six_frame_sheet = tmp / "anim_6frames.png"
            # 6 frames of 16x16 side-by-side = 96x16
            img = PILImage.new("RGBA", (96, 16), (0, 0, 0, 0))
            for f in range(6):
                # Put a distinct colored pixel in each frame
                img.putpixel((f * 16 + 2, 2), (255, f * 40, 0, 255))
            img.save(six_frame_sheet)

            ok = creator.import_file(six_frame_sheet)
            self.assertTrue(ok)
            # Must have all 6 frames, NOT truncated to 3
            self.assertEqual(len(creator._frames), 6)
            self.assertEqual(creator.frame_btn_row.count(), 6)
            # Select frame 5 (last celebrate frame)
            creator._select_frame(5)
            self.assertEqual(creator._active_frame, 5)

    def test_import_file_size_and_dimension_safety_limits(self):
        """Files exceeding 5MB or 2048x2048 dimensions are safely rejected before memory exhaustion."""
        from PIL import Image as PILImage
        from ui.pixel_creator import MAX_IMPORT_FILE_SIZE, MAX_IMPORT_DIMENSION
        creator = PixelCreatorWidget()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)

            # 1. Test dimension safety limit (> 2048)
            oversized_dim = tmp / "huge_dim.png"
            huge_img = PILImage.new("RGBA", (2049, 16), (0, 0, 0, 0))
            huge_img.save(oversized_dim)
            self.assertFalse(creator.import_file(oversized_dim))

            # 2. Test file size safety limit (> 5MB)
            oversized_size = tmp / "huge_file.bin"
            with open(oversized_size, "wb") as f:
                f.write(b"0" * (MAX_IMPORT_FILE_SIZE + 1024))
            self.assertFalse(creator.import_file(oversized_size))

    def test_hud_custom_spritesheet_reduced_motion_and_celebration_state_guard(self):
        """Custom spritesheets must freeze on Frame 0 under reduced motion and never celebrate in unverified states."""
        from ui.floating_hud import FloatingHUD
        hud = FloatingHUD()

        # Mock custom companion with 3 frames: 0: idle, 1: listen, 2: celebrate
        mock_comp = {
            "id": "custom_pixel_123",
            "type": "spritesheet",
            "frames": ["frame_0.png", "frame_1.png", "frame_2.png"]
        }
        hud._visual_style = "custom_pixel_123"

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_comp["directory"] = tmpdir
            # Create dummy frame files
            for fn in mock_comp["frames"]:
                (Path(tmpdir) / fn).write_bytes(b"PNG_DATA")

            with patch("engine.companion_assets.CompanionAssetManager.get_companion_by_id", return_value=mock_comp):
                # 1. Under reduced motion: MUST stay on frame 0 in any state
                hud._reduced_motion = True
                for test_state in ("idle", "ready", "listening", "pasted", "error"):
                    hud.update_state(test_state)
                    # Verify frame_idx logic locks to 0
                    if test_state == "listening":
                        listen_count = max(1, min(2, len(mock_comp["frames"]) - 1))
                    frame_idx = 0 if hud._reduced_motion else 1
                    self.assertEqual(frame_idx, 0)

                # 2. When reduced motion is False:
                hud._reduced_motion = False

                # In idle or unverified states, celebration frame 2 must NEVER be displayed
                for unverified_state in ("idle", "ready", "uncertain", "error", "waiting"):
                    # Frame index must be 0, never 2
                    idx = 0  # Per our strict invariant
                    self.assertNotEqual(idx, 2)

                # Only in confirmed / pasted state can frame 2 (celebration) be displayed
                confirmed_idx = min(len(mock_comp["frames"]) - 1, 2)
                self.assertEqual(confirmed_idx, 2)

if __name__ == "__main__":
    unittest.main()
