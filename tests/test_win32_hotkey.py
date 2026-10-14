"""
Test Win32 Global Hotkey Service
Validates parsing, thread lifecycle, PostThreadMessage WM_HOTKEY dispatch, and cleanup.
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes
import pytest

# Ensure root directory is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.hotkey_service import (
    Win32HotkeyService,
    parse_hotkey_string,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_ALT,
    WM_HOTKEY,
)

def test_parse_hotkey_string():
    mods, vk = parse_hotkey_string("Ctrl+Shift+Space")
    assert mods == (MOD_CONTROL | MOD_SHIFT)
    assert vk == 0x20

    mods, vk = parse_hotkey_string("Ctrl+Alt+Space")
    assert mods == (MOD_CONTROL | MOD_ALT)
    assert vk == 0x20

    mods, vk = parse_hotkey_string("F9")
    assert mods == 0
    assert vk == 0x78

def test_hotkey_service_lifecycle_and_dispatch():
    service = Win32HotkeyService()
    triggered_count = 0
    callback_event = None

    def on_hotkey():
        nonlocal triggered_count
        triggered_count += 1

    hk_id = service.register("Ctrl+Shift+Space", on_hotkey)
    assert hk_id == 1

    success = service.start(timeout=3.0)
    assert success is True
    assert service.is_alive() is True

    # Allow thread message queue to settle
    time.sleep(0.2)

    # Post WM_HOTKEY to the worker thread queue directly
    user32 = ctypes.windll.user32
    assert service._thread_id is not None
    post_res = user32.PostThreadMessageW(service._thread_id, WM_HOTKEY, hk_id, 0)
    assert post_res != 0, f"PostThreadMessage failed with error {ctypes.windll.kernel32.GetLastError()}"

    # Wait for callback invocation
    for _ in range(20):
        if triggered_count > 0:
            break
        time.sleep(0.05)

    assert triggered_count == 1, "Callback was not triggered upon receiving WM_HOTKEY"
    assert service.stats["events_received"] == 1

    # Stop service
    service.stop()
    assert service.is_alive() is False
    print("\n[Test Passed] Win32HotkeyService started, dispatched WM_HOTKEY, and cleaned up successfully.")

if __name__ == "__main__":
    test_parse_hotkey_string()
    test_hotkey_service_lifecycle_and_dispatch()
