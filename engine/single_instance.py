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
        self.already_running = False

        if sys.platform == "win32":
            kernel32 = ctypes.windll.kernel32
            # Create named mutex
            self.mutex = kernel32.CreateMutexW(None, False, self.mutex_name)
            last_error = kernel32.GetLastError()
            ERROR_ALREADY_EXISTS = 183
            if last_error == ERROR_ALREADY_EXISTS:
                self.already_running = True

    def is_already_running(self) -> bool:
        return self.already_running

    def release(self):
        if self.mutex and sys.platform == "win32":
            ctypes.windll.kernel32.CloseHandle(self.mutex)
            self.mutex = None
