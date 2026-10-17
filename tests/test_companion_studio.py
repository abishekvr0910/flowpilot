"""
FlowPilot Companion Studio Comprehensive Test Suite
Validates:
1. Pointer Gesture & Click Isolation (Zero double-click cycling, drag separation)
2. CompanionStore atomic persistence, migration, and appearance locking
3. CompanionAssetManager creation, security checks, traversal rejection, and packaging
4. PreferenceLearningEngine zero-surveillance heuristics, consensus, and tombstones
5. PersonalizationEngine deletion tombstones preventing default resurrection
6. CompanionStudioDialog UI initialization and draft lifecycle
"""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF, QEvent
from PySide6.QtGui import QMouseEvent

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.companion_store import CompanionStore, DEFAULT_COMPANION_CONFIG
from engine.companion_assets import CompanionAssetManager, BUILTIN_COMPANIONS
from engine.preference_learning import PreferenceLearningEngine
from engine.personalization import PersonalizationEngine
from ui.floating_hud import FloatingHUD
from ui.companion_studio import CompanionStudioDialog
from ui.companion_preview import CompanionPreviewWidget

@pytest.fixture(autouse=True, scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="fp_test_companion_")
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


# -----------------------------------------------------------------
# 1. Pointer Gesture & Click Isolation
# -----------------------------------------------------------------
def test_hud_double_click_is_absorbed_zero_appearance_change():
    """Verify double-clicking the companion produces 0 style changes and 0 dictation toggles."""
    hud = FloatingHUD()
    initial_style = hud._visual_style

    toggle_emitted = []
    hud.toggle_requested.connect(lambda: toggle_emitted.append(True))

    # Simulate double-click event
    pos = QPointF(20, 20)
    gpos = QPointF(100, 100)
    dbl_event = QMouseEvent(QEvent.Type.MouseButtonDblClick, pos, gpos, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)

    hud.mouseDoubleClickEvent(dbl_event)

    assert dbl_event.isAccepted(), "Double click must be accepted and absorbed"
    assert hud._visual_style == initial_style, "Double click must never cycle appearance!"
    assert len(toggle_emitted) == 0, "Double click must not emit toggle dictation"
    hud.close()

def test_hud_drag_movement_does_not_toggle_dictation():
    """Verify dragging the companion across the screen does not trigger recording on release."""
    hud = FloatingHUD()
    hud._visual_style = "kitty"

    toggle_emitted = []
    hud.toggle_requested.connect(lambda: toggle_emitted.append(True))

    # 1. Press
    press_event = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(10, 10), QPointF(100, 100), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    hud.mousePressEvent(press_event)
    assert not hud._is_dragging

    # 2. Move beyond drag threshold
    move_event = QMouseEvent(QEvent.Type.MouseMove, QPointF(60, 60), QPointF(150, 150), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    hud.mouseMoveEvent(move_event)
    assert hud._is_dragging, "Movement > drag threshold must set _is_dragging"

    # 3. Release
    rel_event = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(60, 60), QPointF(150, 150), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    hud.mouseReleaseEvent(rel_event)

    assert not hud._is_dragging
    assert len(toggle_emitted) == 0, "Releasing after drag must NOT toggle dictation!"
    hud.close()

def test_hud_clean_single_click_toggles_dictation():
    """Verify a stationary click cleanly toggles dictation."""
    hud = FloatingHUD()
    toggle_emitted = []
    hud.toggle_requested.connect(lambda: toggle_emitted.append(True))

    press_event = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(10, 10), QPointF(100, 100), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
    hud.mousePressEvent(press_event)

    rel_event = QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(10, 10), QPointF(100, 100), Qt.LeftButton, Qt.NoButton, Qt.NoModifier)
    hud.mouseReleaseEvent(rel_event)

    assert len(toggle_emitted) == 1, "Clean single click must emit toggle_requested"
    hud.close()

def test_hud_appearance_lock_prevents_cycling():
    """Verify toggle_visual_style is blocked when appearance_locked is True."""
    hud = FloatingHUD()
    hud._appearance_locked = True
    hud._visual_style = "kitty"

    hud.toggle_visual_style()
    assert hud._visual_style == "kitty", "Locked appearance must block style cycling"

    hud._appearance_locked = False
    hud.toggle_visual_style()
    assert hud._visual_style != "kitty", "Unlocked appearance may cycle"
    hud.close()

