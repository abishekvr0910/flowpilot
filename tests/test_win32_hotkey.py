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

import threading
from unittest.mock import MagicMock

from engine.hotkey_service import (
    Win32HotkeyService,
    parse_hotkey_string,
    MOD_CONTROL,
    MOD_SHIFT,
    MOD_ALT,
    WM_HOTKEY,
    HC_ACTION,
    WM_KEYDOWN,
    WM_KEYUP,
    LLKHF_INJECTED,
    KBDLLHOOKSTRUCT,
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
    assert service._hook is not None
    assert service._hook_proc is not None

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

    # Posting WM_HOTKEY immediately after a hook trigger must debounce duplicates
    service._last_hook_trigger[hk_id] = time.monotonic()
    assert user32.PostThreadMessageW(service._thread_id, WM_HOTKEY, hk_id, 0) != 0
    time.sleep(0.15)
    assert triggered_count == 1
    assert service.stats["events_received"] == 1

    # Stop service
    service.stop()
    assert service.is_alive() is False
    assert service._hook is None
    assert service._hook_proc is None
    print("\n[Test Passed] Win32HotkeyService started, dispatched WM_HOTKEY, and cleaned up successfully.")


def test_ll_hook_suppression_repeat_release_and_debounce():
    service = Win32HotkeyService()
    pressed = threading.Event()
    released = threading.Event()
    press_count = 0
    release_count = 0

    def on_press():
        nonlocal press_count
        press_count += 1
        pressed.set()

    def on_release():
        nonlocal release_count
        release_count += 1
        released.set()

    hk_id = service.register("Ctrl+Shift+Space", on_press, on_release=on_release, suppress=True)

    next_hook_calls = []
    fake_user32 = MagicMock()
    fake_user32.GetAsyncKeyState.side_effect = lambda vk: 0x8000 if vk in (0x11, 0x10) else 0
    fake_user32.CallNextHookEx.side_effect = lambda *args: (next_hook_calls.append(args) or 0)
    service._user32 = fake_user32

    hook_proc = service._create_hook_proc()
    assert hook_proc is not None

    # 1. Synthetic SendInput events must pass through untouched
    injected_kb = KBDLLHOOKSTRUCT(vkCode=0x20, scanCode=0, flags=LLKHF_INJECTED, time=0, dwExtraInfo=0)
    assert hook_proc(HC_ACTION, WM_KEYDOWN, ctypes.addressof(injected_kb)) == 0
    assert len(next_hook_calls) == 1
    assert press_count == 0

    # 2. First matching keydown triggers callback once and returns 1 (suppressed)
    kb = KBDLLHOOKSTRUCT(vkCode=0x20, scanCode=0, flags=0, time=0, dwExtraInfo=0)
    assert hook_proc(HC_ACTION, WM_KEYDOWN, ctypes.addressof(kb)) == 1
    assert pressed.wait(timeout=1.0)
    assert press_count == 1
    assert service.stats["events_received"] == 1
    assert len(next_hook_calls) == 1

    # 3. Auto-repeat keydown while held is suppressed without re-triggering callback
    assert hook_proc(HC_ACTION, WM_KEYDOWN, ctypes.addressof(kb)) == 1
    time.sleep(0.05)
    assert press_count == 1

    # 4. Keyup triggers on_release and returns 1 (suppressed)
    assert hook_proc(HC_ACTION, WM_KEYUP, ctypes.addressof(kb)) == 1
    assert released.wait(timeout=1.0)
    assert release_count == 1
    assert 0x20 not in service._hook_active_hotkeys
    assert hk_id in service._last_hook_trigger


if __name__ == "__main__":
    test_parse_hotkey_string()
    test_hotkey_service_lifecycle_and_dispatch()
    test_ll_hook_suppression_repeat_release_and_debounce()
