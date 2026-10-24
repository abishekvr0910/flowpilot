"""Feature 2: Global hotkey parsing and binding regression checks."""

import sys
import logging
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

logger = logging.getLogger("FlowPilot.HotkeyTest")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.orchestrator import FlowOrchestrator
from engine.hotkey_service import Win32HotkeyService, parse_hotkey_string, dictation_hotkey_conflict, MOD_CONTROL, MOD_SHIFT, MOD_ALT

def test_hotkey_resolution():
    print("=" * 60)
    print("AUDIT TEST 6: WIN32 REGISTERHOTKEY RESOLUTION & DISPATCH")
    print("=" * 60)

    # 1. Test parsing
    m, vk = parse_hotkey_string("Ctrl+Shift+Space")
    assert m == (MOD_CONTROL | MOD_SHIFT)
    assert vk == 0x20
    print("[1] Parsed 'Ctrl+Shift+Space' successfully.")

    m, vk = parse_hotkey_string("Ctrl+Alt+Space")
    assert m == (MOD_CONTROL | MOD_ALT)
    assert vk == 0x20
    print("[2] Parsed 'Ctrl+Alt+Space' successfully.")

    m, vk = parse_hotkey_string("F9")
    assert m == 0
    assert vk == 0x78
    print("[3] Parsed 'F9' successfully.")

    # A custom key cannot take over FlowPilot recovery or transforms actions.
    assert dictation_hotkey_conflict("Control+Alt+T") == "Selected-text transforms (Ctrl+Alt+T)"
    assert dictation_hotkey_conflict("Shift+Alt+Z") == "Paste last dictation (Alt+Shift+Z)"
    assert dictation_hotkey_conflict("Alt+Shift+X") == "Copy last dictation (Alt+Shift+X)"
    assert dictation_hotkey_conflict("F9") is None
    try:
        parse_hotkey_string("Ctrl+A+B")
    except ValueError:
        pass
    else:
        raise AssertionError("Multiple primary keys must not silently select the last key")

    # Binding a chosen key must not secretly keep the old dictation aliases.
    class FakeService:
        def __init__(self):
            self.keys = []
            self.alive = False
            self.stats = {"errors": []}

        def is_alive(self):
            return self.alive

        def register(self, key, callback, on_release=None):
            self.keys.append(key)

        def start(self, timeout=3.0):
            self.alive = True
            return True

        def stop(self):
            self.alive = False

    legacy = FlowOrchestrator.__new__(FlowOrchestrator)
    legacy.config = {"hotkey": "Ctrl+Shift+Space", "hotkey_mode": "toggle"}
    legacy.hotkey_service = FakeService()
    legacy._auxiliary_hotkeys = {}
    legacy.start_hotkey_listener()
    assert legacy.hotkey_service.keys[:3] == ["Ctrl+Shift+Space", "F9", "Ctrl+Alt+Space"]
    legacy.stt = SimpleNamespace(config=None)
    legacy.processor = SimpleNamespace(config=None)
    legacy.recorder = SimpleNamespace(device=None, set_device=MagicMock())
    with patch("engine.orchestrator.save_config", return_value=True), \
         patch("engine.hotkey_service.get_hotkey_service", side_effect=FakeService):
        assert legacy.update_config({"hotkey_exclusive": True}) is True
    assert legacy.hotkey_service.keys == ["Ctrl+Shift+Space", "Alt+Shift+Z", "Alt+Shift+X"]
    legacy.stop_hotkey_listener()

    isolated = FlowOrchestrator.__new__(FlowOrchestrator)
    isolated.config = {"hotkey": "F9", "hotkey_mode": "toggle", "hotkey_exclusive": True}
    isolated.hotkey_service = FakeService()
    isolated._auxiliary_hotkeys = {}
    isolated.add_auxiliary_hotkey("Ctrl+Alt+T", lambda: None)
    isolated.start_hotkey_listener()
    assert isolated.hotkey_service.keys == ["F9", "Ctrl+Alt+T", "Alt+Shift+Z", "Alt+Shift+X"]
    isolated.stt = SimpleNamespace(config=None)
    isolated.processor = SimpleNamespace(config=None)
    isolated.recorder = SimpleNamespace(device=None, set_device=MagicMock())
    with patch("engine.orchestrator.save_config", return_value=True), \
         patch("engine.hotkey_service.get_hotkey_service", side_effect=FakeService), \
         patch.object(Win32HotkeyService, "test_hotkey_availability", return_value=(True, "Available")):
        assert isolated.update_config({"hotkey": "Ctrl+F9"}) is True
        assert isolated.config["hotkey_exclusive"] is True
        assert isolated.hotkey_service.keys == ["Ctrl+F9", "Ctrl+Alt+T", "Alt+Shift+Z", "Alt+Shift+X"]
        assert isolated.update_config({"hotkey": "Alt+Shift+Z"}) is False
        assert isolated.config["hotkey"] == "Ctrl+F9"
    isolated.stop_hotkey_listener()
    print("[4] F9 is the sole dictation shortcut; rebinding preserves auxiliary actions and rejects reserved keys.")

    # 2. Test orchestrator start and stop with Win32HotkeyService
    orchestrator = FlowOrchestrator()
    orchestrator.start_hotkey_listener()
    assert orchestrator.hotkey_service.is_alive() is True, "Hotkey thread should be running"
    print("[4] Orchestrator started Win32HotkeyService successfully.")

    time.sleep(0.5)

    orchestrator.stop_hotkey_listener()
    assert orchestrator.hotkey_service.is_alive() is False, "Hotkey thread should be stopped"
    print("[5] Orchestrator stopped Win32HotkeyService cleanly.")

    print("\n[RESULT] Win32 Global Hotkey test PASSED 100%.")
    return True

if __name__ == "__main__":
    success = test_hotkey_resolution()
    sys.exit(0 if success else 1)
