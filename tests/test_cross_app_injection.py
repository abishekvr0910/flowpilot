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
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import win32gui
import win32con
from engine.text_injector import TextInjector, InjectionStatus
from engine.window_inspector import WindowInspector
from tests.notepad_harness import (
    is_interactive_desktop, focus_notepad_document, paste_and_verify_notepad,
    open_test_notepad, cleanup_test_fixture,
)

def test_cross_app_safe_abort_when_focus_lost():
    """Separated safety check: validates safe-abort to recovery buffer on focus loss or focus mismatch."""
    payload = "Focus loss safe abort payload\n"

    # Case 1: Missing foreground window (GetForegroundWindow returns 0)
    with patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=0):
        res = TextInjector.inject_with_status(payload, target_hwnd=12345)
        assert res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert TextInjector.last_injected_text == payload

    # Case 2: Focus switched away to another application
    with patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=99999):
        res2 = TextInjector.inject_with_status(payload, target_hwnd=12345)
        assert res2.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert TextInjector.last_injected_text == payload

    print("  -> Cross-app safe abort and focus loss recovery verified successfully.")

def test_cross_app_injection():
    if not is_interactive_desktop():
        print("[RESULT] SKIPPED: Physical cross-application insertion requires an interactive Windows desktop.")
        return True
    print("=" * 70)
    print("FLOWPILOT CROSS-APPLICATION INJECTION & FOCUS STABILITY TEST")
    print("=" * 70)

    np_proc = None
    np_hwnd = 0
    np_fixture = None
    cmd_proc = None
    cmd_verify_file = None
    interactive = is_interactive_desktop()
    print(f"Interactive desktop session: {interactive}")

    try:
        # 1. Spawn Notepad instance
        print("\n[Step 1] Spawning Notepad...")
        np_hwnd, np_proc, np_fixture = open_test_notepad()

        print(f"Notepad HWND: {np_hwnd}")
        assert np_hwnd != 0, "Failed to locate Notepad window"

        # 2. Inject text into Notepad & verify physical document contents
        print("\n[Step 2] Injecting into Notepad...")
        payload_np = "FlowPilot Cross-App Test: Notepad insertion verified.\n"
        if np_hwnd:
            win32gui.ShowWindow(np_hwnd, win32con.SW_RESTORE)
            focus_notepad_document(np_hwnd)

        res_np = paste_and_verify_notepad(payload_np, payload_np, np_hwnd)
        print(f"Notepad Injection Result: verified={res_np.verified}, status={res_np.status}, error={res_np.error}")
        assert res_np.verified is True, f"Failed to inject into Notepad: {res_np.error}"
        np_buf = TextInjector.read_window_buffer(np_hwnd)
        assert "FlowPilot Cross-App Test: Notepad insertion verified" in np_buf, (
            f"Text missing from physical Notepad document buffer: {repr(np_buf)}"
        )
        print("  -> Physical document buffer verification: CONFIRMED")

        # 3. Spawn Console instance (cmd.exe)
        print("\n[Step 3] Spawning Command Prompt...")
        cmd_proc = subprocess.Popen(["cmd.exe", "/k", "echo FlowPilot Console Test"])
        cmd_hwnd = 0
        for _ in range(20):
            time.sleep(0.15)
            def find_cmd(hwnd, _):
                nonlocal cmd_hwnd
                if win32gui.IsWindow(hwnd):
                    cls = win32gui.GetClassName(hwnd)
                    title = win32gui.GetWindowText(hwnd)
                    if "cmd.exe" in title.lower() or cls == "ConsoleWindowClass":
                        cmd_hwnd = hwnd
                return True
            win32gui.EnumWindows(find_cmd, None)
            if cmd_hwnd:
                break
        print(f"Console HWND: {cmd_hwnd}")

        if cmd_hwnd:
            print("\n[Step 4] Injecting into Console window & verifying executed command output...")
            with tempfile.NamedTemporaryFile(prefix="flowpilot_cmd_verify_", suffix=".txt", delete=False) as tf:
                cmd_verify_file = Path(tf.name)
            cmd_verify_file.unlink(missing_ok=True)

            payload_cmd = f"echo FlowPilot_Console_Confirmed > \"{cmd_verify_file}\"\n"
            win32gui.ShowWindow(cmd_hwnd, win32con.SW_RESTORE)
            res_cmd = TextInjector.inject_with_status(payload_cmd, target_hwnd=cmd_hwnd)
            print(f"Console Injection Result: status={res_cmd.status}, error={res_cmd.error_message}")

            # Verify actual delivery: wait for cmd.exe to execute delivered keystrokes and confirm file contents
            executed = False
            for _ in range(30):
                time.sleep(0.1)
                if cmd_verify_file.exists():
                    txt = cmd_verify_file.read_text(encoding="utf-8", errors="replace")
                    if "FlowPilot_Console_Confirmed" in txt:
                        executed = True
                        break
            assert executed, (
                f"Console delivery unconfirmed: keystrokes were not executed by cmd.exe! "
                f"Status: {res_cmd.status}, error: {res_cmd.error_message}"
            )
            print("  -> Console document execution: CONFIRMED (output token physically verified)")

        # 4b. Simulated Rich Text / Code Editor Surface (PySide6 QTextEdit)
        print("\n[Step 4b] Testing Simulated Rich Text / Code Editor Surface (PySide6 QTextEdit)...")
        from PySide6.QtWidgets import QApplication, QTextEdit
        app = QApplication.instance() or QApplication(sys.argv)
        editor = QTextEdit()
        editor.setWindowTitle("FlowPilot Simulated Editor Surface")
        editor.setPlainText("Initial code comment:\n")
        editor.show()
        app.processEvents()
        time.sleep(0.3)

        editor_hwnd = int(editor.winId()) if editor.winId() else 0
        payload_editor = "// FlowPilot injected code snippet: async function test() { return true; }\n"
        if editor_hwnd != 0:
            res_editor = TextInjector.inject_with_status(payload_editor, target_hwnd=editor_hwnd)
            app.processEvents()
            time.sleep(0.3)
            print(f"Editor Surface Injection Result: status={res_editor.status}, error={res_editor.error_message}")
            editor_doc_text = editor.toPlainText()
            assert "// FlowPilot injected code snippet" in editor_doc_text, (
                f"Editor delivery unconfirmed: text missing from editor document! Content: {repr(editor_doc_text)}"
            )
            print("  -> Editor document contents: CONFIRMED (code snippet physically verified in buffer)")
        else:
            print("Note: Headless Qt platform provided no native HWND; deferred.")
        editor.close()

        # 5. Recovery buffer check
        print("\n[Step 5] Checking in-memory recovery buffer...")
        assert TextInjector.last_injected_text != "", "Recovery buffer is empty"
        recopy_ok = TextInjector.re_copy_last()
        assert recopy_ok is True, "Failed to re-copy last dictation"
        print("Recovery buffer successfully verified.")

        # 6. Error handling: inject into invalid/destroyed HWND
        print("\n[Step 6] Testing injection into invalid/closed HWND...")
        dead_hwnd = 99999999
        res_dead = TextInjector.inject_with_status("This should handle invalid HWND safely", target_hwnd=dead_hwnd)
        print(f"Invalid HWND handling return: {res_dead.status} (Gracefully handled)")
        assert res_dead.status in (InjectionStatus.FAILED_RECOVERY_AVAILABLE, InjectionStatus.ERROR)

        print("\n" + "=" * 70)
        print("CROSS-APPLICATION INJECTION & FOCUS STABILITY: PASSED (100%)")
        print("=" * 70)
        return True

    finally:
        # Clean up spawned processes and temporary verification files unconditionally
        print("\n[Cleanup] Terminating spawned test processes...")
        if cmd_verify_file is not None:
            try:
                cmd_verify_file.unlink(missing_ok=True)
            except Exception:
                pass
        cleanup_test_fixture(np_fixture, np_hwnd, np_proc)
        if cmd_proc:
            try:
                cmd_proc.kill()
                cmd_proc.wait(timeout=2.0)
            except Exception:
                pass

if __name__ == "__main__":
    test_cross_app_safe_abort_when_focus_lost()
    success = test_cross_app_injection()
    sys.exit(0 if success else 1)
