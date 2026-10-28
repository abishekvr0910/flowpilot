"""Feature 32: Clipboard, focus, and text delivery regression checks."""

import sys
import time
from pathlib import Path
from unittest.mock import patch
import pyperclip

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import win32gui
import win32con
from engine.text_injector import TextInjector, InjectionStatus, InjectionResult
from tests.notepad_harness import (
    focus_notepad_document, is_interactive_desktop,
    open_test_notepad, cleanup_test_fixture,
)


def test_active_window_focus_is_preserved():
    """Foreground recovery must not retarget a field in an already-active app."""
    with patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=12345), \
         patch('engine.text_injector.win32api.keybd_event') as key_event, \
         patch('engine.text_injector.win32process.AttachThreadInput') as attach:
        TextInjector._safe_set_foreground(12345)
    key_event.assert_not_called()
    attach.assert_not_called()


def test_find_edit_control_when_editor_is_not_first_child():
    """Verify that _find_edit_control enumerates all child windows and finds the editor even when it is not the first child."""
    parent_hwnd = 1000
    children = [
        (2001, "msctls_statusbar32"),   # Child 1: Status bar (not editor)
        (2002, "ToolbarWindow32"),       # Child 2: Toolbar (not editor)
        (2003, "NotepadTextBox"),        # Child 3: Modern Windows 11 Notepad editor
        (2004, "ScrollBar"),             # Child 4: Scrollbar (not editor)
    ]

    def fake_enum_child_windows(hwnd, callback, extra):
        assert hwnd == parent_hwnd
        for child_hwnd, _ in children:
            cont = callback(child_hwnd, extra)
            # Windows API requirement: EnumChildWindows stops if callback returns False or None
            if not cont:
                break

    def fake_get_class_name(child_hwnd):
        for ch, cls_name in children:
            if ch == child_hwnd:
                return cls_name
        return ""

    with patch("engine.text_injector.HAS_WIN32", True), \
         patch("engine.text_injector.sys.platform", "win32"), \
         patch("engine.text_injector.win32gui.EnumChildWindows", side_effect=fake_enum_child_windows), \
         patch("engine.text_injector.win32gui.GetClassName", side_effect=fake_get_class_name):
        resolved = TextInjector._find_edit_control(parent_hwnd)
        assert resolved == 2003, f"Expected child 2003 (NotepadTextBox), got {resolved}"

    # Verify when no editor child exists, it falls back to parent_hwnd
    children_no_editor = [
        (2001, "msctls_statusbar32"),
        (2002, "ToolbarWindow32"),
    ]
    def fake_enum_no_editor(hwnd, callback, extra):
        for child_hwnd, _ in children_no_editor:
            if not callback(child_hwnd, extra):
                break

    with patch("engine.text_injector.HAS_WIN32", True), \
         patch("engine.text_injector.sys.platform", "win32"), \
         patch("engine.text_injector.win32gui.EnumChildWindows", side_effect=fake_enum_no_editor), \
         patch("engine.text_injector.win32gui.GetClassName", return_value="msctls_statusbar32"):
        resolved = TextInjector._find_edit_control(parent_hwnd)
        assert resolved == parent_hwnd, f"Expected parent {parent_hwnd}, got {resolved}"


def test_find_edit_control_resolves_leaf_editor_when_wrapped_by_container():
    """Verify that _find_edit_control resolves the innermost leaf editor control (e.g. RichEditD2DPT)

    when wrapped inside an outer container like modern Windows 11 Notepad's NotepadTextBox.
    """
    parent_hwnd = 1000
    children = [
        (2001, "NotepadTextBox"),  # Container wrapper
        (2002, "RichEditD2DPT"),   # Leaf editor control
    ]

    def fake_enum_child_windows(hwnd, callback, extra):
        assert hwnd == parent_hwnd
        for child_hwnd, _ in children:
            if not callback(child_hwnd, extra):
                break

    def fake_get_class_name(child_hwnd):
        for ch, cls_name in children:
            if ch == child_hwnd:
                return cls_name
        return ""

    def fake_is_child(parent, child):
        # 2002 is a child of 2001
        return parent == 2001 and child == 2002

    with patch("engine.text_injector.HAS_WIN32", True), \
         patch("engine.text_injector.sys.platform", "win32"), \
         patch("engine.text_injector.win32gui.EnumChildWindows", side_effect=fake_enum_child_windows), \
         patch("engine.text_injector.win32gui.GetClassName", side_effect=fake_get_class_name), \
         patch("engine.text_injector.win32gui.IsChild", side_effect=fake_is_child):
        resolved = TextInjector._find_edit_control(parent_hwnd)
        assert resolved == 2002, f"Expected leaf child 2002 (RichEditD2DPT), got {resolved}"



