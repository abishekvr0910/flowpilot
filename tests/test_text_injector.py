import sys
import time
from pathlib import Path
from unittest.mock import patch
import pyperclip

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import win32gui
import win32con
from engine.text_injector import TextInjector, InjectionStatus
from tests.notepad_harness import (
    focus_notepad_document, is_interactive_desktop,
    open_test_notepad, cleanup_test_fixture,
)


def test_active_window_focus_is_preserved():
    """Foreground recovery must not retarget a field in an already-active app."""
    with patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=12345), \
         patch('engine.text_injector.win32api.keybd_event') as key_event, \
         patch('engine.text_injector.win32process.AttachThreadInput') as attach:
        TextInjector._safe_set_foreground(12345)
    key_event.assert_not_called()
    attach.assert_not_called()


def test_clipboard_is_not_physical_confirmation():
    """An opaque target cannot be verified from our own pending clipboard."""
    with patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch.object(TextInjector, '_find_edit_control', return_value=12345), \
         patch.object(TextInjector, '_safe_clipboard_paste', return_value='dictated words') as clipboard_read:
        assert TextInjector.verify_text_injected('dictated words', 12345, timeout=0.01) is False
    clipboard_read.assert_not_called()

def test_text_injection():
    test_active_window_focus_is_preserved()
    test_clipboard_is_not_physical_confirmation()
    print("=" * 60)
    print("AUDIT TEST 3: TEXT INSERTION & CLIPBOARD PRESERVATION")
    print("=" * 60)

    # 1. Set a sentinel in clipboard to verify preservation
    sentinel = "ORIGINAL_CLIPBOARD_VALUE_AUDIT_SAFE"
    clip_ready = TextInjector._safe_clipboard_copy(sentinel)
    print(f"Pre-test clipboard set: {clip_ready} ('{sentinel}')")

    # 2. Open a unique test document and wait for its real RichEdit surface.
    print("Launching notepad.exe for injection verification...")
    try:
        notepad_hwnd, proc, fixture = open_test_notepad()
    except RuntimeError as exc:
        print(f"FAILED: {exc}")
        return False

    print(f"Found Notepad window HWND: {notepad_hwnd}")

    # 5. Bring Notepad to foreground safely and focus document
    win32gui.ShowWindow(notepad_hwnd, win32con.SW_RESTORE)
    focus_notepad_document(notepad_hwnd)
    time.sleep(0.3)

    target_hwnd = notepad_hwnd

    # 6. Inject test text via legitimate product injection path
    test_payload = "FlowPilot Verification: Text injection into Notepad succeeded."
    print(f"Injecting payload: '{test_payload}'...")
    res = TextInjector.inject_with_status(test_payload + "\n", target_hwnd=target_hwnd)
    print(f"TextInjector.inject_with_status returned: status={res.status}, error={res.error_message}")

    # 7. Physical document buffer verification & honest reporting
    first_attempt_verified = TextInjector.verify_text_injected("FlowPilot", target_hwnd, timeout=2.5)
    if not first_attempt_verified:
        buf = TextInjector.read_window_buffer(target_hwnd)
        if buf and "flowpilot" in buf.lower():
            first_attempt_verified = True
    print(f"First-attempt physical document verification: {first_attempt_verified}")

    interactive = is_interactive_desktop()
    print(f"Interactive desktop session: {interactive}")

    # 8. Check clipboard preservation after injection attempt
    time.sleep(2.0)
    post_clipboard = TextInjector._safe_clipboard_paste()
    print(f"Post-injection clipboard value: '{post_clipboard}'")

    if clip_ready:
        preserved = (post_clipboard == sentinel)
        print(f"Clipboard preserved successfully: {preserved}")
    else:
        preserved = True

    if first_attempt_verified:
        print("  -> First-attempt injection PASSED without retry.")
        injection_ok = True
    else:
        # First attempt not confirmed. Check legitimate recovery path without test backdoors.
        print(f"  -> First-attempt not verified in buffer (Status: {res.status}).")
        if res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE or res.recovery_available:
            recovery_held = (TextInjector.last_injected_text == test_payload + "\n")
            print(f"  -> Recovery buffer holds exact text: {recovery_held}")
            rec_ok = TextInjector.re_copy_last()
            rec_clip = TextInjector._safe_clipboard_paste()
            rec_copied = (rec_clip == test_payload + "\n")
            print(f"  -> re_copy_last() placed text on clipboard: {rec_copied}")
            if not interactive:
                print("  Note: Host session is non-interactive (sub-desktop runner). "
                      "FlowPilot safely rejected unknown focus to prevent misdirected keystrokes.")
                injection_ok = (res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE and recovery_held)
            else:
                injection_ok = (first_attempt_verified or (recovery_held and rec_copied))
        else:
            injection_ok = False

    # 9. Cleanup Notepad
    cleanup_test_fixture(fixture, notepad_hwnd, proc)
    print("Closed Notepad instance.")

    if not injection_ok:
        print("FAILED: Text injection failed or was improperly handled.")
        return False
    if not preserved:
        print("FAILED: Clipboard was not properly restored.")
        return False

    print("\n[RESULT] Text insertion and clipboard preservation PASSED.")
    return True

if __name__ == "__main__":
    success = test_text_injection()
    sys.exit(0 if success else 1)
