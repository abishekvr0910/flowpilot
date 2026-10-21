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
import win32process
from engine.text_injector import TextInjector, InjectionStatus
from engine.window_inspector import WindowInspector
from tests.notepad_harness import (
    is_interactive_desktop, focus_notepad_document, paste_and_verify_notepad,
    open_test_notepad, cleanup_test_fixture,
)

def test_cross_app_safe_abort_when_focus_lost():
    """Separated safety check: validates safe-abort to recovery buffer on focus loss or focus mismatch.
    Mocks IsWindow=True, different window hierarchies, and foreground activation;
    asserts the foreground focus check runs and no clipboard writes or keystrokes occur.
    """
    payload = "Focus loss safe abort payload\n"
    target_hwnd = 12345

    # Case 1: Missing foreground window (GetForegroundWindow returns 0)
    with patch("engine.text_injector.win32gui.IsWindow", return_value=True), \
         patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=0), \
         patch("engine.text_injector.win32gui.GetAncestor", side_effect=lambda h, f: h), \
         patch.object(TextInjector, "_safe_set_foreground") as mock_set_fg, \
         patch.object(TextInjector, "_resolve_verified_foreground", wraps=TextInjector._resolve_verified_foreground) as spy_resolve_fg, \
         patch.object(TextInjector, "_safe_clipboard_copy") as mock_clip_copy, \
         patch("engine.text_injector.win32api.keybd_event") as mock_keybd, \
         patch.object(TextInjector, "inject_unicode_sendinput") as mock_sendinput:

        res = TextInjector.inject_with_status(payload, target_hwnd=target_hwnd)
        assert res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert TextInjector.last_injected_text == payload
        assert mock_set_fg.called, "Foreground activation must be attempted when target is not foreground"
        assert spy_resolve_fg.called, "Foreground verification check must run"
        mock_clip_copy.assert_not_called()
        mock_keybd.assert_not_called()
        mock_sendinput.assert_not_called()

    # Case 2: Focus switched away to another application (different hierarchy: 99999 vs 12345)
    with patch("engine.text_injector.win32gui.IsWindow", return_value=True), \
         patch("engine.text_injector.win32gui.GetForegroundWindow", return_value=99999), \
         patch("engine.text_injector.win32gui.GetAncestor", side_effect=lambda h, f: h), \
         patch.object(TextInjector, "_safe_set_foreground") as mock_set_fg, \
         patch.object(TextInjector, "_resolve_verified_foreground", wraps=TextInjector._resolve_verified_foreground) as spy_resolve_fg, \
         patch.object(TextInjector, "_safe_clipboard_copy") as mock_clip_copy, \
         patch("engine.text_injector.win32api.keybd_event") as mock_keybd, \
         patch.object(TextInjector, "inject_unicode_sendinput") as mock_sendinput:

        res2 = TextInjector.inject_with_status(payload, target_hwnd=target_hwnd)
        assert res2.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert TextInjector.last_injected_text == payload
        assert mock_set_fg.called, "Foreground activation must be attempted when target is not foreground"
        assert spy_resolve_fg.called, "Foreground verification check must run"
        mock_clip_copy.assert_not_called()
        mock_keybd.assert_not_called()
        mock_sendinput.assert_not_called()

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

        # 3. Spawn isolated Console instance (cmd.exe) with unique process and title identity
        print("\n[Step 3] Spawning isolated Command Prompt...")
        unique_console_tag = f"FlowPilot_Test_Console_{os.getpid()}_{time.time_ns()}"
        creation_flags = subprocess.CREATE_NEW_CONSOLE if hasattr(subprocess, "CREATE_NEW_CONSOLE") else 0
        cmd_proc = subprocess.Popen(
            ["cmd.exe", "/k", f"title {unique_console_tag} && echo {unique_console_tag}"],
            creationflags=creation_flags
        )
        cmd_hwnd = 0
        for _ in range(30):
            time.sleep(0.15)
            def find_cmd(hwnd, _):
                nonlocal cmd_hwnd
                if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if unique_console_tag in title:
                        cmd_hwnd = hwnd
                return True
            win32gui.EnumWindows(find_cmd, None)
            if cmd_hwnd:
                break
        print(f"Console HWND: {cmd_hwnd}")
        assert cmd_hwnd != 0, (
            f"Failed to locate or spawn isolated test console window with unique tag '{unique_console_tag}'. "
            f"Target window unavailable."
        )

        # Verify window ownership and identity before typing to prevent misdirected keystrokes
        assert win32gui.IsWindow(cmd_hwnd), f"Console HWND {cmd_hwnd} is not a valid window"
        cmd_title = win32gui.GetWindowText(cmd_hwnd)
        assert unique_console_tag in cmd_title, (
            f"Console window ownership mismatch: expected tag '{unique_console_tag}' in '{cmd_title}'"
        )
        _, cmd_win_pid = win32process.GetWindowThreadProcessId(cmd_hwnd)
        assert cmd_win_pid != 0, f"Failed to resolve process ID for console HWND {cmd_hwnd}"
        print(f"  -> Console window ownership verified: PID={cmd_win_pid}, Title='{cmd_title}'")

        # 4. Inject into Console window & verify executed command output
        print("\n[Step 4] Injecting into Console window & verifying executed command output...")
        with tempfile.NamedTemporaryFile(prefix="flowpilot_cmd_verify_", suffix=".txt", delete=False) as tf:
            cmd_verify_file = Path(tf.name)
        cmd_verify_file.unlink(missing_ok=True)

        payload_cmd = f"echo FlowPilot_Console_Confirmed > \"{cmd_verify_file}\"\n"
        win32gui.ShowWindow(cmd_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(cmd_hwnd)
        time.sleep(0.1)
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
        unique_editor_title = f"FlowPilot Simulated Editor Surface ({os.getpid()}_{time.time_ns()})"
        editor.setWindowTitle(unique_editor_title)
        editor.setPlainText("Initial code comment:\n")
        editor.show()
        app.processEvents()
        time.sleep(0.3)

        editor_hwnd = int(editor.winId()) if editor.winId() else 0
        assert editor_hwnd != 0, "Simulated Qt editor surface failed to allocate a valid native window handle (HWND)"
        assert editor.isVisible(), "Simulated Qt editor surface is not visible on desktop"

        payload_editor = "// FlowPilot injected code snippet: async function test() { return true; }\n"
        win32gui.ShowWindow(editor_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(editor_hwnd)
        time.sleep(0.1)
        res_editor = TextInjector.inject_with_status(payload_editor, target_hwnd=editor_hwnd)
        app.processEvents()
        time.sleep(0.3)
        print(f"Editor Surface Injection Result: status={res_editor.status}, error={res_editor.error_message}")
        editor_doc_text = editor.toPlainText()
        assert "// FlowPilot injected code snippet" in editor_doc_text, (
            f"Editor delivery unconfirmed: text missing from editor document! Content: {repr(editor_doc_text)}"
        )
        print("  -> Editor document contents: CONFIRMED (code snippet physically verified in buffer)")
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