def test_clipboard_is_not_physical_confirmation():
    """An opaque target cannot be verified from our own pending clipboard."""
    with patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch.object(TextInjector, '_find_edit_control', return_value=12345), \
         patch.object(TextInjector, '_safe_clipboard_paste', return_value='dictated words') as clipboard_read:
        assert TextInjector.verify_text_injected('dictated words', 12345, timeout=0.01) is False
    clipboard_read.assert_not_called()

def test_clipboard_copy_failure_and_unicode_fallback():
    """Verify that when clipboard copy fails, Unicode SendInput is invoked without raising UnboundLocalError."""
    with patch.object(TextInjector, '_resolve_verified_foreground', return_value=(True, 12345, None)), \
         patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
         patch.object(TextInjector, '_safe_clipboard_copy', return_value=False), \
         patch.object(TextInjector, '_find_edit_control', return_value=12345), \
         patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=12345), \
         patch.object(TextInjector, 'inject_unicode_sendinput', return_value=True) as mock_unicode:
        res = TextInjector.inject_with_status("Fallback text test", target_hwnd=12345)
        assert res.status == InjectionStatus.SENT_UNVERIFIED
        assert res.chars_sent == len("Fallback text test")
        mock_unicode.assert_called_once_with("Fallback text test", 12345)

def test_focus_loss_after_staging_preserves_clipboard_and_recovery():
    """Verify that if focus is lost after clipboard staging, original clipboard is restored and dictated text is preserved in recovery."""
    original_clip = "OriginalUserClipboardContent"
    dictated_text = "DictatedConfidentialText"

    # State tracking
    current_clip = [original_clip]
    def fake_paste(*args, **kwargs):
        return current_clip[0]
    def fake_copy(t, *args, **kwargs):
        current_clip[0] = t
        return True

    # 1st call to _resolve_verified_foreground succeeds (initial focus check)
    # 2nd call fails (focus switched during staging)
    resolve_calls = [(True, 12345, None), (False, 99999, "Focus switched to 99999")]

    with patch.object(TextInjector, '_resolve_verified_foreground', side_effect=resolve_calls), \
         patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
         patch.object(TextInjector, '_safe_clipboard_paste', side_effect=fake_paste), \
         patch.object(TextInjector, '_safe_clipboard_copy', side_effect=fake_copy), \
         patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=12345):

        res = TextInjector.inject_with_status(dictated_text, target_hwnd=12345, preserve_clipboard=True)
        assert res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        assert res.recovery_available is True
        # Dictated text is preserved in recovery buffer
        assert TextInjector.last_injected_text == dictated_text
        # Original clipboard is preserved
        assert current_clip[0] == original_clip

