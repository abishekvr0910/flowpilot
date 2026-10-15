"""
Automated Test for FlowPilot Native Desktop App
Tests QApplication startup, FloatingHUD initialization, Win32 style application,
TrayManager, and clean shutdown.
"""

import sys
from pathlib import Path
from PySide6.QtCore import QTimer

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from desktop_app import FlowPilotApp

def test_desktop_app_startup_and_lifecycle():
    print("=" * 60)
    print("AUDIT TEST: NATIVE PYSIDE6 DESKTOP APPLICATION LIFECYCLE")
    print("=" * 60)

    app_instance = FlowPilotApp(enforce_single_instance=False)
    print("[1] FlowPilotApp initialized successfully.")

    # Verify HUD
    assert app_instance.hud is not None
    assert app_instance.hud.isVisible() is True
    print(f"[2] Floating HUD is visible at position {app_instance.hud.pos().x()}, {app_instance.hud.pos().y()}")

    # Verify Tray
    assert app_instance.tray is not None
    print("[3] System Tray manager is active.")

    # Verify Hotkey Service
    assert app_instance.orchestrator.hotkey_service.is_alive() is True
    print("[4] Win32 Global Hotkey service is running.")

    # Test state update propagation
    app_instance._handle_state_update({"state": "listening", "target_app": "notepad.exe"})
    assert app_instance.hud._current_state == "listening"
    print("[5] Propagated state 'listening' to HUD successfully.")

    app_instance._handle_state_update({"state": "audio_level", "level": 0.65})
    assert app_instance.hud.level_bar.value() == 65
    print("[6] Propagated audio level 65% to HUD successfully.")

    app_instance._handle_state_update({"state": "idle"})
    assert app_instance.hud._current_state == "idle"
    print("[7] Returned HUD to 'idle' state successfully.")

    # Schedule clean shutdown via event loop
    QTimer.singleShot(200, app_instance.quit)
    app_instance.run()

    print("[8] Clean shutdown executed successfully.")
    print("\n[RESULT] Native Desktop App test PASSED 100%.")
    return True

if __name__ == "__main__":
    success = test_desktop_app_startup_and_lifecycle()
    sys.exit(0 if success else 1)