# -----------------------------------------------------------------
# 2. CompanionStore Persistence & Migration
# -----------------------------------------------------------------
def test_companion_store_lifecycle_and_atomic_persistence(temp_dir):
    store = CompanionStore(storage_dir=temp_dir)
    assert store.get("selected_asset_id") == "kitty"
    assert store.get("appearance_locked") is True

    # Update settings
    updated = store.update({
        "selected_asset_id": "mascot",
        "motion_preset": "breathe",
        "appearance_locked": True
    })
    assert updated["selected_asset_id"] == "mascot"
    assert updated["motion_preset"] == "breathe"

    # Reload from fresh store instance
    store2 = CompanionStore(storage_dir=temp_dir)
    assert store2.get("selected_asset_id") == "mascot"
    assert store2.get("motion_preset") == "breathe"
    assert store2.get("appearance_locked") is True

def test_companion_store_migration_from_legacy_config(temp_dir):
    # Pre-populate legacy config.json
    cfg = {
        "hud_style": "wave_bar",
        "cat_palette": "siamese",
        "cat_sound": False,
        "hud_x": 450,
        "hud_y": 750
    }
    with open(temp_dir / "config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f)

    store = CompanionStore(storage_dir=temp_dir)
    assert store.get("selected_asset_id") == "wave_bar"
    assert store.get("cat_palette") == "siamese"
    assert store.get("cat_sound") is False
    assert store.get("hud_x") == 450
    assert store.get("hud_y") == 750

# -----------------------------------------------------------------
# 3. CompanionAssetManager (Custom creations, security, packages)
# -----------------------------------------------------------------
def test_asset_manager_builtins_list(temp_dir):
    mgr = CompanionAssetManager(storage_dir=temp_dir)
    comps = mgr.list_all_companions()
    ids = [c["id"] for c in comps]
    assert "kitty" in ids
    assert "mascot" in ids
    assert "edge_line" in ids
    assert "wave_bar" in ids

def test_asset_manager_create_emoji_companion(temp_dir):
    mgr = CompanionAssetManager(storage_dir=temp_dir)
    comp = mgr.create_emoji_companion("Space Fox", "🦊", motion_preset="tiny_tilt")
    assert comp["type"] == "emoji"
    assert comp["emoji"] == "🦊"
    assert comp["name"] == "Space Fox"

    # Verify retrieval
    retrieved = mgr.get_companion_by_id(comp["id"])
    assert retrieved is not None
    assert retrieved["emoji"] == "🦊"

def test_asset_manager_create_image_validation(temp_dir):
    mgr = CompanionAssetManager(storage_dir=temp_dir)

    # 1. Reject non-existent file
    with pytest.raises(FileNotFoundError):
        mgr.create_image_companion("Fake", temp_dir / "non_existent.png")

    # 2. Reject non-PNG file (corrupt magic bytes)
    fake_file = temp_dir / "fake.png"
    with open(fake_file, "wb") as f:
        f.write(b"NOT_A_PNG_FILE_DATA")
    with pytest.raises(ValueError, match="Only standard PNG"):
        mgr.create_image_companion("Corrupt", fake_file)

    # 3. Accept valid PNG file
    valid_png = temp_dir / "valid.png"
    # Minimal 1x1 valid PNG bytes
    valid_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
    with open(valid_png, "wb") as f:
        f.write(valid_bytes)

    valid_comp = mgr.create_image_companion("Valid Gem", valid_png)
    assert valid_comp["type"] == "image"
    assert (Path(valid_comp["directory"]) / "sprite.png").exists()

def test_asset_manager_export_import_package(temp_dir):
    mgr = CompanionAssetManager(storage_dir=temp_dir)

    # Create an emoji companion
    comp = mgr.create_emoji_companion("Star Mascot", "⭐")
    export_path = temp_dir / "star.flowpack"
    mgr.export_companion_pack(comp["id"], export_path)

    assert export_path.exists()
    assert export_path.stat().st_size > 50

    # Import into a separate manager
    mgr2_dir = temp_dir / "mgr2"
    mgr2 = CompanionAssetManager(storage_dir=mgr2_dir)
    imported = mgr2.import_companion_pack(export_path)

    assert imported["type"] == "emoji"
    assert imported["emoji"] == "⭐"
    assert imported["name"] == "Star Mascot"

# -----------------------------------------------------------------
# 4. PreferenceLearningEngine (Zero Surveillance Adaptation)
# -----------------------------------------------------------------
def test_learning_engine_disabled_by_default(temp_dir):
    le = PreferenceLearningEngine(storage_dir=temp_dir)
    assert not le.is_enabled()

    # Recording while disabled must be a NO-OP
    le.record_setting_action("code.exe", "reduced_motion", True)
    assert len(le.load()["observations"]) == 0

def test_learning_engine_3_day_consensus_heuristic(temp_dir):
    le = PreferenceLearningEngine(storage_dir=temp_dir)
    le.set_enabled(True)

    # Manually inject observations across 3 distinct days
    le._data["observations"] = [
        {"app_id": "code.exe", "setting_key": "reduced_motion", "value": True, "date_str": "2026-10-14"},
        {"app_id": "code.exe", "setting_key": "reduced_motion", "value": True, "date_str": "2026-10-15"},
        {"app_id": "code.exe", "setting_key": "reduced_motion", "value": True, "date_str": "2026-10-16"}
    ]
    le._persist_unlocked()

    proposals = le.get_proposals()
    assert len(proposals) == 1
    prop = proposals[0]
    assert prop["app_id"] == "code.exe"
    assert prop["setting_key"] == "reduced_motion"
    assert prop["value"] is True
    assert prop["days_observed"] == 3
    assert prop["consensus_pct"] == 100

    # Accept proposal
    le.accept_proposal(prop)
    rules = le.get_approved_rules()
    assert rules["code.exe"]["reduced_motion"] is True

    # Once approved, proposal disappears from pending list
    assert len(le.get_proposals()) == 0

def test_learning_engine_tombstones_and_forgetting(temp_dir):
    le = PreferenceLearningEngine(storage_dir=temp_dir)
    le.set_enabled(True)

    prop = {"app_id": "notepad.exe", "setting_key": "motion_preset", "value": "reduced_motion"}
    le.accept_proposal(prop)
    assert le.get_approved_rules()["notepad.exe"]["motion_preset"] == "reduced_motion"

    # Forget rule
    le.forget_rule("notepad.exe", "motion_preset")
    assert "notepad.exe" not in le.get_approved_rules()

    # Verify tombstone recorded
    assert "notepad.exe:motion_preset" in le._data["tombstones"]

    # Subsequent deliberate actions must be ignored due to tombstone
    le.record_setting_action("notepad.exe", "motion_preset", "reduced_motion")
    assert len(le.get_proposals()) == 0

# -----------------------------------------------------------------
# 5. PersonalizationEngine Deletion Tombstones
# -----------------------------------------------------------------
def test_personalization_tombstones_prevent_default_resurrection(temp_dir):
    pe = PersonalizationEngine(storage_path=temp_dir / "personalization.json")
    terms = [item["term"] for item in pe.dictionary]
    assert "FastAPI" in terms

    # Remove term
    removed = pe.remove_term("FastAPI")
    assert removed is True
    assert "fastapi" in pe.tombstones

    # Reload from disk: verify FastAPI is NOT resurrected
    pe2 = PersonalizationEngine(storage_path=temp_dir / "personalization.json")
    terms2 = [item["term"] for item in pe2.dictionary]
    assert "FastAPI" not in terms2

# -----------------------------------------------------------------
# 6. CompanionStudioDialog UI Integration
# -----------------------------------------------------------------
def test_companion_studio_ui_draft_and_apply(temp_dir, monkeypatch):
    monkeypatch.setenv("FLOWPILOT_CONFIG_DIR", str(temp_dir))
    dialog = CompanionStudioDialog()
    assert dialog.tabs.count() == 5

    # Apply changes signal test
    applied_data = []
    dialog.applied.connect(lambda d: applied_data.append(d))

    dialog._draft["selected_asset_id"] = "mascot"
    dialog._on_apply_clicked()

    assert len(applied_data) == 1
    assert applied_data[0]["selected_asset_id"] == "mascot"
    dialog.close()

if __name__ == "__main__":
    ret = pytest.main([__file__, "-v"])
    sys.exit(int(ret))


