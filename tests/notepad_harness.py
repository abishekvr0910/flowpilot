"""Physical Windows Notepad test helpers; never used by production injection."""

import ctypes
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import NamedTuple, Optional

import win32gui
import win32process
import win32api
import win32con


_OWNED_TEST_HWNDS: set[int] = set()
_OWNED_NEW_PIDS: set[int] = set()


def _snapshot_existing_notepads() -> tuple[set[int], set[int]]:
    """Record pre-existing Notepad HWNDs and PIDs so tests never hijack or kill user sessions."""
    hwnds: set[int] = set()
    pids: set[int] = set()

    def _collect(hwnd, _):
        try:
            if win32gui.IsWindow(hwnd) and win32gui.GetClassName(hwnd) == "Notepad":
                hwnds.add(int(hwnd))
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid:
                    pids.add(int(pid))
        except Exception:
            pass
        return True

    try:
        win32gui.EnumWindows(_collect, None)
    except Exception:
        pass
    return hwnds, pids


def open_test_notepad(timeout: float = 10.0) -> tuple[int, subprocess.Popen, Path]:
    """Open a unique test file and select only its initialized Notepad editor without touching user windows."""
    from engine.text_injector import TextInjector

    if not is_interactive_desktop():
        raise RuntimeError("Interactive input desktop not attached; physical Notepad launch skipped.")

    preexisting_hwnds, preexisting_pids = _snapshot_existing_notepads()

    fd, filename = tempfile.mkstemp(prefix="flowpilot-audit-", suffix=".txt")
    os.close(fd)
    fixture = Path(filename)
    process = subprocess.Popen(["notepad.exe", str(fixture)])
    deadline = time.monotonic() + timeout
    observed = []
    while time.monotonic() < deadline:
        exact_candidates = []
        new_window_candidates = []
        observed = []

        def _find(hwnd, _):
            try:
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) == "Notepad":
                    title = win32gui.GetWindowText(hwnd) or ""
                    edit = TextInjector._find_edit_control(hwnd)
                    ready = edit != hwnd and win32gui.GetClassName(edit) in ("RichEditD2DPT", "Edit", "NotepadTextBox")
                    observed.append((hwnd, title, ready, hwnd in preexisting_hwnds))
                    if not ready:
                        return True
                    if fixture.name.casefold() in title.casefold():
                        exact_candidates.append(hwnd)
                    elif hwnd not in preexisting_hwnds:
                        new_window_candidates.append(hwnd)
            except Exception:
                pass
            return True

        win32gui.EnumWindows(_find, None)
        chosen = exact_candidates[0] if exact_candidates else (new_window_candidates[0] if new_window_candidates else 0)
        if chosen:
            if chosen not in preexisting_hwnds:
                _OWNED_TEST_HWNDS.add(int(chosen))
            _, chosen_pid = win32process.GetWindowThreadProcessId(chosen)
            if chosen_pid and int(chosen_pid) not in preexisting_pids:
                _OWNED_NEW_PIDS.add(int(chosen_pid))
            return chosen, process, fixture
        time.sleep(0.1)

    cleanup_test_fixture(fixture, process=process)
    raise RuntimeError(f"Notepad did not expose an editable document for {fixture.name}; observed={observed!r}, launcher_exit={process.poll()}.")


