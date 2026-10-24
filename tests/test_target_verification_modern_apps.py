"""Feature 29: modern target verification and conservative paste status.

Target Verification & Foreground Focus Robustness for Modern Windows Applications
Validates UI Automation reading on a Qt editor and conservative status logic.
The mocked status checks below do not claim physical paste delivery in other apps.
"""

import os
import sys
import time
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QTextEdit, QLineEdit, QMainWindow
from engine.text_injector import TextInjector, InjectionStatus, InjectionResult


def _can_test_physical_uia() -> bool:
    """An offscreen Qt widget has no native accessibility surface to inspect."""
    if os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
        return False
    if os.environ.get("FLOWPILOT_HEADLESS") == "1":
        return False
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return False
    from tests.notepad_harness import is_interactive_desktop
    return is_interactive_desktop()

def test_uia_modern_buffer_read_and_verification():
    """Verify that UIA reads text already present in a Qt editor."""
    app = QApplication.instance() or QApplication(sys.argv)
    win = QMainWindow()
    editor = QTextEdit(win)
    editor.setPlainText("FlowPilot Physical Verification: Modern Windows UI Automation test payload.")
    win.setCentralWidget(editor)
    win.show()
    app.processEvents()

    hwnd = int(win.winId())
    assert hwnd != 0

    # 1. read_window_buffer must successfully extract document text from modern UI surface
    buf = TextInjector.read_window_buffer(hwnd)
    assert buf is not None, "Failed to read document buffer from modern UI surface"
    assert "FlowPilot Physical Verification" in buf

    # 2. verify_text_injected must physically confirm matching token
    verified = TextInjector.verify_text_injected("FlowPilot Physical Verification", hwnd, timeout=1.0)
    assert verified is True, "Physical verification failed on modern UI document buffer"

    win.close()
    app.processEvents()


def test_confirmation_requires_new_document_content():
    """Never claim delivery solely because the token was already in the target."""
    token = "FlowPilot Token 98765"
    baseline = f"Existing document content with {token} present."
    common = (
        patch("engine.text_injector.win32gui.IsWindow", return_value=True),
        patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=12345),
        patch("engine.text_injector.win32api.keybd_event"),
        patch.object(TextInjector, "_resolve_verified_foreground", return_value=(True, 12345, None)),
        patch.object(TextInjector, "_safe_clipboard_copy", return_value=True),
        patch.object(TextInjector, "_is_flowpilot_window", return_value=False),
        patch.object(TextInjector, "_get_target_process_name", return_value=""),
    )

    with ExitStack() as stack:
        active_mocks = [stack.enter_context(mocked) for mocked in common]
        key_events = active_mocks[2]
        stack.enter_context(patch.object(TextInjector, "read_window_buffer", return_value=baseline))
        result = TextInjector.inject_with_status(
            token, target_hwnd=12345, preserve_clipboard=False,
            verify_confirmation=True
        )
    assert result.status == InjectionStatus.SENT_UNVERIFIED
    key_events.assert_called()

    with patch.object(TextInjector, "read_window_buffer", side_effect=["Before", f"Before {token}"]):
        assert TextInjector._verify_new_text_injected(token, 12345, "Before", timeout=0.1)

def test_safe_set_foreground_handles_same_window_and_remote_threads():
    """Verify that _safe_set_foreground handles already-active and non-active targets cleanly."""
    app = QApplication.instance() or QApplication(sys.argv)
    win = QMainWindow()
    win.show()
    app.processEvents()

    hwnd = int(win.winId())
    # Calling on active or visible window must not throw and return boolean
    ok = TextInjector._safe_set_foreground(hwnd)
    assert isinstance(ok, bool)

    win.close()
    app.processEvents()

if __name__ == "__main__":
    test_confirmation_requires_new_document_content()
    test_safe_set_foreground_handles_same_window_and_remote_threads()
    if _can_test_physical_uia():
        test_uia_modern_buffer_read_and_verification()
        print("UIA READ AND CONSERVATIVE VERIFICATION TESTS PASSED.")
    else:
        print("[RESULT] SKIPPED: physical UI Automation document read requires an interactive Windows Qt surface")