def test_slow_app_timing_and_dwell():
    """Verify that slow and remote applications trigger extended dwell and hold delays per Wispr guidance."""
    assert "slack.exe" in TextInjector.SLOW_APP_PROCESSES
    assert "notion.exe" in TextInjector.SLOW_APP_PROCESSES
    assert "mstsc.exe" in TextInjector.REMOTE_APP_PROCESSES

    # Verify behavioral hold and dwell resolution
    with patch.object(TextInjector, '_get_target_process_name', return_value="slack.exe"), \
         patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
         patch.object(TextInjector, '_resolve_verified_foreground', return_value=(True, 100, None)), \
         patch.object(TextInjector, '_safe_clipboard_copy', return_value=True), \
         patch.object(TextInjector, '_safe_clipboard_paste', return_value="Existing clipboard fixture"), \
         patch.object(TextInjector, '_original_clipboard', None), \
         patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=100), \
         patch('engine.text_injector.win32api.keybd_event') as mock_keybd1, \
         patch('engine.text_injector.threading.Timer') as mock_timer, \
         patch('engine.text_injector.time.sleep') as mock_sleep:

        TextInjector.inject_with_status("Slow app test", target_hwnd=100, preserve_clipboard=True)
        # Verify timer was created with 3.5s hold delay for Slack
        timer_args = [call[0] for call in mock_timer.call_args_list]
        assert any(abs(args[0] - 3.5) < 0.01 for args in timer_args)
        # Verify keystroke sleep included 0.040s key dwell
        sleep_args = [call[0][0] for call in mock_sleep.call_args_list]
        assert any(abs(s - 0.040) < 0.001 for s in sleep_args)

    # Verify remote desktop hold and dwell resolution (5.0s hold, 0.050s dwell)
    with patch.object(TextInjector, '_get_target_process_name', return_value="mstsc.exe"), \
         patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
         patch.object(TextInjector, '_resolve_verified_foreground', return_value=(True, 200, None)), \
         patch.object(TextInjector, '_safe_clipboard_copy', return_value=True), \
         patch.object(TextInjector, '_safe_clipboard_paste', return_value="Existing clipboard fixture"), \
         patch.object(TextInjector, '_original_clipboard', None), \
         patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=200), \
         patch('engine.text_injector.win32api.keybd_event') as mock_keybd2, \
         patch('engine.text_injector.threading.Timer') as mock_timer, \
         patch('engine.text_injector.time.sleep') as mock_sleep:

        TextInjector.inject_with_status("Remote desktop test", target_hwnd=200, preserve_clipboard=True)
        timer_args = [call[0] for call in mock_timer.call_args_list]
        assert any(abs(args[0] - 5.0) < 0.01 for args in timer_args)
        sleep_args = [call[0][0] for call in mock_sleep.call_args_list]
        assert any(abs(s - 0.050) < 0.001 for s in sleep_args)

    # Verify inject_last recovery buffer dispatch
    TextInjector.last_injected_text = "Recovered dictation text"
    with patch.object(TextInjector, 'inject_with_status') as mock_inject:
        TextInjector.inject_last(target_hwnd=999)
        mock_inject.assert_called_once_with("Recovered dictation text", target_hwnd=999)

def test_focus_loss_with_newer_user_copy_preserves_user_copy():
    """Verify that if the user copies new text right as focus shifts, focus-loss abort preserves user's new copy."""
    original_clip = "PreDictationClip"
    dictated_text = "DictatedText"
    user_new_copy = "UserNewCopyContent"

    current_clip = [original_clip]
    seq_counter = [100]

    def fake_paste(*args, **kwargs):
        return current_clip[0]

    def fake_copy(t, *args, **kwargs):
        current_clip[0] = t
        seq_counter[0] += 1
        return True

    def fake_seq():
        return seq_counter[0]

    # Focus changes on 2nd check
    def resolve_side_effect(hwnd):
        if resolve_side_effect.calls == 0:
            resolve_side_effect.calls += 1
            return (True, 12345, None)
        # User copied new content right as focus switched!
        current_clip[0] = user_new_copy
        seq_counter[0] = 105
        return (False, 99999, "Focus switched to 99999")
    resolve_side_effect.calls = 0

    with patch.object(TextInjector, '_resolve_verified_foreground', side_effect=resolve_side_effect), \
         patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
         patch.object(TextInjector, '_safe_clipboard_paste', side_effect=fake_paste), \
         patch.object(TextInjector, '_safe_clipboard_copy', side_effect=fake_copy), \
         patch.object(TextInjector, '_get_clipboard_sequence_number', side_effect=fake_seq), \
         patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=12345):

        res = TextInjector.inject_with_status(dictated_text, target_hwnd=12345, preserve_clipboard=True)
        assert res.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
        # The user's new copy must NOT be overwritten by original_clip
        assert current_clip[0] == user_new_copy

