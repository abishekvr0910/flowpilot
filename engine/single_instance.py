"""
FlowPilot Single-Instance Mutex
Ensures only one instance of FlowPilot runs at any time.
If an instance is already active, activates its window and signals the new instance to exit.
"""

import sys
import ctypes
from ctypes import wintypes

class SingleInstance:
    def __init__(self, mutex_name: str = "Global\\FlowPilot_Desktop_SingleInstance_Mutex"):
        self.mutex_name = mutex_name
        self.mutex = None
        self.lock_file = None
        self.already_running = False

        if sys.platform == "win32":
            try:
                kernel32 = ctypes.windll.kernel32
                # Create named mutex
                self.mutex = kernel32.CreateMutexW(None, False, self.mutex_name)
                last_error = kernel32.GetLastError()
                ERROR_ALREADY_EXISTS = 183
                if last_error == ERROR_ALREADY_EXISTS:
                    self.already_running = True
            except Exception:
                pass
        else:
            # POSIX (Linux / macOS) file lock
            try:
                import fcntl
                from pathlib import Path
                lock_path = Path.home() / ".flowpilot" / "flowpilot.lock"
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                self.lock_file = open(lock_path, "w")
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except (IOError, BlockingIOError, ImportError):
                self.already_running = True

    def is_already_running(self) -> bool:
        return self.already_running

    def release(self):
        if self.mutex and sys.platform == "win32":
            try:
                ctypes.windll.kernel32.CloseHandle(self.mutex)
            except Exception:
                pass
            self.mutex = None
        if self.lock_file and sys.platform != "win32":
            try:
                import fcntl
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()
            except Exception:
                pass
            self.lock_file = None
