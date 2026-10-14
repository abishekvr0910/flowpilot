import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.orchestrator import FlowOrchestrator
from engine.hotkey_service import parse_hotkey_string, MOD_CONTROL, MOD_SHIFT, MOD_ALT

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
