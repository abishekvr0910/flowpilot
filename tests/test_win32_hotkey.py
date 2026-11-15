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
    service._hotkeys[hk_id]["registered"] = True

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
    service._dispatcher.stop()


def test_ll_hook_ignores_unregistered_conflicting_hotkey():
    service = Win32HotkeyService()
    called = []
    hk_id = service.register(
        "Ctrl+Shift+Space",
        lambda: called.append("press"),
        on_release=lambda: called.append("release"),
        suppress=True,
    )
    # Simulate failed RegisterHotKey (another application owns the shortcut)
    assert service._hotkeys[hk_id]["registered"] is False

    next_hook_calls = []
    fake_user32 = MagicMock()
    fake_user32.GetAsyncKeyState.side_effect = lambda vk: 0x8000 if vk in (0x11, 0x10) else 0
    fake_user32.CallNextHookEx.side_effect = lambda *args: (next_hook_calls.append(args) or 0)
    service._user32 = fake_user32

    hook_proc = service._create_hook_proc()
    kb = KBDLLHOOKSTRUCT(vkCode=0x20, scanCode=0, flags=0, time=0, dwExtraInfo=0)
    assert hook_proc(HC_ACTION, WM_KEYDOWN, ctypes.addressof(kb)) == 0
    assert hook_proc(HC_ACTION, WM_KEYUP, ctypes.addressof(kb)) == 0
    time.sleep(0.05)
    assert called == []
    assert service.stats["events_received"] == 0
    assert len(next_hook_calls) == 2
    service._dispatcher.stop()


def test_ll_hook_serializes_rapid_press_and_release_with_tap_latch():
    from engine.hotkey_service import TapLatch

    service = Win32HotkeyService()
    events = []
    done = threading.Event()

    def on_start():
        events.append("start_begin")
        time.sleep(0.05)
        events.append("start_end")

    def on_stop():
        events.append("stop")
        done.set()

    latch = TapLatch(on_start=on_start, on_stop=on_stop, window_ms=50)
    hk_id = service.register("Ctrl+Shift+Space", latch.press, on_release=latch.release, suppress=True)
    service._hotkeys[hk_id]["registered"] = True

    fake_user32 = MagicMock()
    fake_user32.GetAsyncKeyState.side_effect = lambda vk: 0x8000 if vk in (0x11, 0x10) else 0
    service._user32 = fake_user32

    hook_proc = service._create_hook_proc()
    kb = KBDLLHOOKSTRUCT(vkCode=0x20, scanCode=0, flags=0, time=0, dwExtraInfo=0)
    assert hook_proc(HC_ACTION, WM_KEYDOWN, ctypes.addressof(kb)) == 1
    assert hook_proc(HC_ACTION, WM_KEYUP, ctypes.addressof(kb)) == 1

    assert done.wait(timeout=1.5)
    assert events == ["start_begin", "start_end", "stop"]
    latch.reset()
    service._dispatcher.stop()


def test_hook_fallback_to_register_hotkey_when_setwindowshook_fails():
    from unittest.mock import patch

    service = Win32HotkeyService()
    triggered = threading.Event()
    hk_id = service.register("Ctrl+Shift+Space", triggered.set, suppress=True)

    with patch.object(service._user32, "SetWindowsHookExW", return_value=0):
        assert service.start(timeout=3.0) is True
        assert service._hook is None
        assert service._hook_proc is None
        ctypes.windll.user32.PostThreadMessageW(service._thread_id, WM_HOTKEY, hk_id, 0)
        assert triggered.wait(timeout=1.5)
    service.stop()