def cleanup_test_fixture(fixture: Optional[Path], hwnd: int = 0, process: Optional[subprocess.Popen] = None) -> None:
    """Close only test-owned Notepad windows/processes; never force-kill pre-existing user Notepad sessions."""
    from engine.text_injector import TextInjector

    is_owned_window = bool(hwnd and int(hwnd) in _OWNED_TEST_HWNDS)
    if hwnd and win32gui.IsWindow(hwnd):
        title = (win32gui.GetWindowText(hwnd) or "").casefold()
        matches_fixture = bool(fixture is not None and fixture.name.casefold() in title)
        if is_owned_window:
            try:
                edit = TextInjector._find_edit_control(hwnd)
                if edit and edit != hwnd and win32gui.IsWindow(edit):
                    win32gui.SendMessage(edit, win32con.WM_SETTEXT, 0, "")
            except Exception:
                pass
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                time.sleep(0.2)
                if win32gui.IsWindow(hwnd) and _force_foreground(hwnd):
                    win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                    win32api.keybd_event(ord("N"), 0, 0, 0)
                    win32api.keybd_event(ord("N"), 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(0.2)
            except Exception:
                pass
            if win32gui.IsWindow(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid and int(pid) in _OWNED_NEW_PIDS:
                        import psutil
                        if psutil.pid_exists(pid):
                            psutil.Process(pid).kill()
                        _OWNED_NEW_PIDS.discard(int(pid))
                except Exception:
                    pass
            _OWNED_TEST_HWNDS.discard(int(hwnd))
        elif matches_fixture:
            # Tab opened inside a pre-existing user Notepad instance: clear test buffer only, never kill PID
            try:
                edit = TextInjector._find_edit_control(hwnd)
                if edit and edit != hwnd and win32gui.IsWindow(edit):
                    win32gui.SendMessage(edit, win32con.WM_SETTEXT, 0, "")
            except Exception:
                pass
    if fixture is not None:
        try:
            fixture.unlink(missing_ok=True)
        except OSError:
            pass
    if process and process.poll() is None:
        try:
            if process.pid in _OWNED_NEW_PIDS:
                process.terminate()
                _OWNED_NEW_PIDS.discard(process.pid)
        except Exception:
            pass


class NotepadPasteResult(NamedTuple):
    verified: bool
    retries: int
    first_attempt_success: bool = True
    recovered: bool = False
    status: str = ""
    error: Optional[str] = None


def is_interactive_desktop() -> bool:
    """Returns True only when the current process executes directly on the active interactive input desktop."""
    import sys
    if os.environ.get("FLOWPILOT_HEADLESS") == "1" or os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
        return False
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        return False
    if sys.platform != "win32":
        return True
    try:
        u = ctypes.windll.user32
        h_cur = u.GetThreadDesktop(ctypes.windll.kernel32.GetCurrentThreadId())
        h_input = u.OpenInputDesktop(0, False, 0x01FF)
        if not h_input:
            return False
        name_cur = ctypes.create_unicode_buffer(256)
        name_input = ctypes.create_unicode_buffer(256)
        needed = ctypes.c_ulong()
        u.GetUserObjectInformationW(h_cur, 2, name_cur, 256, ctypes.byref(needed))
        u.GetUserObjectInformationW(h_input, 2, name_input, 256, ctypes.byref(needed))
        u.CloseDesktop(h_input)
        if name_cur.value.lower() != name_input.value.lower():
            return False
        if name_input.value.lower() in ("winlogon", "screen-saver"):
            return False
        try:
            fg = win32gui.GetForegroundWindow()
            if fg and win32gui.IsWindow(fg):
                title = (win32gui.GetWindowText(fg) or "").lower()
                cls = (win32gui.GetClassName(fg) or "").lower()
                if "lock screen" in title or "lockscreen" in cls or "logon" in title or "logonui" in cls:
                    return False
        except Exception:
            pass
        return True
    except Exception:
        return False


class _GuiThreadInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong), ("flags", ctypes.c_ulong),
        ("hwndActive", ctypes.c_void_p), ("hwndFocus", ctypes.c_void_p),
        ("hwndCapture", ctypes.c_void_p), ("hwndMenuOwner", ctypes.c_void_p),
        ("hwndMoveSize", ctypes.c_void_p), ("hwndCaret", ctypes.c_void_p),
        ("rcCaret", ctypes.c_long * 4),
    ]


def _force_foreground(hwnd: int) -> bool:
    """Forcefully foreground a window on the active interactive desktop."""
    try:
        if win32gui.GetForegroundWindow() == hwnd and win32gui.IsWindowVisible(hwnd):
            return True
        fg = win32gui.GetForegroundWindow()
        fg_tid = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
        target_tid = win32process.GetWindowThreadProcessId(hwnd)[0]
        cur_tid = ctypes.windll.kernel32.GetCurrentThreadId()
        pairs = []
        if fg_tid and fg_tid != cur_tid:
            pairs.append((cur_tid, fg_tid))
        if target_tid and target_tid != cur_tid:
            pairs.append((cur_tid, target_tid))
        if fg_tid and target_tid and fg_tid != target_tid and fg_tid != cur_tid:
            pairs.append((fg_tid, target_tid))
        attached = []
        for a, b in pairs:
            try:
                if win32process.AttachThreadInput(a, b, True):
                    attached.append((a, b))
            except Exception:
                pass
        try:
            win32gui.BringWindowToTop(hwnd)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass
        finally:
            for a, b in reversed(attached):
                try:
                    win32process.AttachThreadInput(a, b, False)
                except Exception:
                    pass
        time.sleep(0.1)
        return win32gui.GetForegroundWindow() == hwnd
    except Exception:
        return False


