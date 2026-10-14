"""
FlowPilot Win32 Native Global Hotkey Service
Uses RegisterHotKey with a dedicated native Windows message loop.
Guarantees global keystroke capture across Notepad, browsers, and desktop apps.
Bypasses low-level keyboard hook timeouts and UAC isolation issues.
"""

import ctypes
from ctypes import wintypes
import threading
import logging
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
}


def parse_hotkey_string(hotkey_str: str) -> Tuple[int, int]:
    """
    Parses strings like 'Ctrl+Shift+Space', 'Ctrl+Alt+Space', 'F9'
    Returns: (modifiers_mask, vk_code)
    """
    parts = [p.strip().upper() for p in hotkey_str.replace(" ", "").split("+")]
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


class Win32HotkeyService:
    def __init__(self):
        self._hotkeys: Dict[int, Dict] = {}
        self._thread: Optional[threading.Thread] = None
        self._thread_id: Optional[int] = None
        self._stop_event = threading.Event()
        self._ready_event = threading.Event()
        self._next_id = 1
        self._user32 = ctypes.windll.user32
        self._kernel32 = ctypes.windll.kernel32
        self.stats = {"events_received": 0, "registered_count": 0, "errors": []}

    def register(self, hotkey_str: str, callback: Callable[[], None]) -> int:
        """
        Registers a hotkey string (e.g. 'Ctrl+Shift+Space' or 'F9') with a callback.
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
                    callback = self._hotkeys[hk_id]["callback"]
                    # Execute callback asynchronously to keep message queue free
                    threading.Thread(target=callback, daemon=True, name=f"FlowPilot-HotkeyAction-{hk_id}").start()

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
