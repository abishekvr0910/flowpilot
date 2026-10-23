import os
import sys
import time
import threading
from typing import Optional
import pyperclip
import psutil

from enum import Enum
from dataclasses import dataclass

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class InjectionStatus(str, Enum):
    """Authoritative truthfulness states for text injection."""
    CONFIRMED_INSERTED = "CONFIRMED_INSERTED"            # Physical presence confirmed in target buffer
    SENT_UNVERIFIED = "SENT_UNVERIFIED"                  # Keystrokes sent to verified focus; target buffer unreadable
    FAILED_RECOVERY_AVAILABLE = "FAILED_RECOVERY_AVAILABLE"  # Target lost or paste failed; text preserved in recovery
    CANCELLED = "CANCELLED"                              # Dictation session was cancelled
    ERROR = "ERROR"                                      # Technical exception occurred

@dataclass
class InjectionResult:
    """Structured result returned by TextInjector."""
    status: InjectionStatus
    chars_sent: int = 0
    target_hwnd: Optional[int] = None
    target_title: str = ""
    target_class: str = ""
    error_message: Optional[str] = None
    recovery_available: bool = True

    def __bool__(self) -> bool:
        """Backward-compatible boolean evaluation: True if sent or confirmed."""
        return self.status in (InjectionStatus.CONFIRMED_INSERTED, InjectionStatus.SENT_UNVERIFIED)

    def is_confirmed(self) -> bool:
        return self.status == InjectionStatus.CONFIRMED_INSERTED