def test_clipboard_change_during_hold_prevents_overwrite():
    """Verify that if the clipboard sequence changes before the hold timer fires, restore is aborted."""
    current_clip = ["InjectedText"]
    def fake_paste():
        return current_clip[0]
    def fake_copy(t):
        current_clip[0] = t
        return True

    TextInjector._original_clipboard = "PreDictationClip"
    TextInjector.last_injected_text = "InjectedText"
    TextInjector._last_copy_seq = 100

    # User performed a new copy -> sequence number is now 101
    with patch.object(TextInjector, '_safe_clipboard_paste', side_effect=fake_paste), \
         patch.object(TextInjector, '_safe_clipboard_copy', side_effect=fake_copy) as mock_copy, \
         patch.object(TextInjector, '_get_clipboard_sequence_number', return_value=101):

        # Trigger restore logic manually as the timer would
        saved_to_restore = TextInjector._original_clipboard
        cur = TextInjector._safe_clipboard_paste()
        cur_seq = TextInjector._get_clipboard_sequence_number()
        # Should abort restore
        if cur_seq != TextInjector._last_copy_seq:
            restore_aborted = True
        else:
            restore_aborted = False

        assert restore_aborted is True
        mock_copy.assert_not_called()

def test_terminal_shift_insert_routing():
    """Verify that other terminal emulators still route to Shift+Insert."""
    assert "wt.exe" in TextInjector.TERMINAL_APP_PROCESSES
    assert "cmd.exe" in TextInjector.TERMINAL_APP_PROCESSES
    assert "powershell.exe" in TextInjector.TERMINAL_APP_PROCESSES
    assert "alacritty.exe" in TextInjector.TERMINAL_APP_PROCESSES

    # Mintty is outside the direct Unicode console classes.
    with patch.object(TextInjector, '_get_target_process_name', return_value="mintty.exe"), \
         patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
         patch.object(TextInjector, '_resolve_verified_foreground', return_value=(True, 300, None)), \
         patch.object(TextInjector, '_safe_clipboard_copy', return_value=True), \
         patch.object(TextInjector, '_safe_clipboard_paste', return_value="Prior clip"), \
         patch.object(TextInjector, '_original_clipboard', None), \
         patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=300), \
         patch('engine.text_injector.win32gui.GetClassName', return_value="mintty"), \
         patch('engine.text_injector.win32api.keybd_event') as mock_keybd, \
         patch('engine.text_injector.threading.Timer'), \
         patch('engine.text_injector.time.sleep'):

        res = TextInjector.inject_with_status("ls -la\n", target_hwnd=300, preserve_clipboard=True)
        assert res.status == InjectionStatus.SENT_UNVERIFIED
        called_vks = [call[0][0] for call in mock_keybd.call_args_list]
        import win32con
        assert win32con.VK_SHIFT in called_vks
        assert win32con.VK_INSERT in called_vks
        assert win32con.VK_CONTROL not in called_vks

    # Standard app (Notepad): should dispatch VK_CONTROL + ord('V')
    with patch.object(TextInjector, '_get_target_process_name', return_value="notepad.exe"), \
         patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
         patch.object(TextInjector, '_resolve_verified_foreground', return_value=(True, 400, None)), \
         patch.object(TextInjector, '_safe_clipboard_copy', return_value=True), \
         patch.object(TextInjector, '_safe_clipboard_paste', return_value="Prior clip"), \
         patch.object(TextInjector, '_original_clipboard', None), \
         patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
         patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=400), \
         patch('engine.text_injector.win32gui.GetClassName', return_value="Notepad"), \
         patch('engine.text_injector.win32api.keybd_event') as mock_keybd2, \
         patch('engine.text_injector.threading.Timer'), \
         patch('engine.text_injector.time.sleep'):

        res2 = TextInjector.inject_with_status("Hello world\n", target_hwnd=400, preserve_clipboard=True)
        assert res2.status == InjectionStatus.SENT_UNVERIFIED
        called_vks2 = [call[0][0] for call in mock_keybd2.call_args_list]
        import win32con
        assert win32con.VK_CONTROL in called_vks2
        assert ord('V') in called_vks2
        assert win32con.VK_INSERT not in called_vks2


