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
        elif part in VK_MAPPING:
            vk = VK_MAPPING[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part)
        else:
            raise ValueError(f"Unknown key in hotkey definition: '{part}'")

    if vk == 0:
        raise ValueError(f"Hotkey '{hotkey_str}' does not specify a valid primary key.")

    return mods, vk


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

    def release(self):
        action = None
        with self._lock:
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


class Win32HotkeyService:
    def __init__(self):
        self._hotkeys: Dict[int, Dict] = {}
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._next_id = 1
        if sys.platform == "win32":
            self._user32 = ctypes.windll.user32
            self._kernel32 = ctypes.windll.kernel32
        else:
            self._user32 = None
            self._kernel32 = None
        self.stats = {"events_received": 0, "registered_count": 0, "errors": []}

    @staticmethod
    def test_hotkey_availability(hotkey_str: str, currently_active_hotkey: Optional[str] = None) -> Tuple[bool, str]:
        """
        Tests whether a given hotkey string can be successfully registered via Win32 RegisterHotKey.
        Returns (is_available: bool, message: str).
        """
        if sys.platform != "win32":
            return True, "Available via cross-platform keyboard listener."
        clean = hotkey_str.replace("<", "").replace(">", "").strip()
        parts = [p.strip().upper() for p in clean.replace(" ", "").split("+")]
        has_primary = any(p in VK_MAPPING or (len(p) == 1 and p.isalnum()) for p in parts if p not in ("CTRL", "CONTROL", "ALT", "SHIFT", "WIN"))
        
        if not has_primary:
            return False, "Modifier-only combination. Windows RegisterHotKey requires a primary key (e.g. Ctrl+Shift+Space, Ctrl+Win+D, or F9)."

        try:
            mods, vk = parse_hotkey_string(clean)
        except ValueError as e:
            return False, f"Invalid format: {e}"

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

    def register(self, hotkey_str: str, callback: Callable[[], None], on_release: Optional[Callable[[], None]] = None) -> int:
        """
        Registers a hotkey string (e.g. 'Ctrl+Shift+Space' or 'F9') with a callback.
        Optionally accepts an on_release callback for Push-to-Talk monitoring.
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
            "registered": False,
        }
        logger.info(f"[HotkeyService] Queued hotkey ID {hk_id}: {hotkey_str} (mods={hex(mods)}, vk={hex(vk)})")
        return hk_id

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
        self._thread = threading.Thread(target=self._message_loop, daemon=True, name="FlowPilot-HotkeyMsgLoop")
        self._thread.start()

        ready = self._ready_event.wait(timeout=timeout)
        if not ready:
            logger.error("[HotkeyService] Message loop thread failed to report ready within timeout.")
            return False
        return True

    def _message_loop(self):
        """
        Runs the Win32 message pump for hotkeys.
        """
        self._thread_id = self._kernel32.GetCurrentThreadId()

        # Force creation of the message queue for this thread
        msg = wintypes.MSG()
        self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)

        # Register each configured hotkey with the thread queue
        for hk_id, info in self._hotkeys.items():
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
                hk_id = msg.wParam
                self.stats["events_received"] += 1
                logger.info(f"[HotkeyService] WM_HOTKEY received for ID {hk_id}")
                if hk_id in self._hotkeys:
                    info = self._hotkeys[hk_id]
                    callback = info["callback"]
                    on_release = info.get("on_release")
                    vk = info["vk"]

                    def run_action(cb=callback, rel=on_release, target_vk=vk):
                        import time
                        try:
                            cb()
                        except Exception as e:
                            logger.error(f"[HotkeyService] Callback error: {e}")
                        if rel:
                            # Push-to-talk release monitor: responsive 10ms polling
                            time.sleep(0.01)
                            while not self._stop_event.is_set():
                                state = self._user32.GetAsyncKeyState(target_vk)
                                if not (state & 0x8000):
                                    try:
                                        rel()
                                    except Exception as e:
                                        logger.error(f"[HotkeyService] OnRelease error: {e}")
                                    break
                                time.sleep(0.01)

                    threading.Thread(target=run_action, daemon=True, name=f"FlowPilot-HotkeyAction-{hk_id}").start()

            self._user32.TranslateMessage(ctypes.byref(msg))
            self._user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup on exit
        for hk_id, info in self._hotkeys.items():
            if info["registered"]:
                self._user32.UnregisterHotKey(None, hk_id)
                info["registered"] = False
        logger.info("[HotkeyService] Message loop terminated and hotkeys unregistered.")

    def stop(self):
        """
        Cleanly stops the message loop and unregisters all hotkeys.
        """
        self._stop_event.set()
        if self._thread_id:
            self._user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._thread_id = None
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

    def register(self, hotkey_str: str, callback: Callable[[], None], on_release: Optional[Callable[[], None]] = None) -> int:
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

    def start(self, timeout: float = 3.0) -> bool:
        with self._lock:
            if self._running and self._listener:
                return True
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
            self._active_keys.add(norm)
            self.stats["events_received"] += 1

            for hk_id, info in self._hotkeys.items():
                req = info["parts"]
                if req.issubset(self._active_keys) and hk_id not in self._triggered_hotkeys:
                    self._triggered_hotkeys.add(hk_id)
                    cb = info["callback"]
                    threading.Thread(target=cb, daemon=True, name=f"PynputAction-{hk_id}").start()

    def _on_release(self, key):
        norm = self._normalize_key(key)
        with self._lock:
            if norm in self._active_keys:
                self._active_keys.remove(norm)

            for hk_id in list(self._triggered_hotkeys):
                info = self._hotkeys.get(hk_id)
                if info:
                    req = info["parts"]
                    if not req.issubset(self._active_keys):
                        self._triggered_hotkeys.remove(hk_id)
                        rel = info["on_release"]
                        if rel:
                            threading.Thread(target=rel, daemon=True, name=f"PynputRelease-{hk_id}").start()

    def stop(self):
        with self._lock:
            if self._listener:
                try:
                    self._listener.stop()
                except Exception:
                    pass
                self._listener = None
            self._running = False
            self._active_keys.clear()
            self._triggered_hotkeys.clear()

    def is_alive(self) -> bool:
        return self._running and self._listener is not None


def get_hotkey_service():
    """Returns the optimal hotkey service for the current operating system."""
    import sys
    if sys.platform == "win32":
        return Win32HotkeyService()
    else:
        return PynputHotkeyService()
