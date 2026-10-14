import sys
import time
from typing import Optional
import pyperclip

try:
    import win32gui
    import win32con
    import win32api
    import win32process
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class TextInjector:
    """
    High-reliability Windows text injector.
    - Robust against Windows clipboard lock contention (retry loop with backoff).
    - Preserves existing clipboard contents safely without racing.
    - Verifies target window focus and uses AttachThreadInput / SwitchToThisWindow.
    - Handles terminal consoles and Unicode scripts cleanly.
    - Provides in-memory recovery buffer for instant manual re-copying.
    """

    last_injected_text: str = ""

    @classmethod
    def _safe_clipboard_copy(cls, text: str, max_retries: int = 5, retry_delay: float = 0.05) -> bool:
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
            # Fallback bypass: Windows allows SetForegroundWindow if Alt is momentarily tapped
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
    def inject(cls, text: str, target_hwnd: Optional[int] = None, preserve_clipboard: bool = True) -> bool:
        if not text:
            return False

        cls.last_injected_text = text

        # 1. Backup current clipboard content safely
        previous_clipboard = None
        if preserve_clipboard:
            previous_clipboard = cls._safe_clipboard_paste()

        try:
            # 2. Restore focus to target window if provided
            if target_hwnd:
                cls._safe_set_foreground(target_hwnd)
                time.sleep(0.08)

            # 3. Copy text to clipboard with lock retry
            if not cls._safe_clipboard_copy(text):
                print("[Injector Error] Failed to set clipboard for injection.")
                return False
            time.sleep(0.04)

            # 4. Detect if target window is a legacy console/terminal requiring Shift+Insert
            is_legacy_console = False
            if HAS_WIN32 and target_hwnd and sys.platform == "win32":
                try:
                    cls_name = win32gui.GetClassName(target_hwnd)
                    if cls_name in ("ConsoleWindowClass",):
                        is_legacy_console = True
                except Exception:
                    pass

            # 5. Simulate keystrokes
            if HAS_WIN32 and sys.platform == "win32":
                if is_legacy_console:
                    # Shift + Insert for legacy console
                    win32api.keybd_event(win32con.VK_SHIFT, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_INSERT, 0, 0, 0)
                    time.sleep(0.05)
                    win32api.keybd_event(win32con.VK_INSERT, 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_SHIFT, 0, win32con.KEYEVENTF_KEYUP, 0)
                else:
                    # Standard Ctrl + V
                    win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
                    win32api.keybd_event(ord('V'), 0, 0, 0)
                    time.sleep(0.05)
                    win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
                    win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
            else:
                from pynput.keyboard import Controller, Key
                kb = Controller()
                kb.press(Key.ctrl)
                kb.press('v')
                time.sleep(0.05)
                kb.release('v')
                kb.release(Key.ctrl)

            print(f"[Injector] Successfully injected {len(text)} characters.")
            return True

        except Exception as e:
            print(f"[Injector Error] Text injection failed: {e}")
            return False

        finally:
            # 6. Restore previous clipboard after a safe 1.5s delay to prevent IDE paste race
            if preserve_clipboard and previous_clipboard is not None and previous_clipboard != text:
                def restore():
                    time.sleep(1.5)
                    try:
                        current = cls._safe_clipboard_paste()
                        # Only restore if the user hasn't copied something new in the meantime
                        if current == text:
                            cls._safe_clipboard_copy(previous_clipboard)
                    except Exception:
                        pass
                import threading
                threading.Thread(target=restore, daemon=True, name="FlowPilot-ClipboardRestore").start()