def test_serial_dispatcher_stop_rejects_and_invalidates_queued_callbacks():
    import threading
    from engine.hotkey_service import _SerialCallbackDispatcher

    dispatcher = _SerialCallbackDispatcher()
    started = threading.Event()
    release = threading.Event()
    second_ran = threading.Event()

    def first():
        started.set()
        release.wait(timeout=2.0)

    def second():
        second_ran.set()

    assert dispatcher.enqueue(first, "first") is True
    assert started.wait(timeout=1.5)
    assert dispatcher.enqueue(second, "second") is True

    # stop() immediately marks accepting=False and invalidates queued items
    assert dispatcher.stop(timeout=0.02) is False
    assert dispatcher.enqueue(lambda: None, "rejected") is False

    release.set()
    assert dispatcher.stop(timeout=1.5) is True
    assert not second_ran.is_set()


def test_serial_dispatcher_stop_timeout_then_reset_prevents_overlapping_workers():
    import threading
    import time
    from engine.hotkey_service import _SerialCallbackDispatcher

    dispatcher = _SerialCallbackDispatcher()
    started = threading.Event()
    release = threading.Event()
    next_done = threading.Event()
    guard = threading.Lock()
    active_count = 0
    overlaps = []
    order = []

    def first():
        nonlocal active_count
        with guard:
            active_count += 1
            if active_count > 1:
                overlaps.append(active_count)
            order.append("first_start")
        started.set()
        release.wait(timeout=2.0)
        with guard:
            order.append("first_end")
            active_count -= 1

    def next_cb():
        nonlocal active_count
        with guard:
            active_count += 1
            if active_count > 1:
                overlaps.append(active_count)
            order.append("next")
            active_count -= 1
        next_done.set()

    assert dispatcher.enqueue(first, "first") is True
    assert started.wait(timeout=1.5)
    first_worker = dispatcher._worker
    assert first_worker is not None and first_worker.is_alive()

    # Timed-out stop() followed by reset() + enqueue() must keep the single live worker
    assert dispatcher.stop(timeout=0.02) is False
    dispatcher.reset()
    assert dispatcher._worker is first_worker
    assert dispatcher.enqueue(next_cb, "next") is True
    assert dispatcher._worker is first_worker

    time.sleep(0.05)
    assert order == ["first_start"]

    release.set()
    assert next_done.wait(timeout=1.5)
    assert order == ["first_start", "first_end", "next"]
    assert overlaps == []
    assert dispatcher.stop(timeout=1.5) is True


def test_win32_hotkey_service_stop_and_restart_rearms_dispatch():
    import threading
    from unittest.mock import patch

    service = Win32HotkeyService()
    calls = []
    first_done = threading.Event()
    second_done = threading.Event()

    with patch.object(service._user32, "SetWindowsHookExW", return_value=0), \
         patch.object(service._user32, "RegisterHotKey", return_value=1), \
         patch.object(service._user32, "UnregisterHotKey", return_value=1):
        hk1 = service.register("Ctrl+Alt+F9", lambda: (calls.append("cb1"), first_done.set()))
        assert service.start(timeout=3.0) is True
        ctypes.windll.user32.PostThreadMessageW(service._thread_id, WM_HOTKEY, hk1, 0)
        assert first_done.wait(timeout=1.5)
        service.stop()
        assert not service.is_alive()

        hk2 = service.register("Ctrl+Alt+F10", lambda: (calls.append("cb2"), second_done.set()))
        assert service.start(timeout=3.0) is True
        ctypes.windll.user32.PostThreadMessageW(service._thread_id, WM_HOTKEY, hk2, 0)
        assert second_done.wait(timeout=1.5)
        service.stop()

    assert calls == ["cb1", "cb2"]


if __name__ == "__main__":
    test_parse_hotkey_string()
    test_hotkey_service_lifecycle_and_dispatch()
    test_ll_hook_suppression_repeat_release_and_debounce()
    test_ll_hook_ignores_unregistered_conflicting_hotkey()
    test_ll_hook_serializes_rapid_press_and_release_with_tap_latch()
    test_hook_fallback_to_register_hotkey_when_setwindowshook_fails()
    test_serial_dispatcher_stop_rejects_and_invalidates_queued_callbacks()
    test_serial_dispatcher_stop_timeout_then_reset_prevents_overlapping_workers()
    test_win32_hotkey_service_stop_and_restart_rearms_dispatch()
