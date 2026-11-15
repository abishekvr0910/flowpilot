"""
FlowPilot Win32 Native Global Hotkey Service
Uses RegisterHotKey with a dedicated native Windows message loop.
Guarantees global keystroke capture across Notepad, browsers, and desktop apps.
Bypasses low-level keyboard hook timeouts and UAC isolation issues.
"""

import sys
import ctypes
from ctypes import wintypes
import threading
from collections import deque
import logging
import time
from typing import Callable, Dict, Optional, Tuple

logger = logging.getLogger("FlowPilot.HotkeyService")

# Win32 Constants
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000  # Windows 7+ avoids repeating messages when held

WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
LLKHF_INJECTED = 0x00000001

if sys.platform == "win32":
    LRESULT = ctypes.c_ssize_t
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [
            ("vkCode", wintypes.DWORD),
            ("scanCode", wintypes.DWORD),
            ("flags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ctypes.c_ulonglong)
        ]
else:
    HOOKPROC = None
    KBDLLHOOKSTRUCT = None

# Virtual Key mapping
VK_MAPPING = {
    "SPACE": 0x20,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
    "A": 0x41, "B": 0x42, "C": 0x43, "D": 0x44, "E": 0x45,
    "F": 0x46, "G": 0x47, "H": 0x48, "I": 0x49, "J": 0x4A,
    "K": 0x4B, "L": 0x4C, "M": 0x4D, "N": 0x4E, "O": 0x4F,
    "P": 0x50, "Q": 0x51, "R": 0x52, "S": 0x53, "T": 0x54,
    "U": 0x55, "V": 0x56, "W": 0x57, "X": 0x58, "Y": 0x59, "Z": 0x5A,
    "0": 0x30, "1": 0x31, "2": 0x32, "3": 0x33, "4": 0x34,
    "5": 0x35, "6": 0x36, "7": 0x37, "8": 0x38, "9": 0x39,
    "ESC": 0x1B, "ESCAPE": 0x1B, "TAB": 0x09, "ENTER": 0x0D, "RETURN": 0x0D,
    "GRAVE": 0xC0, "TILDE": 0xC0, "BACKTICK": 0xC0,
}

# Dictation must not replace another FlowPilot action. Compare parsed key codes so
# equivalent spellings (such as Control+Alt+T) cannot bypass this check.
RESERVED_FLOWPILOT_SHORTCUTS = {
    (MOD_CONTROL | MOD_ALT, VK_MAPPING["T"]): "Selected-text transforms (Ctrl+Alt+T)",
    (MOD_CONTROL | MOD_ALT, VK_MAPPING["V"]): "Paste last dictation (Ctrl+Alt+V)",
    (MOD_CONTROL | MOD_ALT, VK_MAPPING["L"]): "Quick switch language (Ctrl+Alt+L)",
    (MOD_ALT | MOD_SHIFT, VK_MAPPING["Z"]): "Paste last dictation (Alt+Shift+Z)",
    (MOD_ALT | MOD_SHIFT, VK_MAPPING["X"]): "Copy last dictation (Alt+Shift+X)",
    (MOD_ALT | MOD_SHIFT, VK_MAPPING["U"]): "Reserved external undo (currently unavailable)",
}

RESERVED_WINDOWS_SHORTCUTS = {
    (MOD_WIN, ord("L")): "Windows Lock Screen (Win+L)",
    (MOD_WIN, ord("D")): "Windows Show Desktop (Win+D)",
    (MOD_ALT, VK_MAPPING["TAB"]): "Windows Task Switcher (Alt+Tab)",
    (MOD_WIN, VK_MAPPING["TAB"]): "Windows Task View (Win+Tab)",
    (MOD_WIN, ord("R")): "Windows Run Dialog (Win+R)",
    (MOD_WIN, ord("E")): "Windows File Explorer (Win+E)",
    (MOD_WIN, ord("X")): "Windows Quick Link Menu (Win+X)",
    (MOD_WIN, ord("C")): "Windows Copilot / Quick Assistant (Win+C)",
}


def parse_hotkey_string(hotkey_str: str) -> Tuple[int, int]:
    """
    Parses strings like 'Ctrl+Shift+Space', 'Ctrl+Alt+Space', 'F9'
    Returns: (modifiers_mask, vk_code)
    """
    clean = hotkey_str.replace("<", "").replace(">", "").strip()
    parts = [p.strip().upper() for p in clean.replace(" ", "").split("+")]
    mods = 0
    vk = 0
    for part in parts:
        if part in ("CTRL", "CONTROL"):
            mods |= MOD_CONTROL
        elif part == "ALT":
            mods |= MOD_ALT
        elif part == "SHIFT":
            mods |= MOD_SHIFT
        elif part == "WIN":
            mods |= MOD_WIN
        elif part in VK_MAPPING or (len(part) == 1 and part.isascii() and part.isalnum()):
            if vk:
                raise ValueError("A shortcut must contain exactly one primary key.")
            vk = VK_MAPPING.get(part, ord(part) if len(part) == 1 else 0)
        else:
            raise ValueError(f"Unknown key in hotkey definition: '{part}'")

    if vk == 0:
        raise ValueError(f"Hotkey '{hotkey_str}' does not specify a valid primary key.")

    return mods, vk


def dictation_hotkey_conflict(hotkey_str: str) -> Optional[str]:
    """Return a FlowPilot-owned or reserved system action that conflicts with a dictation shortcut."""
    try:
        parsed = parse_hotkey_string(hotkey_str)
        if parsed in RESERVED_FLOWPILOT_SHORTCUTS:
            return RESERVED_FLOWPILOT_SHORTCUTS[parsed]
        if parsed in RESERVED_WINDOWS_SHORTCUTS:
            return RESERVED_WINDOWS_SHORTCUTS[parsed]
    except Exception:
        pass
    return None


class TapLatch:
    """
    Pure state machine providing dual push-to-talk (hold to speak)
    and hands-free latch (double tap to lock) on a single hotkey.
    Adopted from high-performance desktop dictation architecture.
    """
    IDLE = "idle"
    HELD = "held"
    PENDING = "pending"
    LATCHED = "latched"

    def __init__(self, on_start: Callable[[], None], on_stop: Callable[[], None], window_ms: int = 400, clock=time.monotonic):
        self.on_start = on_start
        self.on_stop = on_stop
        self.window = max(0.05, window_ms / 1000.0)
        self._clock = clock
        self.state = self.IDLE
        self._pressed_at = 0.0
        self._timer: Optional[threading.Timer] = None
        self._lock = threading.Lock()

    def press(self):
        action = None
        with self._lock:
            now = self._clock()
            if self.state == self.IDLE:
                self.state = self.HELD
                self._pressed_at = now
                action = self.on_start
            elif self.state == self.PENDING:
                if self._timer:
                    self._timer.cancel()
                    self._timer = None
                self.state = self.LATCHED
                logger.info("[TapLatch] Double-tap detected: Latched into hands-free recording mode.")
                action = None
            elif self.state == self.LATCHED:
                self.state = self.IDLE
                logger.info("[TapLatch] Tap while latched: Stopping hands-free recording.")
                action = self.on_stop
        if action:
            action()

    def latch_to_toggle(self) -> bool:
        """
        Transition from HELD push-to-talk into LATCHED hands-free mode.
        When latched, releasing the hold key will not stop recording.
        """
        with self._lock:
            if self.state == self.HELD:
                self.state = self.LATCHED
                logger.info("[TapLatch] Switched from hold-to-talk to latched hands-free mode.")
                return True
            return False

    def release(self):
        action = None
        with self._lock:
            if self.state == self.LATCHED:
                # Releasing the key while in latched mode is a no-op (hands-free recording stays active)
                return
            if self.state != self.HELD:
                return
            now = self._clock()
            held_duration = now - self._pressed_at
            if held_duration >= self.window:
                # Normal push-to-talk release
                self.state = self.IDLE
                action = self.on_stop
            else:
                # Quick tap: wait to see if a second tap arrives within window
                self.state = self.PENDING
                self._timer = threading.Timer(self.window, self._on_window_expired)
                self._timer.daemon = True
                self._timer.start()
        if action:
            action()

    def _on_window_expired(self):
        action = None
        with self._lock:
            if self.state != self.PENDING:
                return
            self.state = self.IDLE
            self._timer = None
            action = self.on_stop
        if action:
            action()

    def reset(self):
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None
            self.state = self.IDLE


class _SerialCallbackDispatcher:
    """Executes hotkey press and release callbacks strictly in FIFO order."""

    def __init__(self, thread_name: str = "FlowPilot-HotkeyDispatcher"):
        self._thread_name = thread_name
        self._cond = threading.Condition()
        self._items: deque = deque()
        self._accepting: bool = True
        self._generation: int = 0
        self._worker: Optional[threading.Thread] = None

    @staticmethod
    def _invoke_safe(fn: Callable[[], None], label: str) -> None:
        try:
            fn()
        except Exception as e:
            logger.error(f"[HotkeyService] {label} error: {e}")

    def _run(self):
        me = threading.current_thread()
        while True:
            with self._cond:
                while not self._items and self._accepting:
                    self._cond.wait()
                if not self._accepting:
                    self._items.clear()
                    if self._worker is me:
                        self._worker = None
                    self._cond.notify_all()
                    return
                item_gen, fn, label = self._items.popleft()
                if item_gen != self._generation:
                    continue
            self._invoke_safe(fn, label)

    def reset(self) -> None:
        """Re-arm callback acceptance on service start without creating duplicate workers."""
        with self._cond:
            self._accepting = True
            self._generation += 1
            self._items.clear()
            self._cond.notify_all()

    def cancel_pending(self) -> None:
        """Reject subsequent enqueues and discard all queued-but-unstarted callbacks."""
        with self._cond:
            self._accepting = False
            self._generation += 1
            self._items.clear()
            self._cond.notify_all()

    def enqueue(self, fn: Callable[[], None], label: str) -> bool:
        with self._cond:
            if not self._accepting:
                return False
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(
                    target=self._run,
                    daemon=True,
                    name=self._thread_name,
                )
                self._worker.start()
            self._items.append((self._generation, fn, label))
            self._cond.notify_all()
            return True

    def stop(self, timeout: float = 1.5) -> bool:
        with self._cond:
            self._accepting = False
            self._generation += 1
            self._items.clear()
            worker = self._worker
            self._cond.notify_all()
        if worker is not None and worker is not threading.current_thread() and worker.is_alive():
            worker.join(timeout=timeout)
            with self._cond:
                if worker.is_alive():
                    return False
                if self._worker is worker:
                    self._worker = None
        else:
            with self._cond:
                if self._worker is worker and (worker is None or not worker.is_alive()):
                    self._worker = None
        return True


class Win32HotkeyService:
    def __init__(self):
        self._hotkeys: Dict[int, Dict] = {}
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._next_id = 1
        self._hook = None
        self._hook_proc = None
        self._hook_active_hotkeys: Dict[int, int] = {}  # vk -> hk_id
        self._last_hook_trigger: Dict[int, float] = {}  # hk_id -> timestamp
        self._dispatcher = _SerialCallbackDispatcher("FlowPilot-HotkeyDispatcher")
        if sys.platform == "win32":
            self._user32 = ctypes.windll.user32
            self._kernel32 = ctypes.windll.kernel32
        else:
            self._user32 = None
            self._kernel32 = None
        self.stats = {"events_received": 0, "registered_count": 0, "errors": []}

    def _get_current_modifiers(self) -> int:
        if not self._user32:
            return 0
        mods = 0
        if self._user32.GetAsyncKeyState(0x11) & 0x8000:  # VK_CONTROL
            mods |= MOD_CONTROL
        if self._user32.GetAsyncKeyState(0x12) & 0x8000:  # VK_MENU (Alt)
            mods |= MOD_ALT
        if self._user32.GetAsyncKeyState(0x10) & 0x8000:  # VK_SHIFT
            mods |= MOD_SHIFT
        if (self._user32.GetAsyncKeyState(0x5B) & 0x8000) or (self._user32.GetAsyncKeyState(0x5C) & 0x8000):  # VK_LWIN / VK_RWIN
            mods |= MOD_WIN
        return mods

    @staticmethod
    def _invoke_safe(fn: Callable[[], None], label: str) -> None:
        try:
            fn()
        except Exception as e:
            logger.error(f"[HotkeyService] {label} error: {e}")

    def _create_hook_proc(self):
        if not HOOKPROC:
            return None

        @HOOKPROC
        def hook_proc(nCode, wParam, lParam):
            if nCode == HC_ACTION:
                if self._stop_event.is_set():
                    return self._user32.CallNextHookEx(None, nCode, wParam, lParam)
                try:
                    kb = KBDLLHOOKSTRUCT.from_address(lParam)
                    # Never intercept synthetic/injected events from FlowPilot (SendInput)
                    if kb.flags & LLKHF_INJECTED:
                        return self._user32.CallNextHookEx(None, nCode, wParam, lParam)

                    vk = kb.vkCode
                    is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)

                    if is_down:
                        if vk in self._hook_active_hotkeys:
                            # Hardware auto-repeat while key is held down: suppress repeat chatter
                            active_id = self._hook_active_hotkeys[vk]
                            info = self._hotkeys.get(active_id)
                            if info and info.get("registered") and info.get("suppress", True):
                                return 1
                        else:
                            curr_mods = self._get_current_modifiers()
                            for hk_id, info in list(self._hotkeys.items()):
                                if info.get("registered") and info["vk"] == vk and info["mods"] == curr_mods:
                                    self._hook_active_hotkeys[vk] = hk_id
                                    self._last_hook_trigger[hk_id] = time.monotonic()
                                    self.stats["events_received"] += 1
                                    self._dispatcher.enqueue(info["callback"], "Callback")
                                    if info.get("suppress", True):
                                        return 1
                                    break
                    elif is_up:
                        if vk in self._hook_active_hotkeys:
                            active_id = self._hook_active_hotkeys.pop(vk, None)
                            info = self._hotkeys.get(active_id)
                            if info and info.get("registered"):
                                rel = info.get("on_release")
                                if rel:
                                    self._dispatcher.enqueue(rel, "OnRelease")
                                if info.get("suppress", True):
                                    return 1
                except Exception as exc:
                    logger.debug(f"[HotkeyService] Hook callback exception: {exc}")

            return self._user32.CallNextHookEx(None, nCode, wParam, lParam)

        return hook_proc

    @staticmethod
    def test_hotkey_availability(hotkey_str: str, currently_active_hotkey: Optional[str] = None) -> Tuple[bool, str]:
        """
        Tests whether a given hotkey string can be successfully registered via Win32 RegisterHotKey.
        Returns (is_available: bool, message: str).
        """
        clean = hotkey_str.replace("<", "").replace(">", "").strip()
        parts = [p.strip().upper() for p in clean.replace(" ", "").split("+")]
        has_primary = any(p in VK_MAPPING or (len(p) == 1 and p.isalnum()) for p in parts if p not in ("CTRL", "CONTROL", "ALT", "SHIFT", "WIN"))
        
        if not has_primary:
            return False, "Modifier-only combination. Windows RegisterHotKey requires a primary key (e.g. Ctrl+Shift+Space, Ctrl+Win+D, or F9)."

        try:
            mods, vk = parse_hotkey_string(clean)
        except ValueError as e:
            return False, f"Invalid format: {e}"

        conflict = dictation_hotkey_conflict(clean)
        if conflict:
            return False, f"Conflict: Shortcut is already assigned/reserved for {conflict} (exempted from reassignment)."

        if sys.platform != "win32":
            return True, "Valid shortcut; availability cannot be checked outside Windows."

        if currently_active_hotkey:
            try:
                cur_clean = currently_active_hotkey.replace("<", "").replace(">", "").strip()
                cur_mods, cur_vk = parse_hotkey_string(cur_clean)
                if (cur_mods, cur_vk) == (mods, vk):
                    return True, "Currently active and registered by FlowPilot."
            except Exception:
                pass

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        test_id = 0xBEEF
        res = user32.RegisterHotKey(None, test_id, mods | MOD_NOREPEAT, vk)
        if res:
            user32.UnregisterHotKey(None, test_id)
            return True, "Available and ready for registration."
        else:
            err = kernel32.GetLastError()
            if err == 1409:
                return False, "Conflict: Key already registered by another application or reserved by Windows (Error 1409)."
            return False, f"Registration failed (Win32 Error {err})."

    def register(
        self,
        hotkey_str: str,
        callback: Callable[[], None],
        on_release: Optional[Callable[[], None]] = None,
        suppress: bool = True
    ) -> int:
        """
        Registers a hotkey string (e.g. 'Ctrl+Shift+Space' or 'F9') with a callback.
        Optionally accepts an on_release callback for Push-to-Talk monitoring.
        suppress: If True, uses WH_KEYBOARD_LL to suppress key repeat chatter and key leak into target apps.
        Returns the integer registration ID.
        """
        mods, vk = parse_hotkey_string(hotkey_str)
        hk_id = self._next_id
        self._next_id += 1
        self._hotkeys[hk_id] = {
            "str": hotkey_str,
            "mods": mods,
            "vk": vk,
            "callback": callback,
            "on_release": on_release,
            "suppress": suppress,
            "registered": False,
        }
        logger.info(f"[HotkeyService] Queued hotkey ID {hk_id}: {hotkey_str} (mods={hex(mods)}, vk={hex(vk)}, suppress={suppress})")
        return hk_id

    register_hotkey = register

    def start(self, timeout: float = 3.0) -> bool:
        """
        Starts the dedicated Windows message pump in a background thread.
        Waits until hotkeys are registered or timeout expires.
        """
        if self._thread and self._thread.is_alive():
            logger.warning("[HotkeyService] Already running.")
            return True

        self._stop_event.clear()
        self._ready_event.clear()
        self.stats["registered_count"] = 0
        self.stats["errors"] = []
        self._dispatcher.reset()
        self._thread = threading.Thread(target=self._message_loop, daemon=True, name="FlowPilot-HotkeyMsgLoop")
        self._thread.start()

        ready = self._ready_event.wait(timeout=timeout)
        if not ready:
            logger.error("[HotkeyService] Message loop thread failed to report ready within timeout.")
            return False
        return True

    def _configure_win32_signatures(self):
        """Ensure 64-bit safe argtypes/restype on hook and key-state Win32 calls."""
        if not self._user32 or HOOKPROC is None:
            return
        try:
            self._user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
            self._user32.CallNextHookEx.restype = LRESULT
            self._user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
            self._user32.SetWindowsHookExW.restype = wintypes.HHOOK
            self._user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
            self._user32.UnhookWindowsHookEx.restype = wintypes.BOOL
            self._user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
            self._user32.GetAsyncKeyState.restype = wintypes.SHORT
        except Exception as e:
            logger.debug(f"[HotkeyService] Failed to configure Win32 hook signatures: {e}")

    def _message_loop(self):
        """
        Runs the Win32 message pump for hotkeys.
        Installs WH_KEYBOARD_LL when suppressible hotkeys are configured so key repeats
        and primary keystrokes do not leak into target applications, while retaining
        RegisterHotKey / WM_HOTKEY as a fallback.
        """
        self._thread_id = self._kernel32.GetCurrentThreadId()
        self._configure_win32_signatures()

        # Force creation of the message queue for this thread
        msg = wintypes.MSG()
        self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        # Install low-level keyboard hook on this pumping thread
        self._hook = None
        self._hook_proc = self._create_hook_proc()
        if self._hook_proc is not None:
            hook_handle = self._user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, None, 0)
            if hook_handle:
                self._hook = hook_handle
                logger.info("[HotkeyService] Installed WH_KEYBOARD_LL suppression hook.")
            else:
                err = self._kernel32.GetLastError()
                self._hook_proc = None
                logger.warning(f"[HotkeyService] SetWindowsHookExW(WH_KEYBOARD_LL) failed (Win32 Error: {err}); falling back to RegisterHotKey only.")

        # Register each configured hotkey with the thread queue
        for hk_id, info in list(self._hotkeys.items()):
            mods = info["mods"] | MOD_NOREPEAT
            vk = info["vk"]
            success = self._user32.RegisterHotKey(None, hk_id, mods, vk)
            if not success:
                # Retry without MOD_NOREPEAT (for legacy compatibility)
                success = self._user32.RegisterHotKey(None, hk_id, info["mods"], vk)

            if success:
                info["registered"] = True
                self.stats["registered_count"] += 1
                logger.info(f"[HotkeyService] Successfully registered global hotkey #{hk_id} '{info['str']}'")
            else:
                err = self._kernel32.GetLastError()
                err_msg = f"Failed to register hotkey #{hk_id} '{info['str']}' (Win32 Error: {err})"
                self.stats["errors"].append(err_msg)
                logger.error(f"[HotkeyService] {err_msg}")

        self._ready_event.set()

        # Message loop
        while not self._stop_event.is_set():
            ret = self._user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                # WM_QUIT or error
                break

            if msg.message == WM_HOTKEY:
                if self._stop_event.is_set():
                    continue
                hk_id = msg.wParam
                if hk_id in self._hotkeys:
                    info = self._hotkeys[hk_id]
                    vk = info["vk"]
                    last_hook_ts = self._last_hook_trigger.get(hk_id, 0.0)
                    if self._hook_active_hotkeys.get(vk) == hk_id or (last_hook_ts and (time.monotonic() - last_hook_ts) < 0.3):
                        logger.debug(f"[HotkeyService] Debounced duplicate WM_HOTKEY for ID {hk_id} (handled by hook).")
                    else:
                        self.stats["events_received"] += 1
                        logger.info(f"[HotkeyService] WM_HOTKEY received for ID {hk_id}")
                        callback = info["callback"]
                        on_release = info.get("on_release")
                        self._dispatcher.enqueue(callback, "Callback")

                        if on_release:
                            def poll_release(rel=on_release, target_vk=vk):
                                # Push-to-talk release monitor: responsive 10ms polling
                                time.sleep(0.01)
                                while not self._stop_event.is_set():
                                    state = self._user32.GetAsyncKeyState(target_vk)
                                    if not (state & 0x8000):
                                        self._dispatcher.enqueue(rel, "OnRelease")
                                        break
                                    time.sleep(0.01)

                            threading.Thread(target=poll_release, daemon=True, name=f"FlowPilot-HotkeyRelease-{hk_id}").start()

            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup on exit
        if self._hook:
            try:
                self._user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None
        self._hook_proc = None
        self._hook_active_hotkeys.clear()
        self._last_hook_trigger.clear()

        for hk_id, info in list(self._hotkeys.items()):
            if info["registered"]:
                self._user32.UnregisterHotKey(None, hk_id)
                info["registered"] = False
        logger.info("[HotkeyService] Message loop terminated and hotkeys unregistered.")

    def stop(self):
        """
        Cleanly stops the message loop and unregisters all hotkeys.
        """
        self._stop_event.set()
        self._dispatcher.cancel_pending()
        if self._thread_id:
            self._user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._dispatcher.stop()
        self._thread = None
        self._thread_id = None
        self._hook_active_hotkeys.clear()
        self._last_hook_trigger.clear()
        logger.info("[HotkeyService] Stopped.")

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()


