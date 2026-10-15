import sys
import time
import threading
from typing import Optional
import pyperclip

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
    _restore_lock = threading.Lock()
    _restore_timer: Optional[threading.Timer] = None
    _original_clipboard: Optional[str] = None
    _last_copy_seq: Optional[int] = None

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
                return True
            except Exception as e:
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.CloseClipboard()
                    except Exception:
                        pass
                if attempt == max_retries - 1:
                    print(f"[Injector Warning] Clipboard copy failed after {max_retries} attempts: {e}")
                    return False
                time.sleep(retry_delay * (attempt + 1))
        return False

    @classmethod
    def _safe_clipboard_paste(cls, max_retries: int = 5, retry_delay: float = 0.05) -> Optional[str]:
        """Reads text from clipboard with retry backoff and lock recovery."""
        for attempt in range(max_retries):
            try:
                return pyperclip.paste()
            except Exception:
                if sys.platform == "win32":
                    try:
                        import ctypes
                        ctypes.windll.user32.CloseClipboard()
                    except Exception:
                        pass
                if attempt == max_retries - 1:
                    return None
                time.sleep(retry_delay * (attempt + 1))
        return None

    @classmethod
    def _safe_set_foreground(cls, hwnd: int) -> None:
        if not HAS_WIN32 or not hwnd or sys.platform != "win32":
            return
        try:
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.BringWindowToTop(hwnd)
            current_hwnd = win32gui.GetForegroundWindow()
            if current_hwnd == hwnd:
                return

            cur_thread, _ = win32process.GetWindowThreadProcessId(current_hwnd) if current_hwnd else (0, 0)
            target_thread, _ = win32process.GetWindowThreadProcessId(hwnd)

            if cur_thread and target_thread and cur_thread != target_thread:
                win32process.AttachThreadInput(cur_thread, target_thread, True)
                win32gui.SetForegroundWindow(hwnd)
                win32process.AttachThreadInput(cur_thread, target_thread, False)
            else:
                ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
                win32gui.SetForegroundWindow(hwnd)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SwitchToThisWindow(hwnd, True)
                win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
                win32gui.SetForegroundWindow(hwnd)
                win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                pass

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
                if any(x in cname for x in ("edit", "richedit", "document", "scintilla", "terminal")):
                    found.append(child)
            except Exception:
                pass
        try:
            win32gui.EnumChildWindows(hwnd, enum_cb, None)
        except Exception:
            pass
        return found[0] if found else hwnd

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
        if HAS_WIN32 and target_hwnd and sys.platform == "win32":
            if not win32gui.IsWindow(target_hwnd):
                cls.last_injected_text = text
                cls._safe_clipboard_copy(text)
                return InjectionResult(
                    status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
                    error_message=f"Target HWND {target_hwnd} is no longer valid. Preserved in recovery buffer.",
                    recovery_available=True
                )

            # Check if active foreground is target or a child of target
            cur_fg = win32gui.GetForegroundWindow()
            if cur_fg != target_hwnd:
                cls._safe_set_foreground(target_hwnd)
                time.sleep(0.04)
                cur_fg = win32gui.GetForegroundWindow()

                is_descendant = False
                p = cur_fg
                while p:
                    if p == target_hwnd:
                        is_descendant = True
                        break
                    p = win32gui.GetParent(p)

                # Only abort if cur_fg is another distinct window (cur_fg != 0)
                if cur_fg != 0 and cur_fg != target_hwnd and not is_descendant:
                    # Target window lost focus! Abort paste to prevent injecting into wrong app.
                    cls.last_injected_text = text
                    cls._safe_clipboard_copy(text)
                    print(f"[Injector Security] Active focus switched from HWND {target_hwnd} to {cur_fg}. Paste aborted to protect user data.")
                    return InjectionResult(
                        status=InjectionStatus.FAILED_RECOVERY_AVAILABLE,
                        target_hwnd=target_hwnd,
                        error_message="Active window focus changed during processing. Aborted to prevent wrong-window paste; saved to recovery buffer.",
                        recovery_available=True
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
                            if cls.verify_text_injected(check_val, target_hwnd, timeout=0.6):
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

            # 5. Keystroke dispatch (Ctrl+V / Shift+Insert)
            if HAS_WIN32 and sys.platform == "win32":
                if is_legacy_console:
                    win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_INSERT, 0, 0, 0)
                    time.sleep(0.015)
                    win32api.keybd_event(win32con.VK_INSERT, 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                else:
                    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                    win32api.keybd_event(ord('V'), 0, 0, 0)
                    time.sleep(0.015)
                    win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
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
            if verify_confirmation and target_hwnd:
                check_val = expected_token if expected_token is not None else text.strip()
                if cls.verify_text_injected(check_val, target_hwnd, timeout=0.6):
                    return InjectionResult(
                        status=InjectionStatus.CONFIRMED_INSERTED,
                        chars_sent=len(text),
                        target_hwnd=target_hwnd
                    )

            # Standard opaque targets (VS Code, Chrome, etc.) where buffer is not directly readable
            return InjectionResult(
                status=InjectionStatus.SENT_UNVERIFIED,
                chars_sent=len(text),
                target_hwnd=target_hwnd
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
                            # User copied something else (or non-text object); preserve user data
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
                    cls._restore_timer = threading.Timer(1.5, restore_worker)
                    cls._restore_timer.daemon = True
                    cls._restore_timer.start()

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
        """
        if not HAS_WIN32 or sys.platform != "win32":
            return False

        if target_hwnd and win32gui.IsWindow(target_hwnd):
            cls._safe_set_foreground(target_hwnd)
            time.sleep(0.06)

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
            sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
            cls.last_injected_text = text
            print(f"[Injector] Successfully sent {sent // 2} Unicode keystrokes directly to target window.")
            return sent == len(inputs)
        except Exception as e:
            print(f"[Injector Error] SendInput Unicode typing failed: {e}")
            return False

    @classmethod
    def read_window_buffer(cls, target_hwnd: int) -> Optional[str]:
        """
        Safely reads the current document buffer from a window.
        Uses WM_GETTEXT on child edit controls first, falling back to Ctrl+A/Ctrl+C.
        Preserves and restores pre-existing clipboard contents safely.
        """
        if not HAS_WIN32 or not target_hwnd or sys.platform != "win32":
            return None
        if not win32gui.IsWindow(target_hwnd):
            return None

        # Resolve child edit control if available
        edit_ctrl = cls._find_edit_control(target_hwnd)

        # 1. Attempt non-destructive WM_GETTEXT on edit control
        try:
            import ctypes
            length = ctypes.windll.user32.SendMessageW(edit_ctrl, win32con.WM_GETTEXTLENGTH, 0, 0)
            buf_len = max(length + 2, 8192)
            buf = ctypes.create_unicode_buffer(buf_len)
            ctypes.windll.user32.SendMessageW(edit_ctrl, win32con.WM_GETTEXT, buf_len, buf)
            if buf.value:
                return buf.value
        except Exception:
            pass

        # 2. Fall back to focus + Ctrl+A / Ctrl+C with safe clipboard restoration
        orig_clip = cls._safe_clipboard_paste()
        try:
            cls._safe_set_foreground(target_hwnd)
            time.sleep(0.06)

            # Focus the child edit control if different from parent
            if edit_ctrl != target_hwnd:
                try:
                    win32gui.SetFocus(edit_ctrl)
                except Exception:
                    pass
                time.sleep(0.03)

            # Select All (Ctrl+A), Copy (Ctrl+C)
            win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
            win32api.keybd_event(ord('A'), 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(ord('A'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(ord('C'), 0, 0, 0)
            time.sleep(0.04)
            win32api.keybd_event(ord('C'), 0, win32con.KEYEVENTF_KEYUP, 0)
            win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            time.sleep(0.08)

            content = cls._safe_clipboard_paste()

            # Deselect by pressing Right Arrow
            win32api.keybd_event(win32con.VK_RIGHT, 0, 0, 0)
            win32api.keybd_event(win32con.VK_RIGHT, 0, win32con.KEYEVENTF_KEYUP, 0)

            return content
        finally:
            if orig_clip is not None:
                cls._safe_clipboard_copy(orig_clip)
                cls._last_copy_seq = cls._get_clipboard_sequence_number()

    @classmethod
    def verify_text_injected(cls, expected_text: str, target_hwnd: int, timeout: float = 1.0) -> bool:
        """
        Verifies that expected_text was physically received and is present inside the target document buffer.
        """
        start = time.time()
        clean_expected = expected_text.strip().lower()
        while time.time() - start < timeout:
            buf = cls.read_window_buffer(target_hwnd)
            if buf and clean_expected in buf.lower():
                return True
            time.sleep(0.08)
        return False

