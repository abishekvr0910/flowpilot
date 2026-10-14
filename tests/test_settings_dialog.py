"""
Automated Test for FlowPilot SettingsDialog & Hotkey Conflict Inspector
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.settings_dialog import SettingsDialog
from engine.hotkey_service import Win32HotkeyService
from engine.personalization import PersonalizationEngine

def test_settings_dialog_components():
    print("=" * 60)
    print("TEST: SETTINGS DIALOG & HOTKEY CONFLICT INSPECTOR")
    print("=" * 60)

    app = QApplication.instance() or QApplication(sys.argv)

    saved_config = {}
    def on_save_callback(cfg):
        nonlocal saved_config
        saved_config = dict(cfg)

    initial_config = {
        "local_model_size": "base",
        "language": "en",
        "active_tone_mode": "developer",
        "hotkey": "Ctrl+Shift+Space",
        "hotkey_mode": "toggle",
        "ducking_enabled": True,
        "sound_effects_enabled": True,
        "history": []
    }

    dialog = SettingsDialog(
        config=initial_config,
        on_save=on_save_callback,
        personalization=PersonalizationEngine(storage_path=PROJECT_ROOT / "config" / "test_personalization.json")
    )

    print("[1] SettingsDialog initialized successfully.")

    # Check mode selection
    assert dialog.radio_toggle.isChecked() is True
    assert dialog.radio_ptt.isChecked() is False
    print("[2] Initial mode correctly reflects 'toggle'.")

    # Switch to push-to-talk
    dialog.radio_ptt.setChecked(True)
    assert dialog.radio_ptt.isChecked() is True
    print("[3] Successfully switched to Push-to-Talk mode.")

    # Test hotkey availability on current hotkey
    dialog.combo_shortcut.setEditText("Ctrl+Shift+Space")
    dialog._test_current_hotkey()
    assert "Available" in dialog.lbl_hotkey_status.text() or "Currently active" in dialog.lbl_hotkey_status.text()
    print(f"[4] Hotkey check on 'Ctrl+Shift+Space': {dialog.lbl_hotkey_status.text()}")

    # Test hotkey check on Win+Ctrl+Space (known Windows reserved collision)
    dialog.combo_shortcut.setEditText("Ctrl+Win+Space")
    dialog._test_current_hotkey()
    assert "Conflict" in dialog.lbl_hotkey_status.text()
    print(f"[5] Hotkey check on 'Ctrl+Win+Space': {dialog.lbl_hotkey_status.text()}")

    # Test hotkey check on modifier-only 'Ctrl+Win'
    dialog.combo_shortcut.setEditText("Ctrl+Win")
    dialog._test_current_hotkey()
    assert "Modifier-only" in dialog.lbl_hotkey_status.text()
    print(f"[6] Hotkey check on modifier-only 'Ctrl+Win': {dialog.lbl_hotkey_status.text()}")

    # Test hotkey check on F9
    dialog.combo_shortcut.setEditText("F9")
    dialog._test_current_hotkey()
    assert "Available" in dialog.lbl_hotkey_status.text()
    print(f"[7] Hotkey check on single-key 'F9': {dialog.lbl_hotkey_status.text()}")

    # Test saving settings (mock QMessageBox.information to prevent modal block)
    from PySide6.QtWidgets import QMessageBox
    orig_info = QMessageBox.information
    QMessageBox.information = lambda *args, **kwargs: None
    try:
        dialog._save_settings()
    finally:
        QMessageBox.information = orig_info
    assert saved_config.get("hotkey_mode") == "push_to_talk"
    assert saved_config.get("hotkey") == "F9"
    assert saved_config.get("ducking_enabled") is True
    print("[8] Saved settings verified: hotkey='F9', hotkey_mode='push_to_talk'.")

    # Cleanup test personalization file if created
    test_p_path = PROJECT_ROOT / "config" / "test_personalization.json"
    if test_p_path.exists():
        test_p_path.unlink()

    print("\n[RESULT] SettingsDialog & Hotkey Inspector test PASSED 100%.")
    return True

if __name__ == "__main__":
    success = test_settings_dialog_components()
    sys.exit(0 if success else 1)