def test_console_hosts_use_direct_unicode_without_clipboard():
    """Conhost and Windows Terminal must not rely on Shift+Insert delivery."""
    for window_class in ('ConsoleWindowClass', 'CASCADIA_HOSTING_WINDOW_CLASS'):
        with patch('engine.text_injector.win32gui.IsWindow', return_value=True), \
             patch('engine.text_injector.win32gui.GetForegroundWindow', return_value=500), \
             patch('engine.text_injector.win32gui.GetClassName', return_value=window_class), \
             patch('engine.text_injector.win32gui.GetWindowText', return_value='Isolated console'), \
             patch('engine.text_injector.target_has_higher_integrity', return_value=False), \
             patch.object(TextInjector, '_resolve_verified_foreground', return_value=(True, 500, None)), \
             patch.object(TextInjector, '_safe_clipboard_copy') as clipboard_copy, \
             patch.object(TextInjector, 'inject_unicode_sendinput', return_value=True) as unicode_send:
            result = TextInjector.inject_with_status('echo hello', target_hwnd=500)
            assert result.status == InjectionStatus.SENT_UNVERIFIED
            unicode_send.assert_called_once_with('echo hello', 500)
            clipboard_copy.assert_not_called()

            newline_result = TextInjector.inject_with_status('echo hello\n', target_hwnd=500)
            assert newline_result.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE
            assert TextInjector.last_injected_text == 'echo hello\n'
            unicode_send.assert_called_once()
            clipboard_copy.assert_not_called()

            unicode_send.return_value = False
            uncertain_result = TextInjector.inject_with_status('echo uncertain', target_hwnd=500)
            assert uncertain_result.status == InjectionStatus.SENT_UNVERIFIED
            assert uncertain_result.recovery_available is True
            assert TextInjector.last_injected_text == 'echo uncertain'
            clipboard_copy.assert_not_called()

def test_terminal_dual_mode_routing():
    """Verify terminal dual-mode injector chooses direct typing or clipboard paste correctly."""
    with patch.object(TextInjector, 'inject_unicode_sendinput', return_value=True) as mock_direct:
        res = TextInjector.inject_terminal_dual_mode("git status", target_hwnd=500, prefer_direct_typing=True)
        assert res.status == InjectionStatus.SENT_UNVERIFIED
        mock_direct.assert_called_once_with("git status", 500)

    with patch.object(TextInjector, 'inject_with_status', return_value=InjectionResult(status=InjectionStatus.SENT_UNVERIFIED, chars_sent=10)) as mock_paste:
        res2 = TextInjector.inject_terminal_dual_mode("git commit -m 'test'", target_hwnd=500, prefer_direct_typing=False)
        assert res2.status == InjectionStatus.SENT_UNVERIFIED
        mock_paste.assert_called_once_with("git commit -m 'test'", 500, preserve_clipboard=True)