class PynputHotkeyService:
    """
    Cross-platform Global Hotkey Service for Linux (X11) and macOS.
    Monitors keyboard events via pynput listener and supports:
    - Chord key combinations (e.g. Ctrl+Shift+Space, Alt+Shift+Z)
    - Single-key hotkeys (e.g. F9)
    - Push-to-talk press and release monitoring
    - TapLatch hands-free double-tap gesture
    """
    def __init__(self):
        self._hotkeys: Dict[int, Dict] = {}
        self._listener = None
        self._active_keys = set()
        self._triggered_hotkeys = set()
        self._lock = threading.Lock()
        self._next_id = 1
        self._running = False
        self._stop_event = threading.Event()
        self._dispatcher = _SerialCallbackDispatcher("FlowPilot-PynputDispatcher")
        self.stats = {"events_received": 0, "registered_count": 0, "errors": []}

    @staticmethod
    def test_hotkey_availability(hotkey_str: str, currently_active_hotkey: Optional[str] = None) -> Tuple[bool, str]:
        return True, "Available via cross-platform keyboard listener."

    @staticmethod
    def _normalize_key(key) -> str:
        try:
            import pynput.keyboard as pk
            if key in (pk.Key.ctrl, pk.Key.ctrl_l, pk.Key.ctrl_r):
                return "CTRL"
            if key in (pk.Key.alt, pk.Key.alt_l, pk.Key.alt_r, getattr(pk.Key, "alt_gr", None)):
                return "ALT"
            if key in (pk.Key.shift, pk.Key.shift_l, pk.Key.shift_r):
                return "SHIFT"
            if key in (pk.Key.cmd, pk.Key.cmd_l, pk.Key.cmd_r):
                return "CMD"
            if key == pk.Key.space:
                return "SPACE"
            if hasattr(key, "name") and key.name:
                return key.name.upper()
            if hasattr(key, "char") and key.char:
                return key.char.upper()
        except Exception:
            pass
        return str(key).upper()

    def register(
        self,
        hotkey_str: str,
        callback: Callable[[], None],
        on_release: Optional[Callable[[], None]] = None,
        suppress: bool = True,
    ) -> int:
        _ = suppress
        clean = hotkey_str.replace("<", "").replace(">", "").strip()
        parts = {p.strip().upper() for p in clean.replace(" ", "").split("+")}
        normalized_parts = set()
        for p in parts:
            if p in ("CONTROL", "CTRL"):
                normalized_parts.add("CTRL")
            elif p in ("WIN", "CMD", "COMMAND"):
                normalized_parts.add("CMD")
            else:
                normalized_parts.add(p)

        hk_id = self._next_id
        self._next_id += 1
        with self._lock:
            self._hotkeys[hk_id] = {
                "str": hotkey_str,
                "parts": normalized_parts,
                "callback": callback,
                "on_release": on_release
            }
            self.stats["registered_count"] = len(self._hotkeys)
        return hk_id

    register_hotkey = register

    def start(self, timeout: float = 3.0) -> bool:
        with self._lock:
            if self._running and self._listener:
                return True
            self._stop_event.clear()
            self._dispatcher.reset()
            try:
                import pynput.keyboard as pk
                self._listener = pk.Listener(
                    on_press=self._on_press,
                    on_release=self._on_release
                )
                self._listener.daemon = True
                self._listener.start()
                self._running = True
                logger.info(f"[PynputHotkeyService] Cross-platform listener active with {len(self._hotkeys)} hotkeys.")
                return True
            except Exception as e:
                logger.error(f"[PynputHotkeyService] Failed to start listener: {e}")
                self.stats["errors"].append(str(e))
                return False

    def _on_press(self, key):
        norm = self._normalize_key(key)
        with self._lock:
            if self._stop_event.is_set():
                return
            self._active_keys.add(norm)
            self.stats["events_received"] += 1

            for hk_id, info in self._hotkeys.items():
                req = info["parts"]
                if req.issubset(self._active_keys) and hk_id not in self._triggered_hotkeys:
                    self._triggered_hotkeys.add(hk_id)
                    self._dispatcher.enqueue(info["callback"], "PynputAction")

    def _on_release(self, key):
        norm = self._normalize_key(key)
        with self._lock:
            if norm in self._active_keys:
                self._active_keys.remove(norm)
            if self._stop_event.is_set():
                return

            for hk_id in list(self._triggered_hotkeys):
                info = self._hotkeys.get(hk_id)
                if info:
                    req = info["parts"]
                    if not req.issubset(self._active_keys):
                        self._triggered_hotkeys.remove(hk_id)
                        rel = info["on_release"]
                        if rel:
                            self._dispatcher.enqueue(rel, "PynputRelease")

    def stop(self):
        with self._lock:
            self._stop_event.set()
            self._dispatcher.cancel_pending()
            if self._listener:
                try:
                    self._listener.stop()
                except Exception:
                    pass
                self._listener = None
            self._running = False
            self._active_keys.clear()
            self._triggered_hotkeys.clear()
        self._dispatcher.stop()

    def is_alive(self) -> bool:
        return self._running and self._listener is not None


def get_hotkey_service():
    """Returns the optimal hotkey service for the current operating system."""
    import sys
    if sys.platform == "win32":
        return Win32HotkeyService()
    else:
        return PynputHotkeyService()