def focus_notepad_document(hwnd: int, timeout: float = 6.0) -> bool:
    """Focus this test window's RichEdit document, not a WinUI input bridge."""
    from engine.text_injector import TextInjector

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not win32gui.IsWindow(hwnd):
            return False
        if not _force_foreground(hwnd):
            TextInjector._safe_set_foreground(hwnd)
        fg = win32gui.GetForegroundWindow()
        if fg != 0 and not TextInjector._is_same_window_hierarchy(hwnd, fg):
            time.sleep(0.05)
            continue
        edit = TextInjector._find_edit_control(hwnd)
        if edit == hwnd or win32gui.GetClassName(edit) not in ("RichEditD2DPT", "Edit", "NotepadTextBox"):
            time.sleep(0.05)
            continue
        top_thread, top_pid = win32process.GetWindowThreadProcessId(hwnd)
        edit_thread, edit_pid = win32process.GetWindowThreadProcessId(edit)
        if top_pid != edit_pid:
            return False
        info = _GuiThreadInfo()
        info.cbSize = ctypes.sizeof(info)

        def _check_focus(thread_id: int) -> bool:
            if not thread_id or not ctypes.windll.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
                return False
            foc = info.hwndFocus
            if not foc:
                return False
            if foc == edit:
                return True
            try:
                if hasattr(win32gui, "IsChild") and (win32gui.IsChild(edit, foc) or win32gui.IsChild(foc, edit) or win32gui.IsChild(hwnd, foc)):
                    return True
            except Exception:
                pass
            return False

        if _check_focus(top_thread) or (edit_thread != top_thread and _check_focus(edit_thread)):
            return True
        own_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        attached = False
        try:
            if own_thread != edit_thread:
                attached = bool(win32process.AttachThreadInput(own_thread, edit_thread, True))
                if not attached:
                    time.sleep(0.05)
                    continue
            win32gui.SetFocus(edit)
        except Exception:
            pass
        finally:
            if attached:
                win32process.AttachThreadInput(own_thread, edit_thread, False)
        time.sleep(0.03)
        fg_now = win32gui.GetForegroundWindow()
        fg_ok = (fg_now == 0 or TextInjector._is_same_window_hierarchy(hwnd, fg_now))
        if fg_ok and (_check_focus(top_thread) or (edit_thread != top_thread and _check_focus(edit_thread))):
            return True
    edit = TextInjector._find_edit_control(hwnd) if win32gui.IsWindow(hwnd) else 0
    fg = win32gui.GetForegroundWindow()
    focus_handles = []
    for thread_id in {win32process.GetWindowThreadProcessId(handle)[0]
                      for handle in (hwnd, edit) if handle and win32gui.IsWindow(handle)}:
        info = _GuiThreadInfo()
        info.cbSize = ctypes.sizeof(info)
        if ctypes.windll.user32.GetGUIThreadInfo(thread_id, ctypes.byref(info)):
            focus_handles.append(int(info.hwndFocus or 0))
    print(f"[Notepad harness] Document focus unavailable: target={hwnd}, "
          f"target_title={win32gui.GetWindowText(hwnd) if win32gui.IsWindow(hwnd) else None}, "
          f"edit={edit}, edit_class={win32gui.GetClassName(edit) if edit else None}, "
          f"foreground={fg}, foreground_title={win32gui.GetWindowText(fg) if fg else None}, "
          f"foreground_class={win32gui.GetClassName(fg) if fg else None}, "
          f"thread_focus={focus_handles}")
    return False


def paste_and_verify_notepad(text: str, expected: str, hwnd: int) -> NotepadPasteResult:
    """
    Executes Notepad paste verification using FlowPilot's legitimate product injection workflow.
    Never uses artificial test-only backdoors like WM_PASTE.
    Reports first-attempt success and recovery separately.
    """
    from engine.text_injector import InjectionStatus, TextInjector

    last_status = ""
    last_error = None

    for attempt in range(2):
        if not focus_notepad_document(hwnd):
            return NotepadPasteResult(
                verified=False,
                retries=attempt,
                first_attempt_success=False,
                recovered=False,
                status="FOCUS_UNAVAILABLE",
                error=f"Could not focus document for HWND {hwnd}",
            )

        result = TextInjector.inject_with_status(text, hwnd)
        last_status = str(result.status)
        last_error = result.error_message

        if result.status not in (InjectionStatus.SENT_UNVERIFIED, InjectionStatus.CONFIRMED_INSERTED):
            if result.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE and attempt == 0:
                continue
            return NotepadPasteResult(
                verified=False,
                retries=attempt,
                first_attempt_success=False,
                recovered=False,
                status=last_status,
                error=last_error,
            )

        if TextInjector.verify_text_injected(expected, hwnd, timeout=5.0):
            first_success = (attempt == 0)
            recovered = (attempt > 0)
            return NotepadPasteResult(
                verified=True,
                retries=attempt,
                first_attempt_success=first_success,
                recovered=recovered,
                status=last_status,
            )

        document = TextInjector.read_window_buffer(hwnd)
        if document is not None and expected.casefold() in document.casefold():
            first_success = (attempt == 0)
            recovered = (attempt > 0)
            return NotepadPasteResult(
                verified=True,
                retries=attempt,
                first_attempt_success=first_success,
                recovered=recovered,
                status=last_status,
            )

        if attempt == 0:
            time.sleep(0.15)
            continue

        if document is None:
            return NotepadPasteResult(
                verified=False,
                retries=attempt,
                first_attempt_success=False,
                recovered=False,
                status="OPAQUE_TARGET",
                error="Document buffer could not be queried via Win32",
            )

    return NotepadPasteResult(
        verified=False,
        retries=1,
        first_attempt_success=False,
        recovered=False,
        status=last_status,
        error=last_error,
    )