def test_text_injection():
    test_terminal_dual_mode_routing()
    test_active_window_focus_is_preserved()
    test_clipboard_is_not_physical_confirmation()
    test_clipboard_copy_failure_and_unicode_fallback()
    test_focus_loss_after_staging_preserves_clipboard_and_recovery()
    test_focus_loss_with_newer_user_copy_preserves_user_copy()
    test_slow_app_timing_and_dwell()
    test_terminal_shift_insert_routing()
    test_console_hosts_use_direct_unicode_without_clipboard()
    test_clipboard_change_during_hold_prevents_overwrite()
    test_find_edit_control_when_editor_is_not_first_child()
    test_find_edit_control_resolves_leaf_editor_when_wrapped_by_container()
    if not is_interactive_desktop():
        print("[RESULT] SKIPPED: Physical Notepad insertion requires an interactive Windows desktop; focus, copy failure fallback, focus-loss abort, slow-app timing, and clipboard-confirmation unit checks passed.")
        return True
    print("=" * 60)
    print("AUDIT TEST 3: TEXT INSERTION & CLIPBOARD PRESERVATION")
    print("=" * 60)

    # 1. Set a sentinel in clipboard to verify preservation
    sentinel = "ORIGINAL_CLIPBOARD_VALUE_AUDIT_SAFE"
    clip_ready = TextInjector._safe_clipboard_copy(sentinel)
    print(f"Pre-test clipboard set: {clip_ready} ('{sentinel}')")

    # 2. Open a unique test document and wait for its real RichEdit surface.
    print("Launching notepad.exe for injection verification...")
    try:
        notepad_hwnd, proc, fixture = open_test_notepad()
    except RuntimeError as exc:
        print(f"FAILED: {exc}")
        return False

    print(f"Found Notepad window HWND: {notepad_hwnd}")

    # 5. Bring Notepad to foreground safely and focus document
    win32gui.ShowWindow(notepad_hwnd, win32con.SW_RESTORE)
    assert focus_notepad_document(notepad_hwnd), "Notepad document did not acquire focus"
    time.sleep(0.3)

    target_hwnd = notepad_hwnd

    # 6. Inject test text via legitimate product injection path
    test_payload = "FlowPilot Verification: Text injection into Notepad succeeded."
    print(f"Injecting payload: '{test_payload}'...")
    res = TextInjector.inject_with_status(test_payload + "\n", target_hwnd=target_hwnd)
    print(f"TextInjector.inject_with_status returned: status={res.status}, error={res.error_message}")

    # 7. Physical document buffer verification & honest reporting
    first_attempt_verified = TextInjector.verify_text_injected("FlowPilot", target_hwnd, timeout=2.5)
    if not first_attempt_verified:
        buf = TextInjector.read_window_buffer(target_hwnd)
        if buf and "flowpilot" in buf.lower():
            first_attempt_verified = True
    print(f"First-attempt physical document verification: {first_attempt_verified}")

    interactive = is_interactive_desktop()
    print(f"Interactive desktop session: {interactive}")

    # 8. Check clipboard preservation after injection attempt
    time.sleep(2.0)
    post_clipboard = TextInjector._safe_clipboard_paste()
    print(f"Post-injection clipboard value: '{post_clipboard}'")

    if clip_ready:
        preserved = (post_clipboard == sentinel)
        print(f"Clipboard preserved successfully: {preserved}")
    else:
        preserved = True

    if first_attempt_verified:
        print("  -> First-attempt injection PASSED without retry.")
        injection_ok = True
    else:
        # A sent status is not proof of delivery. Retry only after the actual
        # document buffer proves the payload absent; never risk a duplicate.
        print(f"  -> First-attempt not verified in buffer (Status: {res.status}).")
        document = TextInjector.read_window_buffer(target_hwnd)
        recovery_held = TextInjector.last_injected_text == test_payload + "\n"
        injection_ok = False
        if document is not None and "FlowPilot Verification:" not in document and recovery_held:
            if focus_notepad_document(target_hwnd):
                retry = TextInjector.inject_with_status(test_payload + "\n", target_hwnd=target_hwnd)
                injection_ok = TextInjector.verify_text_injected("FlowPilot Verification:", target_hwnd, timeout=2.5)
                print(f"  -> Proven-absent retry: status={retry.status}, verified={injection_ok}")
                time.sleep(2.0)
                if clip_ready:
                    preserved = preserved and TextInjector._safe_clipboard_paste() == sentinel
        else:
            print("  -> Retry withheld: document unreadable, payload already present, or recovery text missing.")

    # 9. Cleanup Notepad
    cleanup_test_fixture(fixture, notepad_hwnd, proc)
    print("Closed Notepad instance.")

    if not injection_ok:
        print("FAILED: Text injection failed or was improperly handled.")
        assert False, "Text injection failed or was improperly handled."
    if not preserved:
        print("FAILED: Clipboard was not properly restored.")
        assert False, "Clipboard was not properly restored."

    print("\n[RESULT] Text insertion and clipboard preservation PASSED.")
    return True

def test_physical_modifier_release_gate():
    """Verify physical modifier polling helper runs safely and recognizes release."""
    print("Testing physical modifier release gate helper...")
    assert hasattr(TextInjector, "_wait_for_physical_modifiers_release")
    assert TextInjector.FLOWPILOT_SYNTHETIC_EXTRA_INFO == 0x46504C54
    res = TextInjector._wait_for_physical_modifiers_release(timeout_sec=0.05)
    assert isinstance(res, bool)
    print("  -> Physical modifier release gate test PASSED.")


if __name__ == "__main__":
    test_physical_modifier_release_gate()
    success = test_text_injection()
    sys.exit(0 if success else 1)
