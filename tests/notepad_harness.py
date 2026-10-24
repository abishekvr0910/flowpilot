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


def open_test_notepad(timeout: float = 10.0) -> tuple[int, subprocess.Popen, Path]:
    """Open a unique test file and select only its initialized Notepad editor."""
    from engine.text_injector import TextInjector

    fd, filename = tempfile.mkstemp(prefix="flowpilot-audit-", suffix=".txt")
    os.close(fd)
    fixture = Path(filename)
    process = subprocess.Popen(["notepad.exe", str(fixture)])
    deadline = time.monotonic() + timeout
    observed = []
    while time.monotonic() < deadline:
        candidates = []
        observed = []

        def _find(hwnd, _):
            try:
                if win32gui.IsWindowVisible(hwnd) and win32gui.GetClassName(hwnd) == "Notepad":
                    title = win32gui.GetWindowText(hwnd)
                    edit = TextInjector._find_edit_control(hwnd)
                    ready = edit != hwnd and win32gui.GetClassName(edit) in ("RichEditD2DPT", "Edit", "NotepadTextBox")
                    if fixture.name.casefold() in title.casefold():
                        observed.append((hwnd, title, ready))
                    if fixture.name.casefold() in title.casefold() and ready:
                        candidates.append(hwnd)
            except Exception:
                pass
            return True

        win32gui.EnumWindows(_find, None)
        if candidates:
            return candidates[0], process, fixture
        time.sleep(0.1)

    cleanup_test_fixture(fixture, process=process)
    raise RuntimeError(f"Notepad did not expose an editable document for {fixture.name}; observed={observed!r}, launcher_exit={process.poll()}.")


def cleanup_test_fixture(fixture: Optional[Path], hwnd: int = 0, process: Optional[subprocess.Popen] = None) -> None:
    """Close only the matching synthetic tab; never terminate a shared Notepad process."""
    from engine.text_injector import TextInjector

    if fixture is None:
        return
    if hwnd and win32gui.IsWindow(hwnd) and fixture.name.casefold() in win32gui.GetWindowText(hwnd).casefold():
        if focus_notepad_document(hwnd, timeout=2.0):
            for key in (ord("S"), ord("W")):
                win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                win32api.keybd_event(key, 0, 0, 0)
                win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
                win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
                time.sleep(0.2)
    still_open = bool(hwnd and win32gui.IsWindow(hwnd) and
                      fixture.name.casefold() in win32gui.GetWindowText(hwnd).casefold())
    if still_open and hwnd and win32gui.IsWindow(hwnd):
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            time.sleep(0.3)
            still_open = bool(win32gui.IsWindow(hwnd) and
                              fixture.name.casefold() in win32gui.GetWindowText(hwnd).casefold())
        except Exception:
            pass
    if not still_open:
        try:
            fixture.unlink(missing_ok=True)
        except OSError:
            pass
    else:
        print(f"[Notepad harness] Synthetic tab still open; retained fixture {fixture.name} for safe recovery.")
    if process and process.poll() is None:
        owned_windows = []
        def _owned(candidate, _):
            try:
                if win32gui.GetClassName(candidate) == "Notepad" and win32process.GetWindowThreadProcessId(candidate)[1] == process.pid:
                    owned_windows.append(candidate)
            except Exception:
                pass
            return True
        win32gui.EnumWindows(_owned, None)
        if not owned_windows:
            process.terminate()


class NotepadPasteResult(NamedTuple):
    verified: bool
    retries: int
    first_attempt_success: bool = True
    recovered: bool = False
    status: str = ""
    error: Optional[str] = None


def is_interactive_desktop() -> bool:
    """Returns True if the current thread is attached to the active interactive input desktop."""
    import sys
    if os.environ.get("FLOWPILOT_HEADLESS") == "1" or os.environ.get("QT_QPA_PLATFORM", "").lower() == "offscreen":
        return False
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        # Hosted Windows runners can expose a Notepad shell without a usable
        # RichEdit document or hardware-input desktop.
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
        return name_cur.value.lower() == name_input.value.lower()
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
    """Forcefully foreground a window, tolerating the background-window
    SetForegroundWindow restriction. On Windows 11 the modern (Store) Notepad
    runs each window in its own process; a sibling instance's shell window can
    own the foreground and silently defeat a plain SetForegroundWindow call.
    Uses the canonical AttachThreadInput recipe (attach caller + foreground
    thread + target thread, raise the target, detach)."""
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
                if hasattr(win32gui, "IsChild") and (win32gui.IsChild(edit, foc) or win32gui.IsChild(foc, edit)):
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
    print(f"[Notepad harness] Document focus unavailable: target={hwnd}, "
          f"edit_class={win32gui.GetClassName(edit) if edit else None}, "
          f"foreground_class={win32gui.GetClassName(fg) if fg else None}")
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

        # Legitimate product injection on every attempt; no artificial backdoors
        result = TextInjector.inject_with_status(text, hwnd)
        last_status = str(result.status)
        last_error = result.error_message

        if result.status not in (InjectionStatus.SENT_UNVERIFIED, InjectionStatus.CONFIRMED_INSERTED):
            if result.status == InjectionStatus.FAILED_RECOVERY_AVAILABLE and attempt == 0:
                continue  # Target window was not ready or focus changed; allow one recovery attempt
            return NotepadPasteResult(
                verified=False,
                retries=attempt,
                first_attempt_success=False,
                recovered=False,
                status=last_status,
                error=last_error,
            )

        if TextInjector.verify_text_injected(expected, hwnd, timeout=2.0):
            first_success = (attempt == 0)
            recovered = (attempt > 0)
            return NotepadPasteResult(
                verified=True,
                retries=attempt,
                first_attempt_success=first_success,
                recovered=recovered,
                status=last_status,
            )

        # Catch any text that appeared at the polling boundary
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
