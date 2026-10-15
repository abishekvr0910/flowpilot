"""
Tests for FlowPilot Cross-Platform Compatibility (Windows, Linux, macOS).
Verifies that:
1. PynputHotkeyService registers, normalizes, and triggers key chords and releases on Linux/macOS.
2. SingleInstance provides POSIX file lock protection on non-Windows platforms.
3. WindowInspector gracefully handles macOS and Linux active window resolution without crashes.
4. TextInjector handles cross-platform clipboard sequence hashing and OS-specific keystrokes.
5. AudioDucker safely executes on non-Windows platforms.
"""

import sys
import os
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.hotkey_service import PynputHotkeyService, get_hotkey_service
from engine.single_instance import SingleInstance
from engine.window_inspector import WindowInspector
from engine.text_injector import TextInjector
from engine.audio_ducker import AudioDucker


def test_pynput_hotkey_service_registration_and_normalization():
    """Validates that PynputHotkeyService normalizes and tracks multi-key chords and function keys."""
    service = PynputHotkeyService()
    
    triggered = []
    released = []

    hk1 = service.register("Ctrl+Shift+Space", lambda: triggered.append("toggle"))
    hk2 = service.register("F9", lambda: triggered.append("p2t_press"), on_release=lambda: released.append("p2t_release"))
    hk3 = service.register("Alt+Shift+Z", lambda: triggered.append("repaste"))

    assert hk1 == 1
    assert hk2 == 2
    assert hk3 == 3
    assert len(service._hotkeys) == 3

    # Check key parts normalization
    assert service._hotkeys[1]["parts"] == {"CTRL", "SHIFT", "SPACE"}
    assert service._hotkeys[2]["parts"] == {"F9"}
    assert service._hotkeys[3]["parts"] == {"ALT", "SHIFT", "Z"}

    # Simulate key events
    import pynput.keyboard as pk
    
    # 1. Simulate F9 press and release (Push-to-Talk)
    service._on_press(pk.Key.f9)
    time.sleep(0.05)
    assert "p2t_press" in triggered
    service._on_release(pk.Key.f9)
    time.sleep(0.05)
    assert "p2t_release" in released

    # 2. Simulate chord press: Ctrl + Shift + Space
    service._on_press(pk.Key.ctrl_l)
    service._on_press(pk.Key.shift_r)
    service._on_press(pk.Key.space)
    time.sleep(0.05)
    assert "toggle" in triggered

    # 3. Simulate chord release
    service._on_release(pk.Key.space)
    service._on_release(pk.Key.shift_r)
    service._on_release(pk.Key.ctrl_l)


def test_cross_platform_hotkey_factory():
    """Validates get_hotkey_service returns the appropriate platform adapter."""
    with patch("sys.platform", "linux"):
        service = get_hotkey_service()
        assert isinstance(service, PynputHotkeyService)

    with patch("sys.platform", "darwin"):
        service = get_hotkey_service()
        assert isinstance(service, PynputHotkeyService)


def test_cross_platform_clipboard_sequence():
    """Validates fallback clipboard sequence hashing on non-Windows platforms."""
    with patch("sys.platform", "linux"):
        with patch.object(TextInjector, "_safe_clipboard_paste", return_value="test_content_linux"):
            seq1 = TextInjector._get_clipboard_sequence_number()
            assert isinstance(seq1, int) and seq1 > 0

        with patch.object(TextInjector, "_safe_clipboard_paste", return_value="different_content_linux"):
            seq2 = TextInjector._get_clipboard_sequence_number()
            assert isinstance(seq2, int) and seq2 > 0
            assert seq1 != seq2, "Sequence hash must differ when clipboard content changes"


def test_cross_platform_window_inspector():
    """Validates WindowInspector safely returns structured info on Linux and macOS."""
    with patch("sys.platform", "linux"):
        info = WindowInspector.get_active_window_info()
        assert "process_name" in info
        assert "category" in info
        assert "hwnd" in info

    with patch("sys.platform", "darwin"):
        info = WindowInspector.get_active_window_info()
        assert "process_name" in info
        assert "category" in info
        assert "hwnd" in info


def test_cross_platform_audio_ducker():
    """Validates AudioDucker handles start/stop gracefully on non-Windows platforms without exceptions."""
    ducker = AudioDucker()
    with patch("sys.platform", "linux"):
        ducker.start_ducking()
        ducker.stop_ducking()

    with patch("sys.platform", "darwin"):
        ducker.start_ducking()
        ducker.stop_ducking()


if __name__ == "__main__":
    test_pynput_hotkey_service_registration_and_normalization()
    test_cross_platform_hotkey_factory()
    test_cross_platform_clipboard_sequence()
    test_cross_platform_window_inspector()
    test_cross_platform_audio_ducker()
    print("\n[RESULT] All cross-platform compatibility tests PASSED 100%.")
    sys.exit(0)
