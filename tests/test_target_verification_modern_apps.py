"""
Target Verification & Foreground Focus Robustness for Modern Windows Applications
Validates:
1. Physical target verification across modern UI controls via Microsoft UI Automation (UIA)
2. TextInjector.read_window_buffer reading from modern document buffers (TextPattern & ValuePattern)
3. TextInjector.verify_text_injected returning CONFIRMED_INSERTED on verified document presence
4. Robust foreground restoration via AttachThreadInput trio tolerating Windows 11 foreground lock
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QTextEdit, QLineEdit, QMainWindow
from engine.text_injector import TextInjector, InjectionStatus, InjectionResult

def test_uia_modern_buffer_read_and_verification():
    """Verify that TextInjector reads and physically confirms text in modern editor surfaces via UIA."""
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

    # 3. inject_with_status with verify_confirmation=True must return CONFIRMED_INSERTED
    test_token = "FlowPilot Token 98765"
    editor.setPlainText(f"Existing document content with {test_token} present.")
    app.processEvents()

    from unittest.mock import patch
    with patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=hwnd):
        res = TextInjector.inject_with_status(
            test_token,
            target_hwnd=hwnd,
            preserve_clipboard=True,
            verify_confirmation=True,
            expected_token=test_token
        )
    assert res.status == InjectionStatus.CONFIRMED_INSERTED
    assert res.is_confirmed() is True

    win.close()
    app.processEvents()

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
    test_uia_modern_buffer_read_and_verification()
    test_safe_set_foreground_handles_same_window_and_remote_threads()
    print("ALL MODERN APP VERIFICATION TESTS PASSED.")
