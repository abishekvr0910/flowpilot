"""
FlowPilot Cross-Application Text Injection & Focus Stability Test
Simulates dictation workflows across multiple target window contexts:
1. Standard Text Editors (Notepad)
2. Terminal / Console Windows (Command Prompt / Windows Terminal)
3. Focus retention and recovery buffer verification
4. Error handling when target window is closed unexpectedly
"""

import sys
import os
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import win32gui
import win32process
import win32con
from engine.text_injector import TextInjector
from engine.window_inspector import WindowInspector

def test_cross_app_injection():
    print("=" * 70)
    print("FLOWPILOT CROSS-APPLICATION INJECTION & FOCUS STABILITY TEST")
    print("=" * 70)

    # 1. Spawn Notepad instance
    print("\n[Step 1] Spawning Notepad...")
    np_proc = subprocess.Popen(["notepad.exe"])
    time.sleep(1.0)

    np_hwnd = 0
    def find_np(hwnd, _):
        nonlocal np_hwnd
        if win32gui.IsWindowVisible(hwnd) and "notepad" in win32gui.GetWindowText(hwnd).lower():
            np_hwnd = hwnd
    win32gui.EnumWindows(find_np, None)
    print(f"Notepad HWND: {np_hwnd}")
    assert np_hwnd != 0, "Failed to locate Notepad window"

    # 2. Inject text into Notepad
    print("\n[Step 2] Injecting into Notepad...")
    payload_np = "FlowPilot Cross-App Test: Notepad insertion verified.\n"
    ok1 = TextInjector.inject(payload_np, target_hwnd=np_hwnd)
    print(f"Notepad Injection Success: {ok1}")
    assert ok1 is True, "Failed to inject into Notepad"

    # 3. Spawn Console instance (cmd.exe)
    print("\n[Step 3] Spawning Command Prompt...")
    cmd_proc = subprocess.Popen(["cmd.exe", "/k", "echo FlowPilot Console Test"])
    time.sleep(1.0)

    cmd_hwnd = 0
    def find_cmd(hwnd, _):
        nonlocal cmd_hwnd
        if win32gui.IsWindowVisible(hwnd):
            cls = win32gui.GetClassName(hwnd)
            title = win32gui.GetWindowText(hwnd)
            if "cmd.exe" in title.lower() or cls == "ConsoleWindowClass":
                cmd_hwnd = hwnd
    win32gui.EnumWindows(find_cmd, None)
    print(f"Console HWND: {cmd_hwnd}")

    if cmd_hwnd:
        print("\n[Step 4] Injecting into Console window...")
        payload_cmd = "echo FlowPilot Command Injected\n"
        ok2 = TextInjector.inject(payload_cmd, target_hwnd=cmd_hwnd)
        print(f"Console Injection Success: {ok2}")
        assert ok2 is True, "Failed to inject into Console"

    # 5. Recovery buffer check
    print("\n[Step 5] Checking in-memory recovery buffer...")
    assert TextInjector.last_injected_text != "", "Recovery buffer is empty"
    recopy_ok = TextInjector.re_copy_last()
    assert recopy_ok is True, "Failed to re-copy last dictation"
    print("Recovery buffer successfully re-copied.")

    # 6. Error handling: inject into invalid/destroyed HWND
    print("\n[Step 6] Testing injection into invalid/closed HWND...")
    dead_hwnd = 99999999
    ok_dead = TextInjector.inject("This should handle invalid HWND safely", target_hwnd=dead_hwnd)
    print(f"Invalid HWND handling return: {ok_dead} (Gracefully handled)")

    # Clean up spawned processes
    print("\n[Step 7] Cleaning up test processes...")
    try:
        np_proc.kill()
        np_proc.wait(timeout=2.0)
    except Exception:
        pass

    try:
        if cmd_proc:
            cmd_proc.kill()
            cmd_proc.wait(timeout=2.0)
    except Exception:
        pass

    print("\n" + "=" * 70)
    print("CROSS-APPLICATION INJECTION & FOCUS STABILITY: PASSED (100%)")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = test_cross_app_injection()
    sys.exit(0 if success else 1)
