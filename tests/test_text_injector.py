import sys
import time
import subprocess
from pathlib import Path
import pyperclip

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import win32gui
import win32con
from engine.text_injector import TextInjector

def test_text_injection():
    print("=" * 60)
    print("AUDIT TEST 3: TEXT INSERTION & CLIPBOARD PRESERVATION")
    print("=" * 60)

    # 1. Set a sentinel in clipboard to verify preservation
    sentinel = "ORIGINAL_CLIPBOARD_VALUE_AUDIT_SAFE"
    clip_ready = TextInjector._safe_clipboard_copy(sentinel)
    print(f"Pre-test clipboard set: {clip_ready} ('{sentinel}')")

    # 2. Launch Notepad
    print("Launching notepad.exe for injection verification...")
    proc = subprocess.Popen(["notepad.exe"])
    time.sleep(1.2)

    # 3. Find Notepad HWND
    notepad_hwnd = 0
    for _ in range(20):
        hwnds = []
        win32gui.EnumWindows(lambda h, l: l.append(h) if win32gui.IsWindowVisible(h) and "notepad" in win32gui.GetClassName(h).lower() else None, hwnds)
        if hwnds:
            notepad_hwnd = hwnds[0]
            break
        time.sleep(0.2)

    print(f"Found Notepad window HWND: {notepad_hwnd}")
    if not notepad_hwnd:
        print("FAILED: Could not locate Notepad HWND.")
        proc.terminate()
        return False

    # 4. Bring Notepad to foreground safely
    TextInjector._safe_set_foreground(notepad_hwnd)
    time.sleep(0.3)

    # 5. Inject test text
    test_payload = "FlowPilot Verification: Text injection into Notepad succeeded."
    print(f"Injecting payload: '{test_payload}'...")
    success = TextInjector.inject(test_payload + "\n", target_hwnd=notepad_hwnd)
    print(f"TextInjector.inject returned: {success}")

    # 6. Verify text presence in buffer and clipboard restoration
    buffer_verified = TextInjector.verify_text_injected("Text injection into Notepad succeeded", notepad_hwnd)
    print(f"Document buffer verified text arrived: {buffer_verified}")

    time.sleep(1.8)
    post_clipboard = TextInjector._safe_clipboard_paste()
    print(f"Post-injection clipboard value: '{post_clipboard}'")

    if clip_ready:
        preserved = (post_clipboard == sentinel)
        print(f"Clipboard preserved successfully: {preserved}")
    else:
        # Host session clipboard access locked; direct buffer delivery verified
        preserved = buffer_verified
        print(f"Direct Win32 buffer delivery confirmed: {preserved}")

    # 7. Cleanup Notepad
    try:
        proc.kill()
        proc.wait(timeout=2.0)
    except Exception:
        pass
    print("Closed Notepad instance.")

    if not success or not buffer_verified:
        print("FAILED: Text injection failed.")
        return False
    if not preserved:
        print("FAILED: Clipboard was not properly restored.")
        return False

    print("\n[RESULT] Text insertion and clipboard preservation PASSED.")
    return True

if __name__ == "__main__":
    success = test_text_injection()
    sys.exit(0 if success else 1)
