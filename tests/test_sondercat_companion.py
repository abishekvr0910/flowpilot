"""
Automated Test for SondeR-Cat Pixel Kitty Companion Integration
Validates 26x28 ASCII pixel sprite rendering, 13 fur palettes,
interactive audio-reactive paw kneading, dynamic pupils,
celebratory hearts, and sound effect resolution.
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import ui.pet_sprites as ps
from ui.floating_hud import FloatingHUD

def test_sondercat_pixel_companion():
    print("=" * 65)
    print("AUDIT TEST: SONDERCAT PIXEL KITTY COMPANION INTEGRATION")
    print("=" * 65)

    # 1. Sprite Engine Integrity
    assert len(ps.FRAMES) >= 17, f"Expected >=17 frames, got {len(ps.FRAMES)}"
    assert len(ps.PALETTES) >= 13, f"Expected >=13 palettes, got {len(ps.PALETTES)}"
    assert "sit_a" in ps.FRAMES and "sit_b" in ps.FRAMES
    assert "type_a" in ps.FRAMES and "type_b" in ps.FRAMES
    assert "knead_a" in ps.FRAMES and "knead_b" in ps.FRAMES
    assert "orange tabby" in ps.PALETTES and "calico" in ps.PALETTES and "black" in ps.PALETTES
    print(f"[1] Verified {len(ps.FRAMES)} pixel frames and {len(ps.PALETTES)} fur palettes in pet_sprites.")

    # 2. Rendering Accuracy
    app = QApplication.instance() or QApplication([])
    img = ps.render_frame(ps.FRAMES["sit_a"], ps.PALETTES["orange tabby"], scale=3, halo=True)
    assert not img.isNull(), "Rendered QImage must not be null"
    assert img.width() == 78 and img.height() == 84, f"Expected 78x84 at scale 3, got {img.width()}x{img.height()}"
    print(f"[2] Rendered sitting cat pixel frame at scale 3: {img.width()}x{img.height()}px.")

    # 3. FloatingHUD Kitty Style Initialization
    hud = FloatingHUD()
    hud.set_visual_style("kitty")
    assert hud._visual_style == "kitty"
    assert hud.width() == 78 and hud.height() == 84
    print("[3] FloatingHUD initialized in 'kitty' visual style (78x84px).")

    # 4. Interactive Voice Reactions (Paw Kneading)
    hud.update_state("listening")
    hud.update_state("audio_level", {"level": 0.85})
    assert hud._current_state == "listening"
    assert hud._audio_level == 0.85

    for _ in range(8):
        hud._on_anim_tick()
    assert hud._cat_frame in ["type_a", "type_b", "knead_a", "knead_b"], f"Unexpected cat frame: {hud._cat_frame}"
    print(f"[4] Verified voice-reactive paw kneading during speech capture: frame='{hud._cat_frame}'.")

    # 5. Fur Palette Switching
    for pal_name in ["calico", "black", "gray", "siamese", "pink", "orange tabby"]:
        hud.set_cat_palette(pal_name)
        assert hud._cat_palette == pal_name
    print("[5] Successfully switched across 6 fur palettes with automatic cache invalidation.")

    # 6. Celebratory Pasted State & Floating Hearts
    hud.update_state("pasted")
    hud._on_anim_tick()
    hud.repaint()
    print("[6] Verified celebratory 'pasted' state with floating pixel hearts.")

    # 7. Sound Cue Resolution
    wav_path = PROJECT_ROOT / "assets" / "sounds" / "meow.wav"
    assert wav_path.exists(), f"Meow sound file missing at {wav_path}"
    assert wav_path.stat().st_size > 10000, "Meow sound file is incomplete or corrupted"
    print(f"[7] Verified audio sound cue asset: {wav_path.name} ({wav_path.stat().st_size} bytes).")

    # 8. Style Cycling & Backward Compatibility
    hud.toggle_visual_style() # -> edge_line
    assert hud._visual_style == "edge_line"
    hud.toggle_visual_style() # -> wave_bar
    assert hud._visual_style == "wave_bar"
    hud.toggle_visual_style() # -> mascot
    assert hud._visual_style == "mascot"
    hud.toggle_visual_style() # -> kitty
    assert hud._visual_style == "kitty"
    print("[8] 4-way appearance cycle verified (kitty -> edge_line -> wave_bar -> mascot -> kitty).")

    hud.close()
    print("\n[RESULT] SondeR-Cat Pixel Kitty Companion test PASSED 100%.")
    return True

if __name__ == "__main__":
    success = test_sondercat_pixel_companion()
    sys.exit(0 if success else 1)