class TextInjector:
    """
    High-reliability Windows text injector with authoritative truthfulness contracts.
    - Truthful result statuses: CONFIRMED_INSERTED vs SENT_UNVERIFIED vs FAILED_RECOVERY_AVAILABLE.
    - Focus-verified dispatch: aborts if active foreground switched away from target window.
    - Robust against Windows clipboard lock contention (retry loop with backoff).
    - Preserves existing clipboard contents safely without racing.
    - Verifies target window focus and uses AttachThreadInput / SwitchToThisWindow.
    - Handles terminal consoles and Unicode scripts cleanly.
    - Provides in-memory recovery buffer for instant manual re-copying.
    """

    last_injected_text: str = ""
    last_target_hwnd: Optional[int] = None
    last_target_title: str = ""
    _restore_lock = threading.Lock()
    _restore_timer: Optional[threading.Timer] = None
    _original_clipboard: Optional[str] = None
    _last_copy_seq: Optional[int] = None

    @classmethod
    def _is_flowpilot_window(cls, hwnd: Optional[int]) -> bool:
        """Determines if a window handle belongs to FlowPilot itself."""
        if not HAS_WIN32 or not hwnd or sys.platform != "win32":
            return False
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid == os.getpid():
                return True
            title = win32gui.GetWindowText(hwnd).lower()
            if "flowpilot" in title:
                return True
        except Exception:
            pass
        return False

    # Performance-sensitive applications requiring extended clipboard hold and key dwell
    SLOW_APP_PROCESSES = {
        "slack.exe", "teams.exe", "ms-teams.exe", "discord.exe", "notion.exe",
        "outlook.exe", "winword.exe", "powerpnt.exe", "excel.exe", "whatsapp.exe",
        "code.exe", "cursor.exe", "devenv.exe", "pycharm64.exe", "idea64.exe",
        "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "obsidian.exe"
    }

    REMOTE_APP_PROCESSES = {
        "mstsc.exe", "vncviewer.exe", "anydesk.exe", "teamviewer.exe", "vmware.exe", "virtualboxvm.exe"
    }

    @classmethod
    def _get_target_process_name(cls, hwnd: Optional[int]) -> str:
        """Determines process binary name for a given HWND."""
        if not HAS_WIN32 or not hwnd or sys.platform != "win32":
            return ""
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name().lower()
        except Exception:
            return ""

    @classmethod
    def _get_clipboard_sequence_number(cls) -> Optional[int]:
        """Returns Win32 GetClipboardSequenceNumber() or fallback content hash integer on non-Windows."""
        if HAS_WIN32 and sys.platform == "win32":
            try:
                import ctypes
                return int(ctypes.windll.user32.GetClipboardSequenceNumber())
            except Exception:
                return None
        else:
            try:
                import hashlib
                clip = cls._safe_clipboard_paste() or ""
                return int(hashlib.md5(clip.encode("utf-8", errors="ignore")).hexdigest()[:8], 16)
            except Exception:
                return None

    @classmethod
    def _safe_clipboard_copy(cls, text: str, max_retries: int = 8, retry_delay: float = 0.08) -> bool:
        """Copies text to clipboard with retry backoff and lock recovery to survive OpenClipboard locks."""
        for attempt in range(max_retries):
            try:
                pyperclip.copy(text)
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.kernel32.SetLastError(0)
                    except Exception:
                        pass
                return True
            except Exception as e:
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.CloseClipboard()
                        ctypes.windll.kernel32.SetLastError(0)
                    except Exception:
                        pass
                if attempt == max_retries - 1:
                    print(f"[Injector Warning] Clipboard copy failed after {max_retries} attempts: {e}")
                    if sys.platform == "win32":
                        try:
                            import ctypes
                            ctypes.windll.kernel32.SetLastError(0)
                        except Exception:
                            pass
                    return False
                time.sleep(retry_delay * (attempt + 1))
        return False

    @classmethod
    def _safe_clipboard_paste(cls, max_retries: int = 5, retry_delay: float = 0.05) -> Optional[str]:
        """Reads text from clipboard with retry backoff and lock recovery."""
        for attempt in range(max_retries):
            try:
                res = pyperclip.paste()
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.kernel32.SetLastError(0)
                    except Exception:
                        pass
                return res
            except Exception:
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.CloseClipboard()
                        ctypes.windll.kernel32.SetLastError(0)
                    except Exception:
                        pass
                if attempt == max_retries - 1:
                    if sys.platform == "win32":
                        try:
                            import ctypes
                            ctypes.windll.kernel32.SetLastError(0)
                        except Exception:
                            pass
                    return None
                time.sleep(retry_delay * (attempt + 1))
        return None

    @classmethod
    def _safe_set_foreground(cls, hwnd: int) -> bool:
        """
        Forcefully foreground a window, tolerating background-window
        SetForegroundWindow restrictions across Windows 10 and 11.
        Uses the canonical AttachThreadInput recipe (caller thread + foreground
        thread + target thread) with Alt-key lock bypass and BringWindowToTop.
        """
        if not HAS_WIN32 or not hwnd or sys.platform != "win32":
            return False
        try:
            if win32gui.GetForegroundWindow() == hwnd:
                return True

            import ctypes
            try:
                ctypes.windll.user32.AllowSetForegroundWindow(-1)
            except Exception:
                pass
            try:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            except Exception:
                pass

            fg = win32gui.GetForegroundWindow()
            fg_tid = win32process.GetWindowThreadProcessId(fg)[0] if fg else 0
            target_tid = win32process.GetWindowThreadProcessId(hwnd)[0] if hwnd else 0
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

            alt_pressed = False
            try:
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                alt_pressed = True
                win32gui.BringWindowToTop(hwnd)
                win32gui.SetForegroundWindow(hwnd)
            except Exception:
                pass
            finally:
                if alt_pressed:
                    try:
                        win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
                    except Exception:
                        pass
                for a, b in reversed(attached):
                    try:
                        win32process.AttachThreadInput(a, b, False)
                    except Exception:
                        pass

            if win32gui.GetForegroundWindow() != hwnd:
                try:
                    ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
                    win32gui.SetForegroundWindow(hwnd)
                except Exception:
                    pass

            return win32gui.GetForegroundWindow() == hwnd
        except Exception:
            return False

    @classmethod
    def _is_same_window_hierarchy(cls, hwnd1: int, hwnd2: int) -> bool:
        """Determines if two window handles share the same root ancestor window."""
        if not HAS_WIN32 or not hwnd1 or not hwnd2:
            return hwnd1 == hwnd2
        if hwnd1 == hwnd2:
            return True
        try:
            root1 = win32gui.GetAncestor(hwnd1, win32con.GA_ROOT) or hwnd1
            root2 = win32gui.GetAncestor(hwnd2, win32con.GA_ROOT) or hwnd2
            return root1 == root2
        except Exception:
            return False

    @classmethod
    def _resolve_verified_foreground(
        cls,
        target_hwnd: Optional[int],
        max_attempts: int = 5,
        delay: float = 0.02
    ) -> tuple[bool, int, Optional[str]]:
        """
        Verifies that target_hwnd (or a window within its root hierarchy) holds active foreground.
        Per Microsoft Win32 documentation, GetForegroundWindow() can return NULL (0) during an
        activation change. Treating 0 as permission to paste is unsafe as keystrokes will be
        misdirected or dropped.

        This method briefly polls (up to max_attempts * delay = 100ms) to allow transient activation
        changes to settle. If focus remains 0 or belongs to another application, it returns
        (False, current_fg, error_message).
        """
        if not HAS_WIN32 or sys.platform != "win32":
            return True, 0, None

        for _ in range(max_attempts):
            cur_fg = win32gui.GetForegroundWindow()
            if cur_fg != 0:
                if not target_hwnd or cur_fg == target_hwnd or cls._is_same_window_hierarchy(target_hwnd, cur_fg):
                    return True, cur_fg, None
                else:
                    return (
                        False,
                        cur_fg,
                        f"Active focus switched from HWND {target_hwnd} to {cur_fg}."
                    )
            time.sleep(delay)

        return (
            False,
            0,
            f"Active foreground window is unknown (0) after {max_attempts} checks ({max_attempts * delay * 1000:.0f}ms). "
            f"Activation change in progress or no foreground window; paste retained in recovery buffer."
        )

    @classmethod
    def re_copy_last(cls) -> bool:
        """Copies the last transcribed/injected text back into the system clipboard."""
        if cls.last_injected_text:
            return cls._safe_clipboard_copy(cls.last_injected_text)
        return False

    @classmethod
    def _find_edit_control(cls, hwnd: int) -> int:
        """Resolves the child edit control inside a window (e.g. Notepad, RichEdit) if present."""
        if not HAS_WIN32 or not hwnd or sys.platform != "win32":
            return hwnd
        found = []
        def enum_cb(child, _):
            try:
                cname = win32gui.GetClassName(child).lower()
                if any(x in cname for x in ("edit", "richedit", "document", "scintilla", "terminal", "textbox")):
                    found.append(child)
            except Exception:
                pass
            return True
        try:
            win32gui.EnumChildWindows(hwnd, enum_cb, None)
        except Exception:
            pass
        if not found:
            return hwnd
        # When an outer container matches (such as WinUI's NotepadTextBox wrapping
        # RichEditD2DPT), resolve the innermost leaf edit control that actually
        # owns document caret and responds to WM_GETTEXT.
        if len(found) > 1 and hasattr(win32gui, "IsChild"):
            try:
                leaves = [c for c in found if not any(win32gui.IsChild(c, other) for other in found if other != c)]
                if leaves:
                    return leaves[0]
            except Exception:
                pass
        return found[0]

    @classmethod
    def inject_with_status(
        cls,
        text: str,
        target_hwnd: Optional[int] = None,
        preserve_clipboard: bool = True,
        verify_confirmation: bool = False,
        expected_token: Optional[str] = None
    ) -> InjectionResult:
        """
        Truthful text injection with authoritative result statuses:
        - CONFIRMED_INSERTED: Physical verification succeeded in target buffer.
        - SENT_UNVERIFIED: Keystrokes dispatched to verified focus; target is opaque/unreadable.
        - FAILED_RECOVERY_AVAILABLE: Target window focus changed or invalid; saved to recovery.
        - ERROR: Exception or technical failure.
        """
        if not text:
            return InjectionResult(status=InjectionStatus.ERROR, error_message="Empty text provided.")

        # 1. Target window existence and focus security check
        if HAS_WIN32 and sys.platform == "win32":
            if target_hwnd:
                if not win32gui.IsWindow(target_hwnd):
                    cls.last_injected_text = text
                    return InjectionResult(
                        status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
                        error_message=f"Target HWND {target_hwnd} is no longer valid. Preserved in recovery buffer.",
                        recovery_available=True
                    )

                # Check if active foreground is target or shares hierarchy with target
                cur_fg = win32gui.GetForegroundWindow()
                if cur_fg != target_hwnd and not cls._is_same_window_hierarchy(target_hwnd, cur_fg):
                    cls._safe_set_foreground(target_hwnd)
                    time.sleep(0.04)

            # Validate that a known, genuine foreground window exists before any clipboard work
            ok, cur_fg, err_msg = cls._resolve_verified_foreground(target_hwnd)
            if not ok:
                cls.last_injected_text = text
                print(f"[Injector Security] {err_msg} Paste aborted; saved to recovery buffer.")
                return InjectionResult(
                    status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
                    target_hwnd=target_hwnd,
                    error_message=err_msg,
                    recovery_available=True
                )

        # A token that was already in the document is not proof this paste
        # arrived. Record the target buffer before dispatch for comparison.
        before_buffer = (
            cls.read_window_buffer(target_hwnd)
            if verify_confirmation and target_hwnd else None
        )

        # 2. Coordinate clipboard backup without race conditions
        with cls._restore_lock:
            if cls._restore_timer is not None:
                cls._restore_timer.cancel()
                cls._restore_timer = None
            if preserve_clipboard:
                current_clip = cls._safe_clipboard_paste()
                if current_clip != cls.last_injected_text or cls._original_clipboard is None:
                    cls._original_clipboard = current_clip

        cls.last_injected_text = text

        # Safely track intended target editor for recovery and "Paste Last"
        intended_editor = target_hwnd or (cur_fg if ('cur_fg' in locals() and cur_fg) else None)
        if intended_editor and not cls._is_flowpilot_window(intended_editor):
            cls.last_target_hwnd = intended_editor
            if HAS_WIN32 and sys.platform == "win32":
                try:
                    cls.last_target_title = win32gui.GetWindowText(intended_editor)
                except Exception:
                    pass

        # Determine target application performance profile before try block (Wispr slow-app guidance)
        cur_fg_proc = cur_fg if (HAS_WIN32 and sys.platform == "win32" and 'cur_fg' in locals()) else None
        target_proc = cls._get_target_process_name(target_hwnd or cur_fg_proc)
        is_remote = target_proc in cls.REMOTE_APP_PROCESSES
        is_slow = (target_proc in cls.SLOW_APP_PROCESSES) or is_remote
        key_dwell_sec = 0.050 if is_remote else (0.040 if is_slow else 0.02)
        post_paste_delay = 0.15 if is_remote else (0.10 if is_slow else 0.06)
        clipboard_hold_sec = 5.0 if is_remote else (3.5 if is_slow else 1.8)

        try:
            # 3. Copy text to clipboard with lock retry
            if not cls._safe_clipboard_copy(text):
                # Attempt direct Win32 EM_REPLACESEL on child edit control (e.g. RichEditD2DPT / Edit)
                edit_ctrl = cls._find_edit_control(target_hwnd) if target_hwnd else None
                if edit_ctrl and edit_ctrl != target_hwnd:
                    try:
                        import ctypes
                        ctypes.windll.user32.SendMessageW(edit_ctrl, 0x00C2, 1, text)
                        cls.last_injected_text = text
                        if verify_confirmation and target_hwnd:
                            check_val = expected_token if expected_token is not None else text.strip()
                            if cls._verify_new_text_injected(check_val, target_hwnd, before_buffer, timeout=0.6):
                                return InjectionResult(
                                    status=InjectionStatus.CONFIRMED_INSERTED,
                                    chars_sent=len(text),
                                    target_hwnd=target_hwnd
                                )
                        return InjectionResult(status=InjectionStatus.SENT_UNVERIFIED, chars_sent=len(text), target_hwnd=target_hwnd)
                    except Exception:
                        pass

                print("[Injector Warning] Clipboard copy failed. Falling back to direct SendInput Unicode typing...")
                typed_ok = cls.inject_unicode_sendinput(text, target_hwnd)
                if typed_ok:
                    return InjectionResult(status=InjectionStatus.SENT_UNVERIFIED, chars_sent=len(text), target_hwnd=target_hwnd)
                return InjectionResult(status=InjectionStatus.ERROR, error_message="Direct injection and clipboard copy failed.")
            time.sleep(0.015)
            post_copy_seq = cls._get_clipboard_sequence_number()
            cls._last_copy_seq = post_copy_seq

            # 4. Detect legacy console requiring Shift+Insert
            is_legacy_console = False
            if HAS_WIN32 and target_hwnd and sys.platform == "win32":
                try:
                    cls_name = win32gui.GetClassName(target_hwnd)
                    if cls_name in ("ConsoleWindowClass",):
                        is_legacy_console = True
                except Exception:
                    pass

                # Clipboard setup can yield long enough for another window to
                # take focus. Never send Ctrl+V to that unrelated application or during activation changes.
                ok, cur_fg_now, err_msg = cls._resolve_verified_foreground(target_hwnd)
                if not ok:
                    cls.last_injected_text = text
                    # Preserve original clipboard immediately so the newly focused application is not clobbered
                    if preserve_clipboard and cls._original_clipboard is not None:
                        cur_seq = cls._get_clipboard_sequence_number()
                        cur_clip = cls._safe_clipboard_paste()
                        if (cls._last_copy_seq is not None and cur_seq is not None and cur_seq != cls._last_copy_seq) or (cur_clip is not None and cur_clip != text and cur_clip.strip() != text.strip()):
                            print(f"[Injector Security] Clipboard changed during focus loss ({cls._last_copy_seq} -> {cur_seq}). Skipping restore to protect user's newer copy.")
                        else:
                            cls._safe_clipboard_copy(cls._original_clipboard)
                        with cls._restore_lock:
                            cls._original_clipboard = None
                    print(f"[Injector Security] {err_msg} Paste aborted; saved to recovery buffer.")
                    return InjectionResult(
                        status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
                        target_hwnd=target_hwnd,
                        error_message=err_msg,
                        recovery_available=True,
                    )

            # 5. Keystroke dispatch (Ctrl+V / Shift+Insert)
            if HAS_WIN32 and sys.platform == "win32":
                if is_legacy_console:
                    win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_INSERT, 0, 0, 0)
                    time.sleep(key_dwell_sec)
                    win32api.keybd_event(win32con.VK_INSERT, 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                else:
                    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                    win32api.keybd_event(ord('V'), 0, 0, 0)
                    time.sleep(key_dwell_sec)
                    win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
                    time.sleep(post_paste_delay)
            elif sys.platform == "darwin":
                # macOS Cmd+V
                try:
                    from pynput.keyboard import Controller, Key
                    kb = Controller()
                    kb.press(Key.cmd)
                    kb.press('v')
                    time.sleep(0.015)
                    kb.release('v')
                    kb.release(Key.cmd)
                except Exception:
                    try:
                        import subprocess
                        subprocess.run(["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'], check=False, timeout=0.2)
                    except Exception:
                        pass
            else:
                # Linux (X11 / Wayland) Ctrl+V
                try:
                    from pynput.keyboard import Controller, Key
                    kb = Controller()
                    kb.press(Key.ctrl)
                    kb.press('v')
                    time.sleep(0.015)
                    kb.release('v')
                    kb.release(Key.ctrl)
                except Exception:
                    try:
                        import subprocess
                        subprocess.run(["xdotool", "key", "--clearmodifiers", "ctrl+v"], check=False, timeout=0.2)
                    except Exception:
                        pass

            print(f"[Injector] Successfully dispatched {len(text)} characters to HWND {target_hwnd}.")

            # 6. Physical confirmation verification if requested
            effective_target = target_hwnd or (cur_fg if ('cur_fg' in locals() and cur_fg) else None)
            if verify_confirmation and effective_target:
                check_val = expected_token if expected_token is not None else text.strip()
                if cls._verify_new_text_injected(check_val, effective_target, before_buffer, timeout=0.6):
                    return InjectionResult(
                        status=InjectionStatus.CONFIRMED_INSERTED,
                        chars_sent=len(text),
                        target_hwnd=effective_target
                    )

            # Standard opaque targets where buffer is not directly readable
            return InjectionResult(
                status=InjectionStatus.SENT_UNVERIFIED,
                chars_sent=len(text),
                target_hwnd=effective_target or target_hwnd
            )

        except Exception as e:
            print(f"[Injector Warning] Standard clipboard paste failed ({e}). Attempting direct SendInput Unicode fallback...")
            typed_ok = cls.inject_unicode_sendinput(text, target_hwnd)
            if typed_ok:
                return InjectionResult(status=InjectionStatus.SENT_UNVERIFIED, chars_sent=len(text), target_hwnd=target_hwnd)
            return InjectionResult(status=InjectionStatus.ERROR, error_message=str(e))

        finally:
            # 7. Safe clipboard restore: only restore if clipboard still holds our injected text
            if preserve_clipboard and cls._original_clipboard is not None and cls._original_clipboard != text:
                saved_to_restore = cls._original_clipboard
                def restore_worker():
                    try:
                        # 1. Content matching check: only restore if clipboard still holds our injected text
                        current = cls._safe_clipboard_paste()
                        if not current or (current != text and current.strip() != text.strip()):
                            return

                        # 2. Check atomic Win32 clipboard sequence counter:
                        # If sequence moved since FlowPilot's last write, user made a newer copy event
                        cur_seq = cls._get_clipboard_sequence_number()
                        if cls._last_copy_seq is not None and cur_seq is not None and cur_seq != cls._last_copy_seq:
                            print(f"[Injector Security] Clipboard sequence changed ({cls._last_copy_seq} -> {cur_seq}). Skipping restore to protect user's newer copy.")
                            return

                        cls._safe_clipboard_copy(saved_to_restore)
                        cls._last_copy_seq = cls._get_clipboard_sequence_number()
                    except Exception as e:
                        print(f"[Injector Notice] Clipboard restore skipped: {e}")
                    finally:
                        with cls._restore_lock:
                            cls._original_clipboard = None
                            cls._restore_timer = None

                with cls._restore_lock:
                    cls._restore_timer = threading.Timer(clipboard_hold_sec, restore_worker)
                    cls._restore_timer.daemon = True
                    cls._restore_timer.start()

    @classmethod
    def inject_last(cls, target_hwnd: Optional[int] = None) -> InjectionResult:
        """
        Re-injects the last dictated/formatted text into the intended target editor safely.
        If invoked from FlowPilot's dashboard, tray, or background hotkey,
        it automatically brings the intended external editor to the foreground.
        Never fires blind Ctrl+V into FlowPilot or unknown windows.
        """
        if not cls.last_injected_text:
            return InjectionResult(
                status=InjectionStatus.ERROR,
                error_message="No previous dictation text found in recovery buffer.",
                recovery_available=False
            )

        cur_fg = win32gui.GetForegroundWindow() if (HAS_WIN32 and sys.platform == "win32") else 0

        # Resolve intended target window
        chosen_target: Optional[int] = None
        if target_hwnd is not None and not cls._is_flowpilot_window(target_hwnd):
            chosen_target = target_hwnd
        elif cur_fg and not cls._is_flowpilot_window(cur_fg):
            chosen_target = cur_fg
        elif cls.last_target_hwnd and not cls._is_flowpilot_window(cls.last_target_hwnd):
            chosen_target = cls.last_target_hwnd

        if not chosen_target:
            # Safety invariant: Do not dispatch keystrokes to an unknown or FlowPilot window.
            # Safely place the text onto clipboard for user manual paste.
            cls._safe_clipboard_copy(cls.last_injected_text)
            return InjectionResult(
                status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
                error_message="Intended editor window is not open. Last dictation copied to clipboard for safe manual paste (Ctrl+V).",
                recovery_available=True
            )

        # Bring the intended editor to front if it isn't currently active
        if HAS_WIN32 and sys.platform == "win32":
            if cur_fg != chosen_target:
                cls._safe_set_foreground(chosen_target)
                time.sleep(0.08)

        return cls.inject_with_status(cls.last_injected_text, target_hwnd=chosen_target)

    @classmethod
    def inject(cls, text: str, target_hwnd: Optional[int] = None, preserve_clipboard: bool = True) -> bool:
        """Backward-compatible inject call returning True on sent/confirmed, False on failure."""
        res = cls.inject_with_status(text, target_hwnd, preserve_clipboard=preserve_clipboard)
        return bool(res)

    @classmethod
    def inject_unicode_sendinput(cls, text: str, target_hwnd: Optional[int] = None) -> bool:
        """
        Direct-typing fallback via Windows SendInput with KEYEVENTF_UNICODE.
        Bypasses the system clipboard entirely and types characters directly into the target control.
        Guarded: verifies target foreground focus before dispatching any keystrokes.
        """
        if not HAS_WIN32 or sys.platform != "win32":
            return False

        if target_hwnd and win32gui.IsWindow(target_hwnd):
            cls._safe_set_foreground(target_hwnd)
            time.sleep(0.06)

        # Guarded foreground verification before any physical SendInput dispatch
        ok, cur_fg, err_msg = cls._resolve_verified_foreground(target_hwnd)
        if not ok:
            cls.last_injected_text = text
            print(f"[Injector Security] {err_msg} SendInput fallback aborted; target unverified.")
            return False

        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ('wVk', wintypes.WORD),
                    ('wScan', wintypes.WORD),
                    ('dwFlags', wintypes.DWORD),
                    ('time', wintypes.DWORD),
                    ('dwExtraInfo', ctypes.c_ulong)
                ]

            class INPUT(ctypes.Structure):
                class _INPUT(ctypes.Union):
                    _fields_ = [('ki', KEYBDINPUT)]
                _anonymous_ = ('_input',)
                _fields_ = [('type', wintypes.DWORD), ('_input', _INPUT)]

            KEYEVENTF_KEYUP = 0x0002
            KEYEVENTF_UNICODE = 0x0004
            VK_RETURN = 0x0D

            inputs = []
            for ch in text:
                if ch == '\r':
                    continue
                if ch == '\n':
                    inp_down = INPUT(type=1)
                    inp_down.ki.wVk = VK_RETURN
                    inp_up = INPUT(type=1)
                    inp_up.ki.wVk = VK_RETURN
                    inp_up.ki.dwFlags = KEYEVENTF_KEYUP
                    inputs.extend([inp_down, inp_up])
                else:
                    code = ord(ch)
                    inp_down = INPUT(type=1)
                    inp_down.ki.wScan = code
                    inp_down.ki.dwFlags = KEYEVENTF_UNICODE
                    inp_up = INPUT(type=1)
                    inp_up.ki.wScan = code
                    inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
                    inputs.extend([inp_down, inp_up])

            if not inputs:
                return True

            arr = (INPUT * len(inputs))(*inputs)
            # Preparing a long Unicode sequence can outlast a focus change.
            ok, cur_fg, err_msg = cls._resolve_verified_foreground(target_hwnd)
            if not ok:
                cls.last_injected_text = text
                print(f"[Injector Security] {err_msg} SendInput dispatch aborted; target unverified.")
                return False
            sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
            cls.last_injected_text = text
            print(f"[Injector] Successfully sent {sent // 2} Unicode keystrokes directly to target window.")
            return sent == len(inputs)
        except Exception as e:
            print(f"[Injector Error] SendInput Unicode typing failed: {e}")
            return False

    @classmethod
    def _read_via_ui_automation(cls, target_hwnd: int) -> Optional[str]:
        """
        Reads document text via Microsoft UI Automation from target_hwnd.
        Handles IUIAutomationTextPattern and IUIAutomationValuePattern across
        WinUI 3 Notepad, Chromium, Electron, Microsoft Word, and Qt surfaces.
        """
        if not HAS_WIN32 or not target_hwnd or sys.platform != "win32":
            return None
        try:
            import pythoncom
            pythoncom.CoInitialize()
            import comtypes.client
            mod = comtypes.client.GetModule("UIAutomationCore.dll")
            if not hasattr(cls, "_uia_instance") or cls._uia_instance is None:
                cls._uia_instance = comtypes.client.CreateObject(mod.CUIAutomation)
            uia = cls._uia_instance
            elem = uia.ElementFromHandle(target_hwnd)
            if not elem:
                return None

            walker = uia.RawViewWalker

            # Breadth-first search of UI elements for document text or edit value
            queue = [elem]
            visited = 0
            while queue and visited < 30:
                current = queue.pop(0)
                visited += 1

                # Query TextPattern for document surfaces
                try:
                    tp = current.GetCurrentPattern(mod.UIA_TextPatternId)
                    if tp:
                        t_obj = tp.QueryInterface(mod.IUIAutomationTextPattern)
                        txt = t_obj.DocumentRange.GetText(100000)
                        if txt and txt.strip():
                            return txt
                except Exception:
                    pass

                # Query ValuePattern for input fields (excluding top-level window titles)
                if current != elem:
                    try:
                        vp = current.GetCurrentPattern(mod.UIA_ValuePatternId)
                        if vp:
                            v_obj = vp.QueryInterface(mod.IUIAutomationValuePattern)
                            val = v_obj.CurrentValue
                            if val and val.strip() and val.strip() != "python":
                                return val
                    except Exception:
                        pass

                # Enqueue children for traversal
                try:
                    child = walker.GetFirstChildElement(current)
                    while child:
                        queue.append(child)
                        child = walker.GetNextSiblingElement(child)
                except Exception:
                    pass

            return None
        except Exception:
            return None

    @classmethod
    def read_window_buffer(cls, target_hwnd: int) -> Optional[str]:
        """
        Read a Win32 or modern document buffer without changing focus or clipboard.
        First tries Win32 WM_GETTEXT on leaf edit controls if available.
        Falls back to Microsoft UI Automation for modern WinUI 3 Notepad,
        Chromium, Electron, Office, and Qt editor surfaces.

        Opaque controls return None, never a clipboard value masquerading as
        physical proof that the text arrived in the intended field.
        """
        if not HAS_WIN32 or not target_hwnd or sys.platform != "win32":
            return None
        if not win32gui.IsWindow(target_hwnd):
            return None

        # 1. Win32 WM_GETTEXT on child edit control (Notepad legacy, Edit, RichEdit)
        edit_ctrl = cls._find_edit_control(target_hwnd)
        if edit_ctrl and edit_ctrl != target_hwnd and win32gui.IsWindow(edit_ctrl):
            try:
                import ctypes
                user32 = ctypes.windll.user32
                send_timeout = user32.SendMessageTimeoutW
                send_timeout.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t,
                                         ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint,
                                         ctypes.POINTER(ctypes.c_size_t))
                send_timeout.restype = ctypes.c_void_p
                result = ctypes.c_size_t()
                if send_timeout(edit_ctrl, win32con.WM_GETTEXTLENGTH,
                                    0, None, 0x0002, 150, ctypes.byref(result)):
                    buf_len = min(result.value, 100000) + 1
                    buf = ctypes.create_unicode_buffer(buf_len)
                    if send_timeout(edit_ctrl, win32con.WM_GETTEXT,
                                        buf_len, ctypes.cast(buf, ctypes.c_void_p),
                                        0x0002, 150, ctypes.byref(result)):
                        if buf.value:
                            return buf.value
            except Exception:
                pass

        # 2. Modern UI Automation fallback (WinUI 3 Notepad, Chromium, Electron, Office, Qt)
        return cls._read_via_ui_automation(target_hwnd)

    @classmethod
    def verify_text_injected(cls, expected_text: str, target_hwnd: int, timeout: float = 2.5) -> bool:
        """
        Check physical presence in a document buffer. This does not prove that
        a new paste occurred when the text was already present beforehand.
        """
        start = time.time()
        clean_expected = expected_text.strip().lower()
        if not clean_expected:
            return True
        prefix = clean_expected[:40].strip()
        while time.time() - start < timeout:
            buf = cls.read_window_buffer(target_hwnd)
            if buf:
                buf_lower = buf.lower()
                if clean_expected in buf_lower or (prefix and prefix in buf_lower):
                    return True
            time.sleep(0.06)
        return False

    @classmethod
    def _verify_new_text_injected(
        cls, expected_text: str, target_hwnd: int,
        before_buffer: Optional[str], timeout: float = 0.6
    ) -> bool:
        """Confirm delivery only when the expected text appears more often than before."""
        expected = expected_text.strip().casefold()
        if before_buffer is None or not expected:
            return False
        before_count = before_buffer.casefold().count(expected)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            after_buffer = cls.read_window_buffer(target_hwnd)
            if after_buffer is not None and after_buffer.casefold().count(expected) > before_count:
                return True
            time.sleep(0.06)
        return False

